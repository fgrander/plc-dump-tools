"""Canonical serializers.

Byte-stable output is what keeps diffs of an export repository limited to real changes:

* JSON: sorted keys, 2-space indent, no ASCII escaping, LF, final newline.
* YAML front matter: keys in the order given by the caller, list items as one flow-style line.
* File names: kept when file-system safe; otherwise unsafe characters become ``_``. A short hash
  suffix is added only when two names collide (also case-insensitively, for Windows).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from typing import Any

import yaml


# ------------------------------------------------------------------ JSON
def dump_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def compact(d: Mapping[str, Any]) -> dict[str, Any]:
    """Drop keys whose value is ``None`` or an empty collection (LLM-efficient rows).

    ``False`` is kept: "not retentive" and "unknown" are different facts.
    """
    return {k: v for k, v in d.items() if v is not None and v not in ({}, [], ())}


def texts(t: Mapping[str, str] | None) -> dict[str, str]:
    """Multilingual text object with languages sorted (contract §1)."""
    return {k: t[k] for k in sorted(t)} if t else {}


# ------------------------------------------------------------------ YAML front matter
class Flow(dict[str, Any]):
    """A mapping emitted on one line: ``{name: X, type: Real}``."""


class _Dumper(yaml.SafeDumper):
    pass


def _represent_flow(dumper: yaml.SafeDumper, data: Flow) -> yaml.Node:
    return dumper.represent_mapping("tag:yaml.org,2002:map", data.items(), flow_style=True)


def _represent_dict(dumper: yaml.SafeDumper, data: dict[str, Any]) -> yaml.Node:
    return dumper.represent_mapping("tag:yaml.org,2002:map", data.items())


_Dumper.add_representer(Flow, _represent_flow)
_Dumper.add_representer(dict, _represent_dict)
_Dumper.add_representer(tuple, lambda d, data: d.represent_list(list(data)))


def dump_yaml(data: Mapping[str, Any]) -> str:
    """YAML in insertion order; ``Flow`` mappings stay on one line; never wraps long lines."""
    out = yaml.dump(
        dict(data),
        Dumper=_Dumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=1_000_000,
        line_break="\n",
    )
    return str(out)


def front_matter(data: Mapping[str, Any], key_order: Iterable[str]) -> str:
    """``---`` block with the keys of ``data`` in ``key_order`` (unknown keys are an error)."""
    order = list(key_order)
    unknown = set(data) - set(order)
    if unknown:
        raise ValueError(f"front matter keys not in the fixed order: {sorted(unknown)}")
    ordered = {k: data[k] for k in order if k in data}
    return "---\n" + dump_yaml(ordered) + "---\n"


def split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Inverse of :func:`front_matter`: returns (data, body)."""
    if not text.startswith("---\n"):
        raise ValueError("missing front matter")
    end = text.find("\n---\n", 3)
    if end < 0:
        raise ValueError("unterminated front matter")
    data = yaml.safe_load(text[4 : end + 1]) or {}
    if not isinstance(data, dict):
        raise ValueError("front matter is not a mapping")
    return data, text[end + 5 :]


# ------------------------------------------------------------------ file names
_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
_RESERVED = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$", re.IGNORECASE)


def sanitize(name: str) -> str:
    """File-system safe form of an identifier; unchanged when it already is safe."""
    s = _UNSAFE.sub("_", name).strip()
    s = s.rstrip(". ")
    if s.startswith("."):
        s = "_" + s[1:]
    if not s:
        s = "_"
    if _RESERVED.match(s):
        s = "_" + s
    return s


def _short_hash(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()[:6]


def file_names(names: Iterable[str]) -> dict[str, str]:
    """Map identifiers to unique file stems.

    In a group of names that collide (case-insensitively) after sanitizing, the first name in
    sort order whose stem equals the name itself keeps it; every other name gets ``-<hash6>``.
    """
    groups: dict[str, list[str]] = {}
    for n in sorted(set(names)):
        groups.setdefault(sanitize(n).casefold(), []).append(n)
    out: dict[str, str] = {}
    for members in groups.values():
        keeper = next((m for m in members if sanitize(m) == m), None)
        if len(members) == 1:
            keeper = members[0]
        for m in members:
            out[m] = sanitize(m) if m == keeper else f"{sanitize(m)}-{_short_hash(m)}"
    return out
