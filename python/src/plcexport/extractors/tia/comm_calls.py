"""Communication block calls (GET, PUT, BSEND, BRCV, USEND, URCV) in the program files of a TIA
export. The calls are returned unlinked; linking and findings
are the shared rules of ``plcexport.connections_link``.

SIMATIC SD text (``.s7dcl``, SCL and the textual LAD/FBD) is read with the token rules shared
with 002's SD profile. A call is identified by the block name in the call (``"BSEND_DB".BSEND(``,
the LAD/FBD form), by the type of a multi-instance (``#g(`` with ``g : GET``), or by the
instance data block's type (``"GET_DB"(``) when that data block is a unit of the export.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import get_args

from plcexport.model import AreaRole, CallValue, CommBlock, ConnectionUse, DataArea
from plcexport.sd_tokens import TOKEN

BLOCKS: frozenset[str] = frozenset(get_args(CommBlock))
WITH_R_ID = frozenset({"BSEND", "BRCV", "USEND", "URCV"})
WITH_LEN = frozenset({"BSEND", "BRCV"})
ROLES: dict[str, AreaRole] = {"SD": "send", "RD": "receive", "ADDR": "remote"}
_AREA = re.compile(r"^(SD|RD|ADDR)_\d+$", re.IGNORECASE)
_HEX = re.compile(
    r"^(?:16|B#16|W#16|DW#16|BYTE#16|WORD#16|DWORD#16|LWORD#16)#([0-9A-F_]+)$", re.IGNORECASE
)
_DEC = re.compile(r"^(?:(?:U?S?D?L?INT|U?INT|U?DINT|U?SINT|U?LINT)#)?\+?(\d[\d_]*)$", re.IGNORECASE)
_BIN = re.compile(r"^2#([01_]+)$")
_DB_POINTER = re.compile(r"^P#DB(\d+)\.DBX(\d+)\.(\d)\s+(\w+)\s+(\d+)$", re.IGNORECASE)
_POINTER = re.compile(r"^P#[A-Z]+\s*(\d+)\.(\d)\s+(\w+)\s+(\d+)$", re.IGNORECASE)
_SIZES = {"BYTE": 1, "CHAR": 1, "USINT": 1, "SINT": 1, "WORD": 2, "INT": 2, "UINT": 2,
          "DWORD": 4, "DINT": 4, "UDINT": 4, "REAL": 4, "TIME": 4, "LWORD": 8, "LREAL": 8,
          "LINT": 8, "ULINT": 8}  # fmt: skip
_QUOTED_NAME = re.compile(r'^"((?:[^"]|"")+)"')

DbResolver = Callable[[int], str | None]


def constant(operand: str) -> int | None:
    """The value of a constant operand as SD writes it (``16#100``, ``W#16#100``,
    ``WORD#16#100``, ``DW#16#B``, ``32``, ``UINT#5``, ``2#101``); None for anything else."""
    op = operand.strip()
    if m := _HEX.match(op):
        return int(m.group(1).replace("_", ""), 16)
    if m := _BIN.match(op):
        return int(m.group(1).replace("_", ""), 2)
    if m := _DEC.match(op):
        return int(m.group(1).replace("_", ""))
    return None


def _value(raw: str | None, width: int | None) -> CallValue:
    if raw is None or raw == "":
        return CallValue(unassigned=True)
    number = constant(raw)
    if number is None:
        return CallValue(unresolved=raw)
    if width is None:
        return CallValue(str(number))
    return CallValue(f"0x{number & ((1 << (width * 4)) - 1):0{width}X}")


def _area(param: str, raw: str | None, db_number: DbResolver) -> DataArea:
    role = ROLES[param.split("_")[0].upper()]
    if raw is None or raw == "":
        return DataArea(param, role, unassigned=True)
    if m := _DB_POINTER.match(raw):
        n, byte, bit, typ, count = m.groups()
        size = _SIZES.get(typ.upper())
        length = (
            int(count) * size if size else (int(count) + 7) // 8 if typ.upper() == "BOOL" else None
        )
        db = db_number(int(n)) if role != "remote" else None  # a remote area is in the partner
        return DataArea(param, role, raw, db, f"{byte}.{bit}", length)
    if m := _POINTER.match(raw):
        byte, bit, typ, count = m.groups()
        size = _SIZES.get(typ.upper())
        return DataArea(
            param, role, raw, None, f"{byte}.{bit}", int(count) * size if size else None
        )
    if raw.startswith('"'):
        name = _QUOTED_NAME.match(raw)
        db = name.group(1).replace('""', '"') if name and role != "remote" else None
        return DataArea(param, role, raw, db, members=(raw,) if role != "remote" else ())
    return DataArea(param, role, unresolved=raw)


def _block_of(
    kind: str, text: str, statics: Mapping[str, str], instances: Mapping[str, str]
) -> str | None:
    if kind == "global":
        quoted = _QUOTED_NAME.match(text)
        rest = text[quoted.end() :].strip() if quoted else ""
        if rest.startswith("."):
            member = rest[1:].strip().strip('"')
            return member.upper() if member.upper() in BLOCKS else None
        name = quoted.group(1) if quoted else text
        typ = instances.get(name)
    elif kind == "local":
        typ = statics.get(text.lstrip("#").strip('"'))
    else:
        return None
    return typ.upper() if typ and typ.upper() in BLOCKS else None


def _arguments(text: str, tokens: list[re.Match[str]], i: int) -> tuple[dict[str, str], int]:
    """``param := value`` pairs of the call whose ``(`` is just before ``tokens[i]``, values as
    written (whitespace collapsed; ``=>`` outputs skipped), and the index after the ``)``."""
    params: dict[str, str] = {}
    depth, param, start = 1, None, None
    while i < len(tokens) and depth:
        g, kind = tokens[i].group(), tokens[i].lastgroup
        if depth == 1 and g in (",", ")"):
            if param is not None and start is not None:
                params[param] = " ".join(text[start : tokens[i].start()].split())
            param, start = None, None
            if g == ")":
                depth = 0
        elif g == "(":
            depth += 1
        elif g == ")":
            depth -= 1
        elif depth == 1 and kind == "ident" and _is_param(tokens, i):
            param = g.upper()
        elif depth == 1 and kind == "assign" and param is not None:
            start = tokens[i].end()
        elif depth == 1 and kind == "out":
            param = None
        i += 1
    return params, i


def _is_param(tokens: list[re.Match[str]], i: int) -> bool:
    return i + 1 < len(tokens) and tokens[i + 1].group() in (":=", "=>")


def sd_calls(
    unit: str,
    text: str,
    *,
    statics: Mapping[str, str] | None = None,
    instances: Mapping[str, str] | None = None,
    db_number: DbResolver = lambda _n: None,
) -> list[ConnectionUse]:
    """The communication calls of one SD unit. ``statics``: multi-instance name -> type of the
    unit's interface; ``instances``: instance data block -> its function block type;
    ``db_number``: data block number -> unit name."""
    statics, instances = statics or {}, instances or {}
    tokens = list(TOKEN.finditer(text))
    out: list[ConnectionUse] = []
    network: int | None = None
    i = 0
    while i < len(tokens):
        t = tokens[i]
        kind, value = t.lastgroup or "", t.group()
        i += 1
        if kind == "ident" and value.upper() == "NETWORK":
            network = (network or 0) + 1
            continue
        nxt = tokens[i] if i < len(tokens) else None
        if nxt is None or nxt.group() != "(" or kind not in ("global", "local"):
            continue
        block = _block_of(kind, value, statics, instances)
        i += 1  # the "("
        params, i = _arguments(text, tokens, i)
        if block is None:
            continue
        r_id = _value(params.get("R_ID"), 8) if block in WITH_R_ID else None
        out.append(
            ConnectionUse(
                unit=unit,
                block=block,  # type: ignore[arg-type]
                called=value,
                network_no=network,
                line=None if network is not None else text.count("\n", 0, t.start()) + 1,
                id=_value(params.get("ID"), 4),
                r_id=r_id,
                areas=tuple(
                    _area(p, raw, db_number) for p, raw in params.items() if _AREA.match(p)
                ),
                len=_value(params.get("LEN"), None) if block in WITH_LEN else None,
            )
        )
    return out
