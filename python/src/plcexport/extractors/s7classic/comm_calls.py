"""Calls of the communication blocks for S7 connections, read from raw STL.

DotNetSiemensPLCToolBoxLibrary rebuilds ``CALL`` statements and loses the ANY pointers of FB and
SFB calls, so s7dump also emits the statements of such networks without call reconstruction
(``raw_stl``). There the parameters are plain assignments in front of the call::

    L     W#16#AAAA                 T     #Send.IN.ID
    L     W#16#1005                 T     #Send.IN_OUT.SD_1      ANY: syntax 10h, type INT
    L     1                         T     DIW[AR2,P#104.0]       ANY: count
    L     4                         T     DIW[AR2,P#106.0]       ANY: DB number
    L     P#DBX 0.0                 T     DID[AR2,P#108.0]       ANY: area and address
    +AR2  P#90.0                                                 base of the instance
    UC    "BSEND"

Values are taken as written. A parameter fed by anything but a constant is
``unresolved`` with its operand, one without assignment ``unassigned``; nothing is
guessed. This module handles addresses as data and contacts nothing.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from plcexport.model import AreaRole, CallValue, CommBlock

# SFB/FB number -> block and the parameters it must have to be taken for it (a user FB with one
# of these numbers and another interface is not a communication block)
BLOCKS: dict[int, tuple[CommBlock, frozenset[str]]] = {
    8: ("USEND", frozenset({"ID", "R_ID", "SD_1"})),
    9: ("URCV", frozenset({"ID", "R_ID", "RD_1"})),
    12: ("BSEND", frozenset({"ID", "R_ID", "SD_1", "LEN"})),
    13: ("BRCV", frozenset({"ID", "R_ID", "RD_1", "LEN"})),
    14: ("GET", frozenset({"ID", "ADDR_1", "RD_1"})),
    15: ("PUT", frozenset({"ID", "ADDR_1", "SD_1"})),
}
ROLES: dict[str, AreaRole] = {"SD": "send", "RD": "receive", "ADDR": "remote"}
# data type code of an ANY pointer -> (name, bytes per element; 0 = one bit)
ANY_TYPES: dict[int, tuple[str, int]] = {
    0x01: ("BOOL", 0), 0x02: ("BYTE", 1), 0x03: ("CHAR", 1), 0x04: ("WORD", 2), 0x05: ("INT", 2),
    0x06: ("DWORD", 4), 0x07: ("DINT", 4), 0x08: ("REAL", 4), 0x09: ("DATE", 2), 0x0A: ("TOD", 4),
    0x0B: ("TIME", 4), 0x0C: ("S5TIME", 2), 0x0E: ("DT", 8),
}  # fmt: skip
POINTER_CODE = "set by pointer code"

_AREA_PARAM = re.compile(r"^(SD|RD|ADDR)_\d+$")
_SYMBOLIC = re.compile(r"^#([^.]+)\.(?:IN|OUT|IN_OUT|STAT)\.([A-Za-z_0-9]+)$")
_RELATIVE = re.compile(r"^DI[BWDX]\s*\[\s*AR2\s*,\s*P#(\d+)\.\d\s*\]$")
_ABSOLUTE = re.compile(r"^DI[BWDX]\s*(\d+)(?:\.\d)?$")
_BASE = re.compile(r"^P#(\d+)\.\d$")
_INSTANCE_DB = re.compile(r"^DI\s*(\d+)$")
_POINTER = re.compile(r"^P#\s*(DBX|DIX|M|I|E|Q|A|L)\s*(\d+)\.(\d)$")
_HEX = re.compile(r"^(?:B|W|DW)#16#([0-9A-Fa-f_]+)$")
_INT = re.compile(r"^(?:L#)?(-?\d+)$")
_BINARY = re.compile(r"^2#([01_]+)$")
# statements that may stand in front of a call without touching a parameter by pointer
_HARMLESS = frozenset(
    [
        "BLD",
        "=",
        "CDB",
        "TDB",
        "OPN",
        "AUF",
        "TAR2",
        "LAR2",
        "+AR2",
        "NOP",
        "L",
        "T",
        "A",
        "AN",
        "O",
        "ON",
        "U",
        "UN",
        "X",
        "XN",
        "S",
        "R",
        "SET",
        "CLR",
        "NOT",
        "FP",
        "FN",
        "JNB",
        "SPBNB",
        "SAVE",
    ]
)
_AREA_NAMES = {"E": "I", "A": "Q"}  # German mnemonics


@dataclass(frozen=True)
class FoundArea:
    param: str
    role: AreaRole
    pointer: str | None = None
    db_number: int | None = None  # 0 or None: not a data block area
    start_byte: int | None = None
    start: str | None = None  # "byte.bit"
    length_bytes: int | None = None
    unresolved: str | None = None
    unassigned: bool = False


@dataclass(frozen=True)
class FoundCall:
    block: CommBlock
    called: str  # "FB 12 #WritePLC3"
    id: CallValue
    r_id: CallValue | None
    len: CallValue | None
    areas: tuple[FoundArea, ...] = ()


@dataclass
class _Segment:
    """What stands between two calls."""

    assigns: list[tuple[str, str]] = field(default_factory=list)  # (target, loaded operand)
    base: int = 0
    instance_db: int | None = None
    pointer_code: bool = False
    loaded: str | None = None


def constant(operand: str) -> int | None:
    """The value of a constant operand; None for anything else (a variable, a pointer)."""
    op = operand.strip()
    if m := _INT.match(op):
        return int(m.group(1))
    if m := _HEX.match(op):
        return int(m.group(1).replace("_", ""), 16)
    if m := _BINARY.match(op):
        return int(m.group(1).replace("_", ""), 2)
    return None


def _split(line: str) -> tuple[str, str]:
    parts = line.strip().split(None, 1)
    return (parts[0], parts[1].strip() if len(parts) > 1 else "") if parts else ("", "")


def find_calls(
    raw_stl: Sequence[str], resolve: Callable[[str], Mapping[str, Any] | None]
) -> list[FoundCall]:
    """The communication block calls of one network, in order. ``resolve`` returns the dump
    block of a call target (``"BSEND"``, ``FB 12``), or None."""
    calls: list[FoundCall] = []
    seg = _Segment()
    for line in raw_stl:
        op, arg = _split(line)
        if not op or op.startswith("//"):
            continue
        if op in ("UC", "CC", "CALL"):
            callee = resolve(arg)
            if callee is not None and (call := _build(callee, seg)) is not None:
                calls.append(call)
            seg = _Segment()
            continue
        if op == "L":
            seg.loaded = arg
        elif op == "T":
            if seg.loaded is not None:
                seg.assigns.append((arg, seg.loaded))
        elif op == "+AR2":
            if m := _BASE.match(arg):
                seg.base = int(m.group(1))
        elif op in ("OPN", "AUF"):
            if m := _INSTANCE_DB.match(arg):
                seg.instance_db = int(m.group(1))
        elif op not in _HARMLESS:
            seg.pointer_code = True
    return calls


def _build(callee: Mapping[str, Any], seg: _Segment) -> FoundCall | None:
    number, kind = int(callee.get("number") or 0), str(callee.get("type"))
    if kind not in ("FB", "SFB") or number not in BLOCKS:
        return None
    block, required = BLOCKS[number]
    members = {
        str(m["name"]): m
        for m in callee.get("interface") or []
        if m.get("section") in ("IN", "OUT", "IN_OUT") and m.get("offset")
    }
    if not required <= set(members):
        return None  # same number, another interface: not this communication block
    offsets = {name: int(str(m["offset"]).split(".")[0]) for name, m in members.items()}

    by_param: dict[str, str] = {}  # parameter -> operand of its (first word's) assignment
    by_offset: dict[int, str] = {}  # byte offset inside the instance -> operand
    instance: str | None = None
    for target, operand in seg.assigns:
        if m := _SYMBOLIC.match(target):
            instance = instance or m.group(1)
            by_param[m.group(2)] = operand
            if m.group(2) in offsets:
                by_offset[offsets[m.group(2)]] = operand
        elif m := _RELATIVE.match(target):
            by_offset[int(m.group(1)) - seg.base] = operand
        elif m := _ABSOLUTE.match(target):
            by_offset[int(m.group(1))] = operand

    def value(name: str, width: int | None) -> CallValue | None:
        if name not in members:
            return None
        operand = by_param.get(name, by_offset.get(offsets[name]))
        if operand is None:
            if seg.pointer_code:
                return CallValue(unresolved=POINTER_CODE)
            return CallValue(unassigned=True)
        number_ = constant(operand)
        if number_ is None:
            return CallValue(unresolved=operand)
        if width is None:
            return CallValue(str(number_))
        return CallValue(f"0x{number_ & ((1 << (width * 4)) - 1):0{width}X}")

    areas = tuple(
        _area(name, offsets[name], by_offset, seg.pointer_code)
        for name, m in members.items()
        if _AREA_PARAM.match(name) and str(m.get("type")).upper() == "ANY"
    )
    called = f"{kind} {number}" + (
        f" #{instance}" if instance else f" DB {seg.instance_db}" if seg.instance_db else ""
    )
    return FoundCall(
        block, called, value("ID", 4) or CallValue(unassigned=True), value("R_ID", 8),
        value("LEN", None), areas,
    )  # fmt: skip


def _area(param: str, offset: int, by_offset: Mapping[int, str], pointer_code: bool) -> FoundArea:
    role = ROLES[param.split("_")[0]]
    parts = [by_offset.get(offset + k) for k in (0, 2, 4, 6)]  # type word, count, DB, pointer
    if all(p is None for p in parts):
        if pointer_code:
            return FoundArea(param, role, unresolved=POINTER_CODE)
        return FoundArea(param, role, unassigned=True)
    head, count, db = (constant(p) if p is not None else None for p in parts[:3])
    where = _POINTER.match(parts[3].strip()) if parts[3] is not None else None
    if head is None or count is None or db is None or where is None or head >> 8 != 0x10:
        written = ", ".join(p for p in parts if p is not None)
        return FoundArea(param, role, unresolved=written)
    type_name, size = ANY_TYPES.get(head & 0xFF, (f"type {head & 0xFF:#04x}", -1))
    area, byte, bit = where.group(1), int(where.group(2)), int(where.group(3))
    area = _AREA_NAMES.get(area, area)
    if db and area == "DBX":
        location = f"DB{db}.DBX{byte}.{bit}"
    else:
        location = f"{area}{byte}.{bit}" if area in ("DBX", "DIX") else f"{area} {byte}.{bit}"
    length = None if size < 0 else (count + 7) // 8 if size == 0 else count * size
    return FoundArea(
        param, role, f"P#{location} {type_name} {count}", db or None, byte, f"{byte}.{bit}", length
    )
