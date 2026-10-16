"""Validation of the common format.

Two stages, both returning every violation instead of stopping at the first one:

1. :func:`validate_model` — the in-memory ``ExportModel`` before it is written.
2. :func:`validate_export` — the written folder: schemas, index, paths, encoding.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterator, Mapping
from dataclasses import fields, is_dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from plcexport.common import normalize_path_key
from plcexport.format import connections as conn_format
from plcexport.format.canonical import split_front_matter
from plcexport.model import (
    CATEGORIES,
    CONNECTIONS,
    COVERAGE_STATES,
    HMI_UNIT_PREFIX,
    OPTIONAL_CATEGORIES,
    ExportModel,
    LibraryValidationError,
    is_local_xref_target,
    is_valid_reason,
    validate_library,
)

_GUID = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_OFFSET = re.compile(r"^\d+\.[0-7]$")  # data block offset
BINARY_TEXT = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_BINARY = BINARY_TEXT


class ExportInvalid(ValueError):
    def __init__(self, violations: list[str]) -> None:
        shown = "; ".join(violations[:5]) + (" …" if len(violations) > 5 else "")
        super().__init__(f"invalid export: {shown}")
        self.violations = violations


def _strings(obj: Any, path: str = "") -> Iterator[tuple[str, str]]:
    """Every string inside a model part, with a readable location."""
    if isinstance(obj, str):
        yield path, obj
    elif is_dataclass(obj) and not isinstance(obj, type):
        for f in fields(obj):
            yield from _strings(getattr(obj, f.name), f"{path}.{f.name}" if path else f.name)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(k, f"{path}[key]")
            yield from _strings(v, f"{path}[{k}]")
    elif isinstance(obj, (list, tuple, set, frozenset)):
        for i, v in enumerate(obj):
            yield from _strings(v, f"{path}[{i}]")


# ------------------------------------------------------------------ stage 1: model
def validate_model(m: ExportModel) -> list[str]:
    v: list[str] = []

    # unit names unique per kind
    for (kind, name), n in Counter((u.kind, u.name) for u in m.units).items():
        if n > 1:
            v.append(f"duplicate unit {kind} {name!r}")
    units = {u.name: u for u in m.units}

    # variables: (project, path_key) unique; declared in a known unit
    for key, n in Counter(normalize_path_key(x.symbolic_path) for x in m.variables).items():
        if n > 1:
            v.append(f"duplicate variable path_key {key!r}")
    for var in m.variables:
        if var.offset is not None and not _OFFSET.match(var.offset):
            v.append(f"variable {var.symbolic_path!r}: offset {var.offset!r} is not byte.bit")
        if var.declared_in not in units:
            v.append(f"variable {var.symbolic_path!r} declared in unknown unit {var.declared_in!r}")
        elif var.scope != "global_tag" and var.scope != units[var.declared_in].variable_scope:
            v.append(
                f"variable {var.symbolic_path!r}: scope {var.scope!r} differs from "
                f"variable_scope of {var.declared_in!r}"
            )

    # xrefs: target text set; refs resolve
    channels = {c.ref for c in m.hardware.channels}
    hmi_objects = {f"{s.name}/{o.name}" for s in m.hmi.screens for o in s.objects}
    for x in m.xrefs:
        if not x.target_text or not x.target_text.strip():
            v.append(f"xref from {x.from_unit!r} without target_text")
        if x.hmi_ref is not None:
            # "<screen>/<object>"; a screen name may itself contain "/" (TIA: "08-AnalogI/O")
            screen = x.from_unit.removeprefix(HMI_UNIT_PREFIX)
            if not x.from_unit.startswith(HMI_UNIT_PREFIX) or not x.hmi_ref.startswith(
                f"{screen}/"
            ):
                v.append(f"HMI xref {x.hmi_ref!r} must come from its screen, not {x.from_unit!r}")
        elif x.from_unit not in units:
            v.append(f"xref from unknown unit {x.from_unit!r}")
        if x.channel_ref is not None and x.channel_ref not in channels:
            v.append(f"xref {x.target_text!r}: channel_ref {x.channel_ref!r} does not exist")
        if x.hmi_ref is not None and x.hmi_ref not in hmi_objects:
            v.append(f"xref {x.target_text!r}: hmi_ref {x.hmi_ref!r} does not exist")
    modules = {mod.ref for mod in m.hardware.modules}
    for ch in m.hardware.channels:
        if ch.module_ref not in modules:
            v.append(f"channel {ch.ref!r}: module_ref {ch.module_ref!r} does not exist")

    # bodies belong to units
    for name in m.unit_bodies:
        if name not in units:
            v.append(f"body for unknown unit {name!r}")
    for t in m.texts:
        if t.unit not in units:
            v.append(f"text for unknown unit {t.unit!r}")
        if not t.lang:
            v.append(f"text without language in {t.unit!r}")
        if t.network_no is not None and t.element_ref is None:
            v.append(f"network text of {t.unit!r} NW{t.network_no} belongs in unit_bodies")

    # coverage: exactly the 7 categories with consistent states; `connections` is
    # optional, so that older exports and extractors without it stay valid
    cats = m.coverage.categories
    if set(cats) - set(OPTIONAL_CATEGORIES) != set(CATEGORIES):
        missing = sorted(set(CATEGORIES) - set(cats))
        extra = sorted(set(cats) - set(CATEGORIES) - set(OPTIONAL_CATEGORIES))
        v.append(f"coverage categories wrong (missing {missing}, unknown {extra})")
    counts = m.item_counts()
    for cat, cov in cats.items():
        if cov.state not in COVERAGE_STATES:
            v.append(f"coverage {cat}: unknown state {cov.state!r}")
        if cov.state == "delivered" and counts.get(cat, 0) == 0:
            v.append(f"coverage {cat}: delivered but no items")
        if cov.state == "unavailable" and not cov.reason:
            v.append(f"coverage {cat}: unavailable without reason")
        if cov.reason is not None and not is_valid_reason(cov.reason):
            v.append(f"coverage {cat}: invalid reason {cov.reason!r}")
    cm = m.connections
    if CONNECTIONS not in cats and (cm.item_count() or cm.findings):
        v.append("connection content without the coverage category 'connections'")
    v += conn_format.check_doc(
        conn_format.to_doc(cm),
        modules={x.ref for x in m.hardware.modules},
        networks={x.ref for x in m.hardware.networks},
        racks={x.ref for x in m.hardware.racks},
        units=units,
    )
    for g in m.coverage.gaps:
        if g.category not in (*CATEGORIES, *OPTIONAL_CATEGORIES):
            v.append(f"gap {g.item!r}: unknown category {g.category!r}")
        if not is_valid_reason(g.reason):
            v.append(f"gap {g.item!r}: invalid reason {g.reason!r}")

    # safety: flagged units and variables appear in the safety part, and vice versa
    safety_units = {u.name for u in m.units if u.safety}
    if safety_units != set(m.safety.units):
        v.append(
            "safety units differ from units with safety=true "
            f"(flagged only: {sorted(safety_units - set(m.safety.units))}, "
            f"listed only: {sorted(set(m.safety.units) - safety_units)})"
        )
    safety_tags = {x.symbolic_path for x in m.variables if x.safety}
    if safety_tags != set(m.safety.tags):
        v.append(
            "safety tags differ from variables with safety=true "
            f"(flagged only: {sorted(safety_tags - set(m.safety.tags))}, "
            f"listed only: {sorted(set(m.safety.tags) - safety_tags)})"
        )

    # native parts and the units they hold; library rules
    roots = {p.root: p for p in m.native_parts}
    if len(roots) != len(m.native_parts):
        v.append("two native parts share one root folder")
    for root, native in roots.items():
        if not re.fullmatch(r"[A-Za-z0-9_-]+", root) or root in {
            "units",
            "datatypes",
            "hmi",
            "safety",
            "platform",
            "parts",
        }:
            v.append(f"native part root {root!r} is not a free top-level folder name")
        if not native.files:
            v.append(f"native part {native.kind!r} has no files")
        for rel in native.files:
            if rel.startswith("/") or ".." in rel.split("/"):
                v.append(f"native part {native.kind!r}: path {rel!r} leaves the part")
            try:
                native.files[rel].decode("utf-8")
            except UnicodeDecodeError:
                v.append(f"native part {native.kind!r}: {rel!r} is not UTF-8 text")
    for u in m.units:
        heads = {f.split("/", 1)[0] for f in u.files}
        for root in heads & set(roots):
            absent = [
                f
                for f in u.files
                if f.split("/", 1)[0] == root and f.split("/", 1)[1] not in roots[root].files
            ]
            if absent:
                v.append(f"unit {u.name!r}: files {absent} not in native part {root!r}")
    if m.library is not None:
        try:
            validate_library(m.library)
        except LibraryValidationError as exc:
            v.append(f"library: {exc}")
    for k in m.library_links:
        if k.object_kind == "unit" and k.object not in units:
            v.append(f"library link from unknown unit {k.object!r}")

    # noise: no GUIDs or binary outside platform/
    for part in (
        "library",
        "library_links",
        "project",
        "units",
        "unit_bodies",
        "texts",
        "variables",
        "xrefs",
        "hardware",
        "safety",
        "hmi",
        "structure",
        "coverage",
    ):
        for where, s in _strings(getattr(m, part), part):
            if _GUID.search(s):
                v.append(f"GUID-like value outside platform/ at {where}")
            if _BINARY.search(s):
                v.append(f"binary/control characters at {where}")
    return v


# ------------------------------------------------------------------ stage 2: export folder
SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"
REQUIRED_FILES = (
    "README.md", "index.md", "manifest.json", "coverage.json", "structure.json", "symbols.json",
    "io.json", "hardware.json", "xref.json", "safety/safety.json", "hmi/hmi.json",
)  # fmt: skip
JSON_SCHEMAS = {
    "manifest.json": "manifest",
    "coverage.json": "coverage",
    "symbols.json": "symbols",
    "io.json": "io",
    "hardware.json": "hardware",
    "structure.json": "structure",
    "xref.json": "xref",
    "safety/safety.json": "safety",
    "hmi/hmi.json": "hmi",
    "library.json": "library",  # 005, optional
    "library_links.json": "library_links",  # 005, optional
}


@cache
def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def _schema_errors(name: str, data: Any, where: str) -> list[str]:
    return [
        f"{where}: {'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in sorted(_validator(name).iter_errors(data), key=lambda e: list(e.absolute_path))
    ]


def is_unit_file(rel: str) -> bool:
    return (
        (rel.startswith("units/") or rel.startswith("datatypes/"))
        and rel.endswith(".md")
        and (not rel.endswith("/index.md"))
    )


def _index_paths(text: str) -> list[str]:
    paths = []
    for line in text.splitlines():
        if line.startswith("## "):  # readable sections after the file list
            break
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        if len(cells) >= 3 and line.startswith("| ") and cells[2] not in ("Path", "---"):
            paths.append(cells[2])
    return paths


def native_parts_of(files: Mapping[str, bytes]) -> list[dict[str, Any]]:
    """The native parts the manifest lists; [] when there are none."""
    try:
        manifest = json.loads(files.get("manifest.json", b"{}").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return []
    parts = manifest.get("parts") if isinstance(manifest, dict) else None
    if not isinstance(parts, list):
        return []
    return [
        p
        for p in parts
        if isinstance(p, dict) and p.get("kind") != "common" and isinstance(p.get("path"), str)
    ]


def _in_part(rel: str, roots: set[str]) -> bool:
    return rel.split("/", 1)[0] in roots and "/" in rel


def validate_files(files: Mapping[str, bytes]) -> list[str]:
    """Validate an export given as ``{relative path: bytes}`` (contract §10)."""
    from plcexport.format.writer import native_part_checksum

    v: list[str] = []
    text: dict[str, str] = {}
    parts = native_parts_of(files)
    roots = {str(p["path"]) for p in parts}
    for declared in parts:
        root, kind = str(declared["path"]), declared.get("kind")
        members = {
            rel.split("/", 1)[1]: data for rel, data in files.items() if _in_part(rel, {root})
        }
        if not members:
            v.append(f"native part {kind!r}: folder {root}/ missing or empty")
        if declared.get("files") != len(members):
            v.append(
                f"native part {kind!r}: manifest says {declared.get('files')} files, "
                f"found {len(members)}"
            )
        if members and declared.get("checksum") != native_part_checksum(members):
            v.append(f"native part {kind!r}: checksum differs from the files in {root}/")
    for rel, data in sorted(files.items()):
        if _in_part(rel, roots):
            continue  # vendor files are kept byte-exact; the part checksum covers them
        if data.startswith(b"\xef\xbb\xbf"):
            v.append(f"{rel}: UTF-8 BOM")
        try:
            t = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            v.append(f"{rel}: not UTF-8 ({exc.reason} at byte {exc.start})")
            continue
        if "\r" in t:
            v.append(f"{rel}: CR line endings")
        if t and not t.endswith("\n"):
            v.append(f"{rel}: no final newline")
        if _BINARY.search(t):
            v.append(f"{rel}: binary/control characters")
        text[rel] = t
    for req in REQUIRED_FILES:
        if req not in files:
            v.append(f"missing required file {req}")

    parsed: dict[str, Any] = {}
    for rel, schema in JSON_SCHEMAS.items():
        if rel not in text:
            continue
        try:
            parsed[rel] = json.loads(text[rel])
        except json.JSONDecodeError as exc:
            v.append(f"{rel}: invalid JSON ({exc.msg} at line {exc.lineno})")
            continue
        v += _schema_errors(schema, parsed[rel], rel)

    units: set[str] = set()
    for rel in sorted(r for r in text if r.startswith("parts/") and r.endswith(".json")):
        try:
            rows = json.loads(text[rel])
        except json.JSONDecodeError as exc:
            v.append(f"{rel}: invalid JSON ({exc.msg} at line {exc.lineno})")
            continue
        v += _schema_errors("part_units", rows, rel)
        for row in rows if isinstance(rows, list) else []:
            units.add(str(row.get("name")))
            for f in row.get("files") or []:
                if f not in files:
                    v.append(f"{rel}: unit {row.get('name')!r} file {f} missing")
    for rel in sorted(r for r in text if is_unit_file(r)):
        try:
            fm, _ = split_front_matter(text[rel])
        except (ValueError, yaml.YAMLError) as exc:
            v.append(f"{rel}: front matter: {exc}")
            continue
        v += _schema_errors("unit_front_matter", fm, rel)
        units.add(str(fm.get("name")))
        n_lines = text[rel].count("\n")
        lines = text[rel].split("\n")
        for nw in fm.get("networks") or []:
            start, end = nw.get("line_start", 0), nw.get("line_end", 0)
            if not (1 <= start <= end <= n_lines):
                v.append(f"{rel}: NW{nw.get('no')} line span {start}-{end} outside the file")
            elif not lines[start - 1].startswith(f"## NW {nw.get('no')}"):
                v.append(f"{rel}: NW{nw.get('no')} line_start does not point at its heading")
    screens: set[str] = set()
    for rel in sorted(r for r in text if r.startswith("hmi/screens/") and r.endswith(".md")):
        try:
            fm, _ = split_front_matter(text[rel])
        except (ValueError, yaml.YAMLError) as exc:
            v.append(f"{rel}: front matter: {exc}")
            continue
        v += _schema_errors("screen_front_matter", fm, rel)
        screens |= {f"{fm.get('name')}/{o.get('name')}" for o in fm.get("objects") or []}

    # index.md (plus per-folder indexes) lists exactly the files present
    if "index.md" in text:
        listed = _index_paths(text["index.md"])
        for sub in [p for p in listed if p.endswith("/index.md") and p in text]:
            listed += _index_paths(text[sub])
        present = set(files) - {"index.md"}
        for p in sorted(set(listed) - present):
            v.append(f"index.md lists missing file {p}")
        # native files are listed per unit (one main file each), not one by one
        for p in sorted(r for r in present - set(listed) if not _in_part(r, roots)):
            v.append(f"index.md does not list {p}")
        for p, n in Counter(listed).items():
            if n > 1:
                v.append(f"index.md lists {p} {n} times")

    # references between files resolve
    channels = {c.get("ref") for c in (parsed.get("hardware.json") or {}).get("channels", [])}
    if isinstance(parsed.get("xref.json"), list):
        local = sorted(
            {
                str(x.get("target"))
                for x in parsed["xref.json"]
                if x.get("target_kind") == "variable"
                and is_local_xref_target(str(x.get("target")), str(x.get("access")))
            }
        )
        if local:
            v.append(
                f"xref.json: {len(local)} block-local, stack, register or indirect target(s) "
                f", e.g. {', '.join(local[:3])}"
            )
        for x in parsed["xref.json"]:
            src = str(x.get("from_unit"))
            if not src.startswith(HMI_UNIT_PREFIX) and src not in units:
                v.append(f"xref.json: from_unit {src!r} has no unit file")
            if "channel_ref" in x and x["channel_ref"] not in channels:
                v.append(f"xref.json: channel_ref {x['channel_ref']!r} not in hardware.json")
            if "hmi_ref" in x and x["hmi_ref"] not in screens:
                v.append(f"xref.json: hmi_ref {x['hmi_ref']!r} not in hmi/screens")
    io = parsed.get("io.json")
    if isinstance(io, dict):
        for row in [*io.get("inputs", []), *io.get("outputs", [])]:
            if "channel_ref" in row and row["channel_ref"] not in channels:
                v.append(f"io.json: channel_ref {row['channel_ref']!r} not in hardware.json")
    if conn_format.FILE in text:  # optional file
        try:
            doc = json.loads(text[conn_format.FILE])
        except json.JSONDecodeError as exc:
            v.append(f"{conn_format.FILE}: invalid JSON ({exc.msg} at line {exc.lineno})")
        else:
            hw = parsed.get("hardware.json") or {}
            v += conn_format.check_doc(
                doc,
                modules={x.get("ref") for x in hw.get("modules", [])},
                networks={x.get("ref") for x in hw.get("networks", [])},
                racks={x.get("ref") for x in hw.get("racks", [])},
                units=units,
            )
    safety = parsed.get("safety/safety.json")
    if isinstance(safety, dict):
        for u in safety.get("units", []):
            if u not in units:
                v.append(f"safety/safety.json: unit {u!r} has no unit file")
    return v


def validate_export(export_dir: Path) -> list[str]:
    """Validate an export folder; an empty list means it conforms (``plcexport validate``)."""
    if not export_dir.is_dir():
        return [f"{export_dir} is not a folder"]
    files = {
        p.relative_to(export_dir).as_posix(): p.read_bytes()
        for p in sorted(export_dir.rglob("*"))
        if p.is_file()
    }
    return validate_files(files)
