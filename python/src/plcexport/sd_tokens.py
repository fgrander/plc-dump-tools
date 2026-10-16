"""Tokens of SIMATIC SD source text (``.s7dcl``: SCL and the textual LAD/FBD notation).

Used by the call finder (``extractors/tia/comm_calls.py``); imports nothing else from the package.

Token kinds (``match.lastgroup``): comment, string, pragma, global (``"DB".member``), absolute
(``%I0.0``), local (``#x``), typed (``W#16#100``, ``WORD#16#100``, ``T#5s``), number (``16#100``,
``10``, ``1.5``), ident, assign (``:=``), out (``=>``), op (one of ``( ) , ; :``).
"""

from __future__ import annotations

import re

QUOTED = r'"(?:[^"]|"")+"'
MEMBER = rf"(?:\s*\.\s*(?:{QUOTED}|[A-Za-z_]\w*|%[XBWD]\d+)|\[[^\]\n]*\])*"
TOKEN = re.compile(
    rf"""
    (?P<comment>//[^\n]*|\(\*.*?\*\))
  | (?P<string>'(?:\$.|[^'$\n])*')
  | (?P<pragma>\{{[^}}]*\}})
  | (?P<global>{QUOTED}{MEMBER})
  | (?P<absolute>%DB\d+\.DB[XBWD]\d+(?:\.\d+)?|%[IQMEA][XBWD]?\d+(?:\.\d+)?(?::P)?)
  | (?P<local>(?<![\w#])\#(?:{QUOTED}|[A-Za-z_]\w*){MEMBER})
  | (?P<typed>[A-Za-z_]\w*\#[^\s,;()]*)
  | (?P<number>\d[\w#.]*)
  | (?P<ident>[A-Za-z_]\w*)
  | (?P<assign>:=)
  | (?P<out>=>)
  | (?P<op>[(),;:])
    """,
    re.VERBOSE | re.DOTALL,
)
