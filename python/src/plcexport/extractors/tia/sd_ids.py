"""Stable text IDs in SIMATIC SD files.

TIA names every multilingual text of a unit with an ID (``MLC_4M3``). The ``.s7dcl`` file refers
to it in a pragma (``{ S7_MLC := "MLC_4M3" }``, also ``S7_BlockTitle``, ``S7_BlockComment``,
``S7_NetworkTitle``, ``S7_NetworkComment``), the ``.s7res`` file lists the texts by ID. TIA makes
these IDs up again whenever it upgrades a project, so two exports of one unchanged V19 archive
differed in every ID and nothing else (first real batch, 2026-10-10).

The IDs carry no meaning beyond pairing a pragma with its text, so each unit's IDs are renumbered
in a stable order: ``MLC_1``, ``MLC_2`` … in the order of the ``.s7res`` entries, then IDs that
only the ``.s7dcl`` uses. Everything else stays byte-exact (BOM, CRLF, spacing).
"""

from __future__ import annotations

import re
from collections.abc import Mapping

DCL, RES = ".s7dcl", ".s7res"
_ID = rb"MLC_[0-9A-Za-z]+"
_IN_DCL = re.compile(rb'(S7_\w+[ \t]*:=[ \t]*")(' + _ID + rb')(")')
_IN_RES = re.compile(rb"(?m)^([ \t]*-[ \t]*id:[ \t]*)(" + _ID + rb")(?=[ \t]*\r?$)")


def _renumber(dcl: bytes, res: bytes | None) -> tuple[bytes, bytes | None]:
    order: dict[bytes, bytes] = {}
    for pattern, data in ((_IN_RES, res or b""), (_IN_DCL, dcl)):
        for m in pattern.finditer(data):
            order.setdefault(m.group(2), b"MLC_%d" % (len(order) + 1))
    if not order:
        return dcl, res
    new_dcl = _IN_DCL.sub(lambda m: m.group(1) + order[m.group(2)] + m.group(3), dcl)
    new_res = _IN_RES.sub(lambda m: m.group(1) + order[m.group(2)], res) if res else res
    return new_dcl, new_res


def stable_text_ids(files: Mapping[str, bytes]) -> dict[str, bytes]:
    """SD files (path -> bytes) with the text IDs of every unit renumbered in a stable order."""
    out = dict(files)
    for path in sorted(files):
        if not path.endswith(DCL):
            continue
        res_path = path[: -len(DCL)] + RES
        out[path], res = _renumber(files[path], files.get(res_path))
        if res is not None:
            out[res_path] = res
    return out
