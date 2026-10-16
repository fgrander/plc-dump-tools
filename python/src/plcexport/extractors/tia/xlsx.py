"""Minimal xlsx reader for TIA's alarm and supervision exports.

Standard library only (zip + XML, parsed with defusedxml: the files come from customer
projects). Returns each sheet as rows of strings; empty cells are "".
"""

from __future__ import annotations

import re
import zipfile
from io import BytesIO

from defusedxml import ElementTree as SafeET

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_SHEET = re.compile(r"^xl/worksheets/sheet(\d+)\.xml$")
_CELL = re.compile(r"^([A-Z]+)\d+$")


def _column(ref: str) -> int:
    m = _CELL.match(ref)
    if not m:
        return 0
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def read_sheets(data: bytes) -> list[list[list[str]]]:
    """All sheets in order: sheet → rows → cells."""
    with zipfile.ZipFile(BytesIO(data)) as z:
        names = z.namelist()
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = SafeET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.iter(f"{_NS}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{_NS}t")))
        sheets = sorted((int(m.group(1)), n) for n in names if (m := _SHEET.match(n)))
        out: list[list[list[str]]] = []
        for _, name in sheets:
            rows: list[list[str]] = []
            for row in SafeET.fromstring(z.read(name)).iter(f"{_NS}row"):
                cells: list[str] = []
                for c in row.iter(f"{_NS}c"):
                    col = _column(c.get("r", ""))
                    while len(cells) < col:
                        cells.append("")
                    v = c.find(f"{_NS}v")
                    inline = c.find(f"{_NS}is")
                    if c.get("t") == "s" and v is not None and v.text is not None:
                        cells.append(shared[int(v.text)])
                    elif inline is not None:
                        cells.append("".join(t.text or "" for t in inline.iter(f"{_NS}t")))
                    else:
                        cells.append(v.text if v is not None and v.text is not None else "")
                rows.append(cells)
            out.append(rows)
        return out


_LANG = re.compile(r"\[([a-z]{2,3}-[A-Z]{2})\]")


def language_of(header: str) -> str | None:
    """``"Alarm text" - English (USA) / [en-US] / Event text`` → ``en-US``."""
    m = _LANG.search(header)
    return m.group(1) if m else None
