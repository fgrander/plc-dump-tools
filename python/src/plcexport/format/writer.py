"""``ExportModel`` -> common format v1 files (contracts/common-format.md).

:func:`render` is pure: it returns ``{relative path: text}`` and is fully deterministic apart from
``manifest.exported_at`` (``manifest.source.path`` is what the caller passes,
relative to the scanned root in a batch). :func:`write_atomic`
puts the files on disk so that an existing export is never left half overwritten.
"""

from __future__ import annotations

import hashlib
import shutil
import sys
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from plcexport.format import connections as conn_format
from plcexport.format.canonical import (
    Flow,
    compact,
    dump_json,
    file_names,
    front_matter,
    texts,
)
from plcexport.format.readme import render_readme
from plcexport.model import (
    CATEGORIES,
    CONNECTIONS,
    FORMAT_VERSION,
    HMI_UNIT_PREFIX,
    OPTIONAL_CATEGORIES,
    BodyNetwork,
    ExportModel,
    ExportUnit,
    ExportVariable,
    HmiScreen,
    LibraryLink,
    LibraryModel,
    NativePart,
    UnitBody,
    xref_key,
)

UNIT_KEYS = (
    "name", "kind", "number", "language", "original_language", "protected", "safety",
    "parse_quality", "folder", "instance_of", "attributes", "title", "comment", "path_prefix",
    "variable_scope", "interface", "networks", "element_texts", "part",
)  # fmt: skip
SCREEN_KEYS = ("name", "device", "texts", "objects")
KIND_ORDER = ("OB", "FB", "FC", "DB", "IDB", "TAG_TABLE", "OTHER", "UDT")
SECTION_ORDER = ("IN", "OUT", "IN_OUT", "STATIC", "TEMP", "CONSTANT", "RETURN")
PROTECTED_LINE = "> protected – logic not exported"


@dataclass(frozen=True)
class ManifestInfo:
    """Run metadata the core adds around the model (contract §3)."""

    source_path: str
    checksum: str  # "sha256:<hex>"
    exported_at: datetime
    source_kind: str = "folder"
    route: str = "local"
    worker: str | None = None
    vendor_software: str | None = None
    fallback_from: tuple[str, str] | None = None  # (extractor id, reason)


@dataclass
class _UnitFile:
    path: str
    text: str


@dataclass
class _Rendered:
    files: list[_UnitFile] = field(default_factory=list)
    # network no -> (file path, heading line, code lines with their file line numbers)
    networks: dict[int, tuple[str, int, list[tuple[int, str]]]] = field(default_factory=dict)


# ------------------------------------------------------------------ native parts
PART_LABELS = {"siemens-simatic-sd": "SD"}
PART_UNIT_KEYS = (
    "name", "kind", "number", "language", "folder", "protected", "safety", "instance_of",
    "attributes", "files",
)  # fmt: skip


def native_part_checksum(files: Mapping[str, bytes]) -> str:
    """sha256 over the sorted paths and contents of a native part (manifest ``parts``)."""
    h = hashlib.sha256()
    for rel in sorted(files):
        data = files[rel]
        h.update(rel.encode("utf-8") + b"\0" + str(len(data)).encode("ascii") + b"\0" + data)
    return "sha256:" + h.hexdigest()


def native_root_of(
    u: ExportUnit, roots: Mapping[str, NativePart], bodies: Mapping[str, Any]
) -> str | None:
    """The native part root holding unit ``u`` (all its files below one root, no rendered body)."""
    if not u.files or u.name in bodies:
        return None
    heads = {f.split("/", 1)[0] for f in u.files}
    return next(iter(heads)) if len(heads) == 1 and next(iter(heads)) in roots else None


def _part_unit_row(u: ExportUnit) -> dict[str, Any]:
    row = {
        "name": u.name,
        "kind": u.kind,
        "number": u.number,
        "language": u.language,
        "folder": u.folder,
        "protected": u.protected or None,
        "safety": u.safety or None,
        "instance_of": u.instance_of,
        "attributes": dict(sorted(u.attributes.items())) if u.attributes else None,
        "files": list(u.files),
    }
    return {k: row[k] for k in PART_UNIT_KEYS if row[k] is not None}


def _library_json(lib: LibraryModel) -> dict[str, Any]:
    return {
        "name": lib.name,
        "version": lib.version,
        "kind": lib.kind,
        "company": lib.company,
        "duplicate_of": lib.duplicate_of,
        "types": [
            {
                "name": t.name,
                "folder": t.folder,
                "kind": t.kind,
                "versions": [
                    {
                        "version": v.version,
                        "status": v.status,
                        "author": v.author,
                        "date": v.date,
                        "comment": texts(v.comment),
                        "content_part": v.content_part,
                        "content_path": v.content_path,
                        "gap_reason": v.gap_reason,
                    }
                    for v in t.versions
                ],
            }
            for t in lib.types
        ],
        "master_copies": [
            {
                "name": c.name,
                "folder": c.folder,
                "objects": list(c.objects),
                "content_path": c.content_path,
            }
            for c in lib.master_copies
        ],
    }


def link_fact_row(k: LibraryLink) -> dict[str, Any]:
    """A link fact before ``relink`` compared it (contract §4)."""
    return {
        "object": k.object,
        "object_kind": k.object_kind,
        "type_name": k.type_name,
        "type_folder": k.type_folder,
        "version": k.version,
        "status": k.status,
        "original_library": k.original_library,
        "origin": "unknown_library" if k.original_library else "project_only",
        "library": None,
        "comparison": "not_compared",
        "newest_released": None,
    }


# ------------------------------------------------------------------ small helpers
def _size(n: int) -> str:
    return str(n) if n < 1000 else f"{n / 1024:.1f}k"


def _cell(s: str | None) -> str:
    return " ".join((s or "").split()).replace("|", "\\|")


def _first_text(t: Mapping[str, str], langs: tuple[str, ...]) -> str | None:
    for lang in (*langs, *sorted(t)):
        if t.get(lang):
            return t[lang]
    return None


def _texts_cell(t: Mapping[str, str]) -> str:
    return " · ".join(f"{lang}: {_cell(t[lang])}" for lang in sorted(t))


def _comment_lines(t: Mapping[str, str]) -> list[str]:
    out = []
    for lang in sorted(t):
        first, *rest = t[lang].split("\n") or [""]
        out.append(f"> {lang}: {first}".rstrip())
        out += [f"> {line}".rstrip() for line in rest]
    return out


def _title(name: str, title: str | None) -> str:
    return f"# {name} — {title}" if title else f"# {name}"


# ------------------------------------------------------------------ interface
def _offset_key(offset: str | None, position: int | None = None) -> tuple[int, int, int]:
    """members with an offset in rising address order, then members with
    a declaration position in that order, then all others (sorted by name by the caller)."""
    if offset is not None:
        byte, bit = offset.split(".")
        return (0, int(byte), int(bit))
    if position is not None:
        return (1, position, 0)
    return (2, 0, 0)


def _member_tree(unit: ExportUnit, variables: list[ExportVariable]) -> list[Flow]:
    """Nested interface members (front matter) built from the flat variable list."""
    by_parent: dict[str | None, list[ExportVariable]] = {}
    for v in variables:
        by_parent.setdefault(v.parent_path, []).append(v)

    def build(parent: str | None) -> list[Flow]:
        prefix = parent if parent is not None else unit.path_prefix
        out = []
        siblings = sorted(
            by_parent.get(parent, []),
            key=lambda v: (
                SECTION_ORDER.index(v.section)
                if v.section in SECTION_ORDER
                else len(SECTION_ORDER),
                _offset_key(v.offset, v.position),
                v.symbolic_path,
            ),
        )
        for v in siblings:
            if prefix is not None and v.symbolic_path.startswith(prefix + "."):
                name, explicit = v.symbolic_path[len(prefix) + 1 :], None
            else:
                name, explicit = v.symbolic_path, v.symbolic_path
            row: dict[str, Any] = {
                "offset": v.offset,  # first, like the address column of a DB
                "name": name,
                "type": v.data_type,
                "path": explicit,
                "section": v.section,
                "start": v.start_value,
                "retain": v.retain,
                "comment": texts(v.comments),
                "dims": v.array_dims,
                "address": v.address,
                "io_direction": v.io_direction,
                "accessible": v.ext_accessible,
                "visible": v.ext_visible,
                "writable": v.ext_writable,
                "safety": True if v.safety else None,
                "members": build(v.symbolic_path),
            }
            out.append(Flow(compact(row)))
        return out

    return build(None)


def _has_offsets(members: list[Flow]) -> bool:
    return any("offset" in m or _has_offsets(m.get("members") or []) for m in members)


def _interface_rows(members: list[Flow], depth_name: str = "", offsets: bool = False) -> list[str]:
    rows = []
    for m in members:
        name = f"{depth_name}.{m['name']}" if depth_name else str(m["name"])
        offset = f"| {_cell(m.get('offset'))} " if offsets else ""
        rows.append(
            f"{offset}| {_cell(m.get('section'))} | {_cell(name)} | {_cell(m['type'])} | "
            f"{_cell(m.get('start'))} | {_texts_cell(m.get('comment') or {})} |"
        )
        rows += _interface_rows(m.get("members") or [], name, offsets)
    return rows


# ------------------------------------------------------------------ unit files
def _network_block(nw: BodyNetwork, lang: str, langs: tuple[str, ...]) -> list[str]:
    title = _first_text(nw.title, langs)
    lines = [f"## NW {nw.no} — {title}" if title else f"## NW {nw.no}"]
    lines += _comment_lines(nw.comment)
    lines += ["", f"```{lang}", *nw.code.split("\n"), "```", ""]
    return lines


def _unit_head(
    unit: ExportUnit,
    title: str | None,
    comment: Mapping[str, str],
    members: list[Flow],
    n_tags: int,
    part: tuple[int, int] | None,
) -> list[str]:
    if part is not None and part[0] > 1:
        return ["", f"{_title(unit.name, title)} (part {part[0]}/{part[1]})", ""]
    lines = ["", _title(unit.name, title), ""]
    if comment:
        lines += [*_comment_lines(comment), ""]
    if unit.instance_of:
        lines += [f"Instance of `{unit.instance_of}`.", ""]
    if unit.kind == "TAG_TABLE":
        lines += ["## Tags", "", f"See `symbols.json`, table `{unit.name}` ({n_tags} tags).", ""]
    if members:
        heading = "## Members" if unit.kind == "UDT" else "## Interface"
        offsets = _has_offsets(members)  # column only when the layout is known
        lines += [
            heading,
            "| Offset | Section | Name | Type | Start | Comment |"
            if offsets
            else "| Section | Name | Type | Start | Comment |",
            "|---|---|---|---|---|---|" if offsets else "|---|---|---|---|---|",
            *_interface_rows(members, offsets=offsets),
            "",
        ]
    return lines


def _render_unit(
    path_stem: str,
    unit: ExportUnit,
    body: UnitBody | None,
    m: ExportModel,
    members: list[Flow],
    n_tags: int,
    split_bytes: int,
) -> _Rendered:
    langs = m.project.languages
    block = [t for t in m.texts if t.unit == unit.name and t.element_ref is None]
    title_t = {t.lang: t.text for t in block if t.kind == "title"}
    comment_t = {t.lang: t.text for t in block if t.kind == "comment"}
    elements = [t for t in m.texts if t.unit == unit.name and t.element_ref is not None]
    title = _first_text(title_t, langs)
    networks = list(body.networks) if body and not unit.protected else []
    lang = body.language if body else "none"

    def fm_data(nws: list[BodyNetwork], spans: dict[int, tuple[int, int]], part: str | None) -> Any:
        return compact(
            {
                "name": unit.name,
                "kind": unit.kind,
                "number": unit.number,
                "language": lang,
                "original_language": unit.language,
                "protected": unit.protected,
                "safety": True if unit.safety else None,
                "parse_quality": unit.parse_quality,
                "folder": unit.folder,
                "instance_of": unit.instance_of,
                "attributes": {k: unit.attributes[k] for k in sorted(unit.attributes)},
                "title": texts(title_t),
                "comment": texts(comment_t),
                "path_prefix": unit.path_prefix,
                "variable_scope": unit.variable_scope,
                "interface": members,
                "networks": [
                    Flow(
                        compact(
                            {
                                "no": nw.no,
                                "line_start": spans[nw.no][0],
                                "line_end": spans[nw.no][1],
                                "title": texts(nw.title),
                                "comment": texts(nw.comment),
                            }
                        )
                    )
                    for nw in nws
                ],
                "element_texts": [
                    Flow(
                        network_no=t.network_no or 0,
                        element_ref=t.element_ref,
                        kind=t.kind,
                        lang=t.lang,
                        text=t.text,
                    )
                    for t in sorted(
                        elements,
                        key=lambda t: (t.network_no or 0, t.element_ref or "", t.kind, t.lang),
                    )
                ],
                "part": part,
            }
        )

    def render_part(
        nws: list[BodyNetwork], part: tuple[int, int] | None
    ) -> tuple[str, dict[int, tuple[int, list[tuple[int, str]]]]]:
        body_lines = _unit_head(unit, title, comment_t, members, n_tags, part)
        offsets: dict[int, tuple[int, int, int, int]] = {}  # no -> (head, code0, code1, end)
        for nw in nws:
            start = len(body_lines)
            block_lines = _network_block(nw, lang, langs)
            body_lines += block_lines
            code0 = start + 2 + len(_comment_lines(nw.comment)) + 1
            n_code = len(nw.code.split("\n"))
            offsets[nw.no] = (start, code0, code0 + n_code, start + len(block_lines) - 2)
        if not nws:
            if unit.protected:
                body_lines += [PROTECTED_LINE, ""]
            elif body is not None and body.code is not None:
                body_lines += ["## Source", "", f"```{lang}", *body.code.split("\n"), "```", ""]
        part_s = f"{part[0]}/{part[1]}" if part else None
        placeholder = {nw.no: (1, 1) for nw in nws}
        fm_lines = front_matter(fm_data(nws, placeholder, part_s), UNIT_KEYS).count("\n")
        spans = {no: (fm_lines + o[0] + 1, fm_lines + o[3] + 1) for no, o in offsets.items()}
        fm = front_matter(fm_data(nws, spans, part_s), UNIT_KEYS)
        assert fm.count("\n") == fm_lines  # line numbers never change the line count
        text = fm + "\n".join(body_lines).rstrip("\n") + "\n"
        code = {
            no: (
                fm_lines + o[0] + 1,
                [(fm_lines + i + 1, body_lines[i]) for i in range(o[1], o[2])],
            )
            for no, o in offsets.items()
        }
        return text, code

    out = _Rendered()
    text, code = render_part(networks, None)
    if len(text.encode("utf-8")) <= split_bytes or len(networks) < 2:
        out.files.append(_UnitFile(f"{path_stem}.md", text))
        for no, (head, lines) in code.items():
            out.networks[no] = (f"{path_stem}.md", head, lines)
        return out

    # split at network boundaries; the part count is fixed afterwards
    groups: list[list[BodyNetwork]] = [[]]
    for nw in networks:
        trial = [*groups[-1], nw]
        n_guess = 99  # the widest "n/N" while sizing
        if groups[-1] and len(render_part(trial, (len(groups), n_guess))[0].encode()) > split_bytes:
            groups.append([nw])
        else:
            groups[-1] = trial
    for i, g in enumerate(groups, 1):
        path = f"{path_stem}.part-{i}.md"
        text, code = render_part(g, (i, len(groups)))
        out.files.append(_UnitFile(path, text))
        for no, (head, lines) in code.items():
            out.networks[no] = (path, head, lines)
    return out


# ------------------------------------------------------------------ screens
def _render_screen(s: HmiScreen, langs: tuple[str, ...]) -> str:
    objects = [
        Flow(compact({"name": o.name, "type": o.type, "tag_bindings": list(o.tag_bindings)}))
        for o in s.objects
    ]
    fm = front_matter(
        {"name": s.name, "device": s.device, "texts": texts(s.texts), "objects": objects},
        SCREEN_KEYS,
    )
    lines = [
        "",
        _title(f"Screen {s.name}", _first_text(s.texts, langs)),
        "",
        f"Device: `{s.device}`",
        "",
        "| Object | Type | Tags |",
        "|---|---|---|",
    ]
    lines += [
        f"| {_cell(o.name)} | {_cell(o.type)} | {_cell(', '.join(o.tag_bindings))} |"
        for o in s.objects
    ]
    return fm + "\n".join(lines) + "\n"


# ------------------------------------------------------------------ tables
def _rows(items: Iterable[Any], rename: Mapping[str, str] | None = None) -> list[dict[str, Any]]:
    out = []
    for it in items:
        d = asdict(it)
        for old, new in (rename or {}).items():
            d[new] = d.pop(old)
        out.append(
            compact(
                {
                    k: (
                        texts(v)
                        if k in {"texts", "text", "comment"}
                        else list(v)
                        if isinstance(v, tuple)
                        else v
                    )
                    for k, v in d.items()
                }
            )
        )
    return out


def _symbols(m: ExportModel) -> list[dict[str, Any]]:
    rows = [
        compact(
            {
                "symbol": v.symbolic_path,
                "table": v.declared_in,
                "data_type": v.data_type,
                "scope": v.scope,
                "address": v.address,
                "initial": v.start_value,
                "retain": v.retain,
                "comment": texts(v.comments),
                "io_direction": v.io_direction,
                "accessible": v.ext_accessible,
                "visible": v.ext_visible,
                "writable": v.ext_writable,
                "safety": True if v.safety else None,
                "parent": v.parent_path,
                "dims": v.array_dims,
            }
        )
        for v in m.variables
        if v.scope == "global_tag"
    ]
    return sorted(rows, key=lambda r: r["symbol"])


def _io(m: ExportModel) -> dict[str, list[dict[str, Any]]]:
    by_symbol = {c.symbol: c.ref for c in m.hardware.channels if c.symbol}
    by_address = {c.address: c.ref for c in m.hardware.channels}
    out: dict[str, list[dict[str, Any]]] = {"inputs": [], "outputs": []}
    for v in m.variables:
        if v.scope != "global_tag" or v.io_direction not in ("input", "output") or not v.address:
            continue
        out[f"{v.io_direction}s"].append(
            compact(
                {
                    "symbol": v.symbolic_path,
                    "address": v.address,
                    "data_type": v.data_type,
                    "comment": texts(v.comments),
                    "channel_ref": by_symbol.get(v.symbolic_path) or by_address.get(v.address),
                }
            )
        )
    for rows in out.values():
        rows.sort(key=lambda r: (r["address"], r["symbol"]))
    return out


def _xref_rows(m: ExportModel, lines: Mapping[str, _Rendered]) -> list[dict[str, Any]]:
    rows = []
    for x in sorted(m.xrefs, key=xref_key):
        line = None
        rendered = lines.get(x.from_unit)
        if rendered is not None and x.network_no in rendered.networks:
            _, head, code = rendered.networks[x.network_no]
            if x.line is not None and 1 <= x.line <= len(code):  # line within the network code
                line = code[x.line - 1][0]
            else:
                target = " ".join(x.target_text.split())  # STL pads operands: "C      3"
                line = next((n for n, text in code if target in " ".join(text.split())), head)
        rows.append(
            compact(
                {
                    "target": x.target_text,
                    "target_kind": x.target_kind,
                    "from_unit": x.from_unit,
                    "network_no": x.network_no,
                    "line": line,
                    "access": x.access,
                    "via_param": x.via_param,
                    "channel_ref": x.channel_ref,
                    "hmi_ref": x.hmi_ref,
                }
            )
        )
    # order by the position in the export, not by the model's (platform-specific) line numbers
    rows.sort(
        key=lambda r: (r["from_unit"], r.get("network_no", 0), r.get("line", 0), r["target"],
                       r["access"], r.get("via_param", ""))
    )  # fmt: skip
    return rows


# ------------------------------------------------------------------ index
def _index(
    m: ExportModel,
    files: Mapping[str, str],
    entries: list[tuple[str, str, str, str]],  # (cat, name, path, title)
    group_threshold: int,
) -> dict[str, str]:
    """Top-level ``index.md`` (+ per-directory indexes above the threshold)."""
    p = m.project
    head = [
        f"# Index — {p.line_or_machine or p.device or p.controller or 'project'}  "
        f"({p.platform_id} {p.platform_version or ''}".rstrip()
        + f", {p.controller or '-'})",
        "See README.md for how to read this export.",
        "",
        "| Cat | Name | Path | Size | Title |",
        "|---|---|---|---|---|",
    ]

    def row(cat: str, name: str, path: str, title: str, content: str | None) -> str:
        size = _size(len(content.encode("utf-8"))) if content is not None else ""
        return f"| {cat} | {_cell(name)} | {path} | {size} | {_cell(title)[:40]} |"

    unit_entries = [e for e in entries if e[2].startswith(("units/", "datatypes/"))]
    other = [e for e in entries if e not in unit_entries]
    out: dict[str, str] = {}
    lines = list(head)
    if len(unit_entries) > group_threshold:
        groups: dict[str, list[tuple[str, str, str, str]]] = {}
        for e in unit_entries:
            groups.setdefault(e[2].rsplit("/", 1)[0], []).append(e)
        for directory, members in groups.items():
            sub = [
                f"# Index — {directory}",
                "",
                "| Cat | Name | Path | Size | Title |",
                "|---|---|---|---|---|",
            ]
            sub += [row(c, n, path, t, files[path]) for c, n, path, t in members]
            out[f"{directory}/index.md"] = "\n".join(sub) + "\n"
            kind = members[0][0]
            lines.append(
                row(
                    kind,
                    f"{len(members)} {kind} units",
                    f"{directory}/index.md",
                    "",
                    out[f"{directory}/index.md"],
                )
            )
    else:
        lines += [row(c, n, path, t, files[path]) for c, n, path, t in unit_entries]
    lines += [
        row(c, n, path, t, None if path == "manifest.json" else files[path])
        for c, n, path, t in other
    ]
    out["index.md"] = "\n".join(lines) + "\n"
    return out


# ------------------------------------------------------------------ render
def render(
    model: ExportModel,
    info: ManifestInfo,
    split_bytes: int = 40 * 1024,
    group_threshold: int = 500,
) -> dict[str, str]:
    m = model.sorted()
    langs = m.project.languages
    files: dict[str, str] = {}
    entries: list[tuple[str, str, str, str]] = []

    # program units and data types; units whose content is a native part are only listed
    roots = {p.root: p for p in m.native_parts}
    native_units: dict[str, list[ExportUnit]] = {}
    by_dir: dict[str, list[ExportUnit]] = {}
    for u in m.units:
        root = native_root_of(u, roots, m.unit_bodies)
        if root is not None:
            native_units.setdefault(root, []).append(u)
            continue
        by_dir.setdefault("datatypes" if u.kind == "UDT" else f"units/{u.kind}", []).append(u)
    rendered: dict[str, _Rendered] = {}
    tag_counts: dict[str, int] = {}
    for v in m.variables:
        if v.scope == "global_tag":
            tag_counts[v.declared_in] = tag_counts.get(v.declared_in, 0) + 1
    for directory in sorted(by_dir, key=lambda d: KIND_ORDER.index(by_dir[d][0].kind)):
        units = by_dir[directory]
        stems = file_names(u.name for u in units)
        for u in sorted(units, key=lambda u: u.name):
            members = _member_tree(
                u, [v for v in m.variables if v.declared_in == u.name and v.scope != "global_tag"]
            )
            r = _render_unit(
                f"{directory}/{stems[u.name]}",
                u,
                m.unit_bodies.get(u.name),
                m,
                members,
                tag_counts.get(u.name, 0),
                split_bytes,
            )
            rendered[u.name] = r
            title = _first_text(
                {t.lang: t.text for t in m.texts if t.unit == u.name and t.kind == "title"},
                langs,
            ) or _first_text(
                {t.lang: t.text for t in m.texts if t.unit == u.name and t.kind == "comment"},
                langs,
            )
            for f in r.files:
                files[f.path] = f.text
                entries.append((u.kind, u.name, f.path, title or ""))

    # native parts: vendor files unchanged, plus the list of their units
    for root, part in sorted(roots.items()):
        for rel, data in part.files.items():
            files[f"{root}/{rel}"] = data.decode("utf-8")
        label = PART_LABELS.get(part.kind, part.kind)
        units_here = sorted(native_units.get(root, []), key=lambda u: (u.kind, u.name))
        files[f"parts/{part.kind}.json"] = dump_json([_part_unit_row(u) for u in units_here])
        for u in units_here:
            main = next((f for f in u.files if f.endswith(".s7dcl")), u.files[0])
            title = _first_text(
                {t.lang: t.text for t in m.texts if t.unit == u.name and t.kind == "title"}, langs
            )
            entries.append((f"unit ({label})", u.name, main, title or ""))

    # tables
    files["symbols.json"] = dump_json(_symbols(m))
    files["io.json"] = dump_json(_io(m))
    hw = m.hardware
    files["hardware.json"] = dump_json(
        {
            "controllers": _rows(hw.controllers),
            "racks": _rows(hw.racks),
            "modules": _rows(hw.modules),
            "channels": _rows(hw.channels),
            "networks": _rows(hw.networks),
        }
    )
    st = m.structure
    files["structure.json"] = dump_json(
        {"devices": _rows(st.devices), "tasks": _rows(st.tasks), "folders": _rows(st.folders)}
    )
    files["xref.json"] = dump_json(_xref_rows(m, rendered))
    sf = m.safety
    files["safety/safety.json"] = dump_json(
        {
            "units": list(sf.units),
            "tags": list(sf.tags),
            "parameters": _rows(sf.parameters),
            "signatures": _rows(sf.signatures),
        }
    )
    hmi = m.hmi
    files["hmi/hmi.json"] = dump_json(
        {
            "devices": _rows(hmi.devices),
            "alarms": _rows(hmi.alarms, {"alarm_class": "class", "texts": "text"}),
            "hmi_tags": _rows(hmi.hmi_tags),
            "recipes": _rows(hmi.recipes),
        }
    )
    screen_keys = [s.name for s in hmi.screens]
    if len(set(screen_keys)) != len(screen_keys):
        screen_keys = [f"{s.device}_{s.name}" for s in hmi.screens]
    stems = file_names(screen_keys)
    screen_entries = []
    for key, s in zip(screen_keys, hmi.screens, strict=True):
        path = f"hmi/screens/{stems[key]}.md"
        files[path] = _render_screen(s, langs)
        screen_entries.append(("screen", s.name, path, _first_text(s.texts, langs) or ""))
    if m.platform:
        files[f"platform/{m.project.platform_id}/platform.json"] = dump_json(m.platform)
    for name, content in m.platform_files.items():
        files[f"platform/{m.project.platform_id}/{name}"] = dump_json(content)
    if m.library is not None:
        files["library.json"] = dump_json(_library_json(m.library))
    if m.library is not None or m.library_links:
        files["library_links.json"] = dump_json(
            {"compared_with": [], "links": [link_fact_row(k) for k in m.library_links]}
        )
    cm = m.connections
    if cm.item_count() or cm.findings:  # additive, only when there is content
        files[conn_format.FILE] = dump_json(conn_format.to_doc(cm))

    # coverage, readme, manifest
    files["coverage.json"] = dump_json(
        {
            "categories": {
                c: {"state": cov.state, "reason": cov.reason}
                for c, cov in m.coverage.categories.items()
            },
            "gaps": [asdict(g) for g in m.coverage.gaps],
            "warnings": [compact(asdict(w)) for w in m.warnings],
        }
    )
    files["README.md"] = render_readme(m.project.platform_id)
    files["manifest.json"] = dump_json(_manifest(m, info))

    counts = m.item_counts()
    n_xref = sum(1 for x in m.xrefs if not x.from_unit.startswith(HMI_UNIT_PREFIX))
    entries += [
        ("tags", f"Symbols (tags: {counts['symbols']})", "symbols.json", ""),
        ("io", "Inputs and outputs", "io.json", ""),
        ("hw", f"Hardware (modules: {len(hw.modules)})", "hardware.json", ""),
        ("xref", f"Cross-reference (entries: {n_xref})", "xref.json", ""),
        ("safety", f"Safety (units: {len(sf.units)})", "safety/safety.json", ""),
        (
            "hmi",
            f"HMI (screens: {len(hmi.screens)}, alarms: {len(hmi.alarms)})",
            "hmi/hmi.json",
            "",
        ),
        *screen_entries,
        *[("part", p.kind, f"parts/{p.kind}.json", "") for _, p in sorted(roots.items())],
        *([("lib", f"Library: {m.library.name}", "library.json", "")] if m.library else []),
        *(
            [("lib", f"Library links (entries: {len(m.library_links)})", "library_links.json", "")]
            if "library_links.json" in files
            else []
        ),
        ("struct", "Structure", "structure.json", ""),
        *(
            [
                (
                    "conn",
                    f"Connections (connections: {len(cm.connections)}, "
                    f"calls: {len(cm.uses)}, couplers: {len(cm.couplers)})",
                    conn_format.FILE,
                    "",
                )
            ]
            if conn_format.FILE in files
            else []
        ),
        *[
            ("platform", m.project.platform_id, p, "")
            for p in sorted(files)
            if p.startswith("platform/")
        ],
        ("cov", "Coverage", "coverage.json", ""),
        ("doc", "README", "README.md", "How to read this export"),
        ("meta", "Manifest", "manifest.json", ""),
    ]
    files |= _index(m, files, entries, group_threshold)
    if CONNECTIONS in m.coverage.categories:  # readable table after the file list
        files["index.md"] += "\n".join(conn_format.index_section(cm)) + "\n"
    return dict(sorted(files.items()))


def _manifest(m: ExportModel, info: ManifestInfo) -> dict[str, Any]:
    p = m.project
    extractor: dict[str, Any] = {
        "id": p.extractor_id,
        "version": p.extractor_version,
        "route": info.route,
        "worker": info.worker,
        "vendor_software": info.vendor_software,
    }
    if info.fallback_from:
        extractor["fallback_from"] = {"id": info.fallback_from[0], "reason": info.fallback_from[1]}
    up = p.upgrade
    upgrade: dict[str, Any] | None = None
    if up is not None:
        upgrade = {"from": up.from_version, "to": up.to_version, "tool": up.tool}
        if up.messages:
            upgrade["messages"] = list(up.messages)
    optional: dict[str, Any] = {}
    if p.kind != "project":
        optional["kind"] = p.kind
    if p.device is not None:
        optional["device"] = p.device
    if m.native_parts:
        optional["parts"] = [{"kind": "common", "path": "."}] + [
            {
                "kind": part.kind,
                "path": part.root,
                "files": len(part.files),
                "checksum": native_part_checksum(part.files),
            }
            for part in sorted(m.native_parts, key=lambda q: q.root)
        ]
    return optional | {
        "format_version": FORMAT_VERSION,
        "source": {"path": info.source_path, "kind": info.source_kind, "checksum": info.checksum},
        "platform": {"id": p.platform_id, "version": p.platform_version},
        "project": {
            "controller": p.controller,
            "line_or_machine": p.line_or_machine,
            "languages": list(p.languages),
        },
        "extractor": extractor,
        "upgrade": upgrade,
        "exported_at": info.exported_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts": {
            "units": len(m.units),
            "variables": len(m.variables),  # SD units count in "units" like every unit
            "xrefs": len(m.xrefs),
            "hardware_modules": len(m.hardware.modules),
            "hmi_screens": len(m.hmi.screens),
        },
        "coverage_summary": {
            c: m.coverage.categories[c].state
            for c in (*CATEGORIES, *OPTIONAL_CATEGORIES)
            if c in m.coverage.categories
        },
    }


# ------------------------------------------------------------------ atomic write (G2)
class OutputPathTooLong(OSError):
    """a file of the export would get a path over the Windows limit."""


WINDOWS_MAX_PATH = 259  # characters, without the terminating NUL


def path_limit() -> int | None:
    """The longest path this system can write, or None if there is no such limit."""
    if sys.platform != "win32":
        return None
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem"
        ) as key:
            if winreg.QueryValueEx(key, "LongPathsEnabled")[0] == 1:
                return None
    except OSError:
        pass
    return WINDOWS_MAX_PATH


def write_atomic(files: Mapping[str, str], out: Path, job: str | None = None) -> None:
    """Write into ``<out>.tmp-<job>``, validate, then swap it in for ``<out>``.

    If validation or any step fails, the previous export stays in place and
    :class:`~plcexport.format.validate.ExportInvalid` (or the OS error) is raised. A file path
    over the system's limit raises :class:`OutputPathTooLong` before anything is written.
    """
    from plcexport.format.validate import ExportInvalid, validate_export

    job = job or uuid.uuid4().hex[:8]
    tmp = out.with_name(f"{out.name}.tmp-{job}")
    old = out.with_name(f"{out.name}.old-{job}")
    limit = path_limit()
    if limit is not None and files:
        longest = max((str(tmp / rel) for rel in files), key=len)
        if len(longest) > limit:
            final = str(out / Path(longest).relative_to(tmp))
            raise OutputPathTooLong(
                f"output path too long: {len(longest)} characters ({final}); "
                f"the limit is {limit}, use a shorter --out folder"
            )
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        for rel, text in files.items():
            target = tmp / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(text.encode("utf-8"))
        violations = validate_export(tmp)
        if violations:
            raise ExportInvalid(violations)
        if out.exists():
            out.rename(old)
        try:
            tmp.rename(out)
        except OSError:
            if old.exists() and not out.exists():
                old.rename(out)
            raise
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(old, ignore_errors=True)
