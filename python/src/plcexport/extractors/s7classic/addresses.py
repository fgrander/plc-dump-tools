"""STEP 7 operand normalization (contracts/stl-xref-rules.md).

Exports keep operands as written; the normalized key only serves matching, so that ``E 0.0``
(German) and ``I0.0`` (international) are the same input bit. Symbols (``"I_Start"``) and
locals (``#Temp``) are returned unchanged.
"""

from __future__ import annotations

import re
from typing import Literal

Area = Literal[
    "input", "output", "memory", "local", "timer", "counter", "db", "block", "symbol", "other"
]

_GERMAN_AREA = {"PE": "PI", "PA": "PQ", "E": "I", "A": "Q", "PI": "PI", "PQ": "PQ", "I": "I",
                "Q": "Q", "M": "M", "L": "L"}  # fmt: skip
_BIT_WORD = re.compile(r"^(PE|PA|PI|PQ|E|A|I|Q|M|L)([BWD]?)(\d+(?:\.\d)?)$")
_TIMER_COUNTER = re.compile(r"^(T|C|Z)(\d+)$")
_DB_FULL = re.compile(r"^DB(\d+)\.DB([XBWD])(\d+(?:\.\d)?)$")
_DB_OPEN = re.compile(r"^D([BI])([XBWD])(\d+(?:\.\d)?)$")
_BLOCK = re.compile(r"^(DB|DI|FB|FC|SFB|SFC|OB|UDT|VAT)(\d+)$")


def collapse(text: str) -> str:
    """Operand as written, with runs of whitespace reduced to one space."""
    return " ".join(text.split())


def normalize(operand: str) -> str:
    """Mnemonic-independent key: ``E 0.0`` / ``I0.0`` -> ``I0.0``; ``Z 3`` -> ``C3``."""
    text = operand.strip()
    if text.startswith(('"', "#")):
        return text
    compact = "".join(text.split()).upper()
    if m := _BIT_WORD.match(compact):
        return f"{_GERMAN_AREA[m.group(1)]}{m.group(2)}{m.group(3)}"
    if m := _TIMER_COUNTER.match(compact):
        return f"{'C' if m.group(1) == 'Z' else m.group(1)}{m.group(2)}"
    if _DB_FULL.match(compact) or _DB_OPEN.match(compact) or _BLOCK.match(compact):
        return compact
    return compact


def area(operand: str) -> Area:
    """Memory area of an operand (normalized first)."""
    text = operand.strip()
    if text.startswith('"'):
        return "symbol"
    if text.startswith("#"):
        return "local"
    key = normalize(text)
    if m := _BIT_WORD.match(key):
        areas: dict[str, Area] = {"I": "input", "PI": "input", "Q": "output", "PQ": "output",
                                  "M": "memory", "L": "local"}  # fmt: skip
        return areas[m.group(1)]
    if key.startswith("T") and _TIMER_COUNTER.match(key):
        return "timer"
    if key.startswith("C") and _TIMER_COUNTER.match(key):
        return "counter"
    if _DB_FULL.match(key) or _DB_OPEN.match(key):
        return "db"
    if _BLOCK.match(key):
        return "block"
    return "other"


_GLOBAL_AREAS = frozenset(
    {"input", "output", "memory", "timer", "counter", "db", "symbol", "block"}
)


def is_global_target(operand: str) -> bool:
    """cross-referenced operands — I/O, memory, timers, counters, DB values, global
    symbols and blocks. Not locals (``#x``, ``L 0.1``), not ``DIX``/``DIW`` (the running FB's
    own instance data), not registers or anything else unrecognized."""
    a = area(operand)
    if a == "db" and normalize(operand).startswith("DI"):
        return False
    return a in _GLOBAL_AREAS


def is_address(operand: str) -> bool:
    """True for an absolute address, a symbol or a local — not for constants or pointers."""
    return area(operand) != "other"


def io_direction(address: str | None) -> Literal["input", "output", "memory"] | None:
    if not address:
        return None
    a = area(address)
    if a == "input" or a == "output" or a == "memory":
        return a
    return None
