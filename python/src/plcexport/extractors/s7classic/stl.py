"""STL analyzer: cross-references from STEP 7 statement list.

Implements contracts/stl-xref-rules.md. Input is one network's STL lines (as ``s7dump`` emits
them) plus a lookup of callee interfaces; output is one :class:`StlRef` per operand occurrence.
International and German mnemonics are both accepted. An unknown instruction with an operand
produces a warning, never an exception.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from plcexport.extractors.s7classic.addresses import area, collapse

Access = Literal["read", "write", "read_write", "call", "unknown_direction", "indirect"]
TargetKind = Literal["variable", "unit"]

READ_BIT = {"A", "AN", "O", "ON", "X", "XN", "U", "UN"}
WRITE = {"=", "S", "R", "T", "FR", "CU", "CD", "ZV", "ZR", "TAR1", "TAR2"}
TIMER_START = {"SP", "SE", "SD", "SS", "SF", "SI", "SV", "SA"}
EDGE = {"FP", "FN"}
READ = {"L", "LC", "LAR1", "LAR2"}
OPEN = {"OPN", "AUF"}
CALLS = {"CALL", "UC", "CC"}
NO_OPERAND_EFFECT = {
    "NOT", "SET", "CLR", "SAVE", "BE", "BEC", "BEU", "BEB", "BEA", "NOP", "TAK", "POP", "PUSH",
    "ENT", "LEAVE", "INC", "DEC", "+AR1", "+AR2", "CAW", "CAD", "TAW", "TAD", "INVI", "INVD",
    "NEGI", "NEGD", "NEGR", "ITD", "ITB", "BTI", "DTB", "BTD", "DTR", "RND", "RND+", "RND-",
    "TRUNC", "ABS", "SQR", "SQRT", "EXP", "LN", "SIN", "COS", "TAN", "ASIN", "ACOS", "ATAN",
    "SSI", "SSD", "SLW", "SRW", "SLD", "SRD", "RLD", "RRD", "RLDA", "RRDA", "AW", "OW", "XOW",
    "AD", "OD", "XOD", "UW", "UD", "MOD", "+", "-", "*", "/", ")", "A(", "AN(", "O(", "ON(",
    "X(", "XN(", "U(", "UN(", "==I", "<>I", ">I", "<I", ">=I", "<=I", "==D", "<>D", ">D", "<D",
    ">=D", "<=D", "==R", "<>R", ">R", "<R", ">=R", "<=R", "+I", "-I", "*I", "/I", "+D", "-D",
    "*D", "/D", "+R", "-R", "*R", "/R", "CDB", "TDB",
}  # fmt: skip
JUMPS_PREFIX = ("J", "SP", "LOOP")  # JU/JC/…, German SPA/SPB/…, LOOP

_LABEL = re.compile(r"^\s*([A-Za-z_]\w{0,3})\s*:(?!=)\s*")  # "M001:", "T1  :", not "X:="
_PARAM = re.compile(r"^\s*([A-Za-z_]\w*)\s*:=\s*(.*?)\s*;?\s*$")
_CONSTANT = re.compile(
    r"^(?:[+-]?\d+(?:\.\d+)?(?:E[+-]?\d+)?|[A-Z0-9]+#.*|'.*'|TRUE|FALSE|L#.*|B#.*|W#.*|DW#.*)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class StlRef:
    line: int  # 0-based index into the network's lines
    target_text: str
    target_kind: TargetKind
    access: Access
    via_param: str | None = None


@dataclass
class StlResult:
    refs: list[StlRef] = field(default_factory=list)
    warnings: list[tuple[int, str]] = field(default_factory=list)  # (line, text)


CalleeLookup = Callable[[str], Mapping[str, str] | None]  # callee -> {param: section}


def _strip(line: str) -> str:
    code = line.split("//", 1)[0]
    code = _LABEL.sub("", code, count=1)
    return code.strip().rstrip(";").strip()


def _is_constant(operand: str) -> bool:
    return bool(_CONSTANT.match(operand.replace(" ", ""))) or operand.upper().startswith("P#")


def _is_element(operand: str) -> bool:
    """``#arr[1, 0]`` or ``"DB".arr[#i]``: an array element, not register-indirect addressing."""
    return "[" in operand and operand.lstrip()[:1] in ('"', "#")


def _element(i: int, operand: str, access: Access, out: StlResult, via: str | None = None) -> None:
    """Record an array element under its array variable, and non-constant indexes as reads."""
    out.refs.append(StlRef(i, collapse(operand[: operand.index("[")]), "variable", access, via))
    for index in re.findall(r"\[([^\]]*)\]", operand):
        for part in index.split(","):
            part = part.strip()
            if part and not _is_constant(part):
                out.refs.append(StlRef(i, collapse(part), "variable", "read"))


def _indirect(i: int, operand: str, out: StlResult) -> None:
    out.refs.append(StlRef(i, collapse(operand), "variable", "indirect"))
    inner = operand[operand.index("[") + 1 : operand.rindex("]")] if "]" in operand else ""
    if inner and not inner.upper().startswith(("AR1", "AR2")):
        out.refs.append(StlRef(i, collapse(inner), "variable", "read"))


def _call(i: int, operand: str, lines: Sequence[str], callees: CalleeLookup, out: StlResult) -> int:
    """Handle CALL/UC/CC and its parameter lines; return the index of the last consumed line."""
    # 'CALL "FB_X" , "DB_X"' or 'CALL "GRAFCET FB", DB1 (' with one parameter per line and ')'
    operand = operand.rstrip().removesuffix("(").rstrip()
    target, _, instance = operand.partition(",")
    target = collapse(target)
    out.refs.append(StlRef(i, target, "unit", "call"))
    if instance.strip():
        out.refs.append(StlRef(i, collapse(instance), "variable", "call"))
    sections = callees(target) or {}
    j = i + 1
    while j < len(lines):
        m = _PARAM.match(_LABEL.sub("", lines[j].split("//", 1)[0], count=1))
        if not m:
            if lines[j].split("//", 1)[0].strip() == ")":
                j += 1  # end of the parameter list
            break
        param, value = m.group(1), m.group(2).strip()
        closes = value.endswith(")") and value.count("(") < value.count(")")
        if closes:  # "MAN_ON := )" or "X := M 1.0)" ends the parameter list
            value = value[:-1]
        value = value.strip().rstrip(",").strip()
        if value and not _is_constant(value):
            sec = sections.get(param)
            access: Access = {"IN": "read", "OUT": "write", "IN_OUT": "read_write"}.get(
                sec or "", "unknown_direction"
            )  # type: ignore[assignment]
            if _is_element(value):
                _element(j, value, access, out, via=param)
            elif "[" in value:
                _indirect(j, value, out)
            else:
                out.refs.append(StlRef(j, collapse(value), "variable", access, via_param=param))
        j += 1
        if closes:
            break
    return j - 1


def analyze(lines: Sequence[str], callees: CalleeLookup | None = None) -> StlResult:
    callees = callees or (lambda _name: None)
    out = StlResult()
    i = 0
    while i < len(lines):
        code = _strip(lines[i])
        if not code:
            i += 1
            continue
        parts = code.split(None, 1)
        op = parts[0].upper()
        operand = parts[1].strip() if len(parts) > 1 else ""
        if op in CALLS:
            i = _call(i, operand, lines, callees, out) + 1
            continue
        is_jump = op.startswith(JUMPS_PREFIX) and op not in (TIMER_START | WRITE | READ)
        if not operand or op in NO_OPERAND_EFFECT or is_jump:
            i += 1
            continue
        access: Access | None = (
            "read" if op in READ_BIT or op in READ
            else "write" if op in WRITE or op in TIMER_START
            else "read_write" if op in EDGE
            else None
        )  # fmt: skip
        if _is_element(operand) and access is not None:
            _element(i, operand, access, out)
        elif "[" in operand:
            _indirect(i, operand, out)
        elif _is_constant(operand):
            pass
        elif op in OPEN:
            out.refs.append(StlRef(i, collapse(operand), "unit", "read"))
        elif access is not None:
            out.refs.append(StlRef(i, collapse(operand), "variable", access))
        else:
            out.warnings.append((i, lines[i].strip()))
        i += 1
    return out


def is_known_target(operand: str) -> bool:
    return area(operand) != "other"
