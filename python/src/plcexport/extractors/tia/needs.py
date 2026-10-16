"""Products a TIA source needs, and whether an installation covers them.

A need is a product name without its version: TIA maps a V20 product to its V21 successor on
upgrade, and the TIA version itself is routed by rank (``rank.py``). Installed names can bundle
several products ("WinCC Basic/Comfort/Advanced" covers "WinCC Comfort"), as in tiadump's
``OpenReport.Expand``. The engineering base that every TIA installation has is never a need.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

# "V21", "V20 SP1", "V11 Update 2", "V17 Upd 3", "V5.4" at the end of a name
_VERSION_TAIL = re.compile(r"\s+V\d+(?:\.\d+)*(?:\s*(?:SP|Upd(?:ate)?)\s*\d+)*\s*$", re.IGNORECASE)
BASE = frozenset({"totally integrated automation portal", "step 7 professional", "step 7 basic"})


def normalize(name: str) -> str:
    """Comparable form: no trailing version, single spaces, case-folded."""
    return " ".join(_VERSION_TAIL.sub("", name.strip()).split()).casefold()


def expand(name: str) -> set[str]:
    """``WinCC Basic/Comfort/Advanced`` → itself, WinCC Basic, WinCC Comfort, WinCC Advanced."""
    n = normalize(name)
    out = {n}
    if "/" in n:
        parts = n.split("/")
        first = parts[0]
        prefix = first[: first.rfind(" ") + 1] if " " in first else ""
        out.add(first)
        out.update(prefix + p.strip() for p in parts[1:])
    return out


def needs_from(products: Iterable[Any]) -> list[str]:
    """Needs from product rows (``(name, version)``, ``{"name": …}`` or plain names), sorted and
    without the engineering base."""
    names: set[str] = set()
    for p in products:
        if isinstance(p, Mapping):
            raw = str(p.get("name") or "")
        elif isinstance(p, (tuple, list)):
            raw = str(p[0]) if p else ""
        else:
            raw = str(p)
        n = normalize(raw)
        if n and n not in BASE:
            names.add(n)
    return sorted(names)


def _covered(packages: Iterable[Any]) -> set[str]:
    out: set[str] = set(BASE)
    for p in packages:
        name = p.get("name") if isinstance(p, Mapping) else p
        if name:
            out |= expand(str(name))
    return out


def uncovered(packages: Iterable[Any], needs: Iterable[str]) -> list[str]:
    """The needs a capability's packages do not cover, sorted."""
    have = _covered(packages)
    return sorted({normalize(n) for n in needs} - have)


def covers(packages: Iterable[Any], needs: Iterable[str]) -> bool:
    return not uncovered(packages, needs)
