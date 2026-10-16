"""Common format v1 files -> ``ExportModel``.

Used by 002's ``common-export`` profile and by tests. Works on ``{relative path: text}`` so it can
read from a folder or from a pinned git revision alike. Split units (``.part-<n>.md``) are joined.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml

from plcexport.common import ExtractText, ExtractWarning
from plcexport.format import connections as conn_format
from plcexport.format.canonical import split_front_matter
from plcexport.format.validate import is_unit_file
from plcexport.model import (
    BodyNetwork,
    CategoryCoverage,
    Coverage,
    ExportModel,
    ExportProject,
    ExportUnit,
    ExportVariable,
    ExportXref,
    Gap,
    HardwareModel,
    HmiAlarm,
    HmiDevice,
    HmiModel,
    HmiObject,
    HmiRecipe,
    HmiScreen,
    HmiTag,
    HwChannel,
    HwController,
    HwModule,
    HwNetwork,
    HwRack,
    LibraryLink,
    LibraryModel,
    LibraryType,
    MasterCopy,
    NativePart,
    SafetyModel,
    SafetyParameter,
    SafetySignature,
    StructDevice,
    StructFolder,
    StructTask,
    StructureModel,
    TypeVersion,
    UnitBody,
    Upgrade,
)


@dataclass
class ReadExport:
    model: ExportModel
    manifest: dict[str, Any]
    unit_files: dict[str, tuple[str, ...]] = field(default_factory=dict)  # unit -> its files
    network_file: dict[str, dict[int, str]] = field(default_factory=dict)  # unit -> no -> file
    network_spans: dict[str, dict[int, tuple[int, int]]] = field(default_factory=dict)


def _json(files: Mapping[str, str], rel: str, default: Any) -> Any:
    return json.loads(files[rel]) if rel in files else default


def _code(lines: list[str], start: int, end: int) -> str:
    """Code between the first fence after ``start`` and the closing fence at ``end``."""
    block = lines[start - 1 : end]
    opening = next((i for i, line in enumerate(block) if line.startswith("```")), None)
    if opening is None:
        return ""
    return "\n".join(block[opening + 1 : -1])


def _source_code(body: str) -> str | None:
    lines = body.split("\n")
    if "## Source" not in lines:
        return None
    i = lines.index("## Source")
    opening = next(j for j in range(i, len(lines)) if lines[j].startswith("```"))
    closing = next(j for j in range(opening + 1, len(lines)) if lines[j] == "```")
    return "\n".join(lines[opening + 1 : closing])


def _members(
    unit: str,
    scope: Any,
    prefix: str | None,
    parent: str | None,
    members: list[dict[str, Any]],
) -> list[ExportVariable]:
    out: list[ExportVariable] = []
    for index, m in enumerate(members):
        base = parent if parent is not None else prefix
        path = m.get("path") or (f"{base}.{m['name']}" if base is not None else str(m["name"]))
        out.append(
            ExportVariable(
                declared_in=unit,
                scope=scope,
                symbolic_path=path,
                data_type=str(m["type"]),
                section=m.get("section"),
                io_direction=m.get("io_direction"),
                parent_path=parent,
                array_dims=m.get("dims"),
                address=m.get("address"),
                offset=m.get("offset"),
                # the order of the file, so that a model read back is written the same way
                position=None if m.get("offset") is not None else index,
                start_value=m.get("start"),
                retain=m.get("retain"),
                ext_accessible=m.get("accessible"),
                ext_visible=m.get("visible"),
                ext_writable=m.get("writable"),
                comments=dict(m.get("comment") or {}),
                safety=bool(m.get("safety", False)),
            )
        )
        out += _members(unit, scope, prefix, path, m.get("members") or [])
    return out


def read_files(files: Mapping[str, str]) -> ReadExport:
    manifest = _json(files, "manifest.json", {})
    mp = manifest.get("project") or {}
    up = manifest.get("upgrade")
    project = ExportProject(
        platform_id=(manifest.get("platform") or {}).get("id", ""),
        platform_version=(manifest.get("platform") or {}).get("version"),
        controller=mp.get("controller"),
        line_or_machine=mp.get("line_or_machine"),
        extractor_id=(manifest.get("extractor") or {}).get("id", ""),
        extractor_version=(manifest.get("extractor") or {}).get("version", ""),
        languages=tuple(mp.get("languages") or ()),
        upgrade=Upgrade(up["from"], up["to"], up["tool"], tuple(up.get("messages") or ()))
        if up
        else None,
        kind=manifest.get("kind", "project"),
        device=manifest.get("device"),
    )
    result = ReadExport(model=ExportModel(project=project), manifest=manifest)
    m = result.model

    # ---- units (parts joined in part order)
    parts: dict[tuple[str, str], list[tuple[int, str, dict[str, Any], str]]] = {}
    for rel in sorted(r for r in files if is_unit_file(r)):
        try:
            fm, body = split_front_matter(files[rel])
            if "name" not in fm or "kind" not in fm:
                raise ValueError("front matter without name or kind")
        except (ValueError, yaml.YAMLError) as exc:
            # tolerate a damaged unit file: keep the unit by its path, without content
            stem = rel.rsplit("/", 1)[1].removesuffix(".md").split(".part-")[0]
            kind = "UDT" if rel.startswith("datatypes/") else rel.split("/")[1]
            fm = {"name": stem, "kind": kind, "parse_quality": "names_only"}
            body = ""
            m.warnings.append(ExtractWarning("parse_error", f"{rel}: {exc}", stem))
        n = int(str(fm.get("part") or "1/1").split("/")[0])
        parts.setdefault((str(fm["kind"]), str(fm["name"])), []).append((n, rel, fm, body))
    for (_, name), plist in sorted(parts.items()):
        plist.sort()
        _, _, fm, first_body = plist[0]
        result.unit_files[name] = tuple(p[1] for p in plist)
        scope = fm.get("variable_scope")
        m.units.append(
            ExportUnit(
                name=name,
                kind=fm["kind"],
                language=fm.get("original_language"),
                files=result.unit_files[name],
                parse_quality=fm.get("parse_quality", "full"),
                number=fm.get("number"),
                instance_of=fm.get("instance_of"),
                protected=bool(fm.get("protected", False)),
                attributes=dict(fm.get("attributes") or {}),
                safety=bool(fm.get("safety", False)),
                folder=fm.get("folder"),
                path_prefix=fm.get("path_prefix"),
                variable_scope=scope,
            )
        )
        for kind in ("title", "comment"):
            for lang, t in sorted((fm.get(kind) or {}).items()):
                m.texts.append(ExtractText(name, cast(Any, kind), lang, t))
        for e in fm.get("element_texts") or []:
            m.texts.append(
                ExtractText(
                    name, e["kind"], e["lang"], e["text"], e["network_no"] or None, e["element_ref"]
                )
            )
        m.variables += _members(name, scope, fm.get("path_prefix"), None, fm.get("interface") or [])
        networks: list[BodyNetwork] = []
        for _, rel, pfm, _ in plist:
            lines = files[rel].split("\n")
            for nw in pfm.get("networks") or []:
                no, start, end = nw["no"], nw["line_start"], nw["line_end"]
                result.network_file.setdefault(name, {})[no] = rel
                result.network_spans.setdefault(name, {})[no] = (start, end)
                networks.append(
                    BodyNetwork(
                        no,
                        _code(lines, start, end),
                        dict(nw.get("title") or {}),
                        dict(nw.get("comment") or {}),
                    )
                )
        code = _source_code(first_body) if not networks else None
        if networks or code is not None:
            m.unit_bodies[name] = UnitBody(fm.get("language", "none"), tuple(networks), code)

    # ---- tables
    for r in _json(files, "symbols.json", []):
        m.variables.append(
            ExportVariable(
                declared_in=r["table"],
                scope=r["scope"],
                symbolic_path=r["symbol"],
                data_type=r["data_type"],
                io_direction=r.get("io_direction"),
                parent_path=r.get("parent"),
                array_dims=r.get("dims"),
                address=r.get("address"),
                start_value=r.get("initial"),
                retain=r.get("retain"),
                ext_accessible=r.get("accessible"),
                ext_visible=r.get("visible"),
                ext_writable=r.get("writable"),
                comments=dict(r.get("comment") or {}),
                safety=bool(r.get("safety", False)),
            )
        )
    for x in _json(files, "xref.json", []):
        m.xrefs.append(
            ExportXref(
                from_unit=x["from_unit"],
                target_kind=x["target_kind"],
                target_text=x["target"],
                access=x["access"],
                network_no=x.get("network_no"),
                line=x.get("line"),
                via_param=x.get("via_param"),
                channel_ref=x.get("channel_ref"),
                hmi_ref=x.get("hmi_ref"),
            )
        )
    hw = _json(files, "hardware.json", {})
    m.hardware = HardwareModel(
        controllers=tuple(
            HwController(c["ref"], c["name"], c.get("type"), c.get("order_no"), c.get("firmware"))
            for c in hw.get("controllers", [])
        ),
        racks=tuple(HwRack(r["ref"], r["name"]) for r in hw.get("racks", [])),
        modules=tuple(
            HwModule(
                x["ref"],
                x["type"],
                x.get("rack"),
                x.get("slot"),
                x.get("order_no"),
                x.get("firmware"),
                tuple(x.get("address_ranges") or ()),
            )
            for x in hw.get("modules", [])
        ),
        channels=tuple(
            HwChannel(c["ref"], c["module_ref"], c["address"], c.get("symbol"))
            for c in hw.get("channels", [])
        ),
        networks=tuple(
            HwNetwork(
                n["ref"], n["interface"], n.get("address"), n.get("device_name"), n.get("subnet")
            )
            for n in hw.get("networks", [])
        ),
    )
    sf = _json(files, "safety/safety.json", {})
    m.safety = SafetyModel(
        units=tuple(sf.get("units", [])),
        tags=tuple(sf.get("tags", [])),
        parameters=tuple(
            SafetyParameter(p["scope"], p["name"], p["value"]) for p in sf.get("parameters", [])
        ),
        signatures=tuple(
            SafetySignature(s["scope"], s["value"], s["kind"]) for s in sf.get("signatures", [])
        ),
    )
    hmi = _json(files, "hmi/hmi.json", {})
    screens = []
    for rel in sorted(r for r in files if r.startswith("hmi/screens/") and r.endswith(".md")):
        fm, _ = split_front_matter(files[rel])
        screens.append(
            HmiScreen(
                fm["name"],
                fm["device"],
                tuple(
                    HmiObject(o["name"], o["type"], tuple(o.get("tag_bindings") or ()))
                    for o in fm.get("objects") or []
                ),
                dict(fm.get("texts") or {}),
            )
        )
    m.hmi = HmiModel(
        devices=tuple(HmiDevice(d["name"], d.get("type")) for d in hmi.get("devices", [])),
        screens=tuple(screens),
        alarms=tuple(
            HmiAlarm(a["id"], a.get("class"), dict(a.get("text") or {}), a.get("trigger_tag"))
            for a in hmi.get("alarms", [])
        ),
        hmi_tags=tuple(
            HmiTag(t["name"], t["device"], t.get("plc_tag")) for t in hmi.get("hmi_tags", [])
        ),
        recipes=tuple(
            HmiRecipe(r["name"], r["device"], tuple(r.get("elements") or ()))
            for r in hmi.get("recipes", [])
        ),
    )
    st = _json(files, "structure.json", {})
    m.structure = StructureModel(
        devices=tuple(StructDevice(d["name"], d.get("type")) for d in st.get("devices", [])),
        tasks=tuple(
            StructTask(t["name"], t["kind"], t.get("interval"), tuple(t.get("units", [])))
            for t in st.get("tasks", [])
        ),
        folders=tuple(
            StructFolder(f["path"], tuple(f.get("units", []))) for f in st.get("folders", [])
        ),
    )
    cov = _json(files, "coverage.json", {})
    m.coverage = Coverage(
        categories={
            c: CategoryCoverage(v["state"], v.get("reason"))
            for c, v in (cov.get("categories") or {}).items()
        },
        gaps=tuple(Gap(g["category"], g["item"], g["reason"]) for g in cov.get("gaps", [])),
    )
    m.warnings += [
        ExtractWarning(w["code"], w["message"], w.get("unit")) for w in cov.get("warnings", [])
    ]
    m.connections = conn_format.from_doc(_json(files, conn_format.FILE, None))
    platform_files = [r for r in files if r.startswith("platform/") and r.endswith(".json")]
    for rel in sorted(platform_files):
        if rel.rsplit("/", 1)[-1] == "platform.json":
            m.platform.update(json.loads(files[rel]))
        else:
            m.platform_files[rel.rsplit("/", 1)[-1]] = json.loads(files[rel])
    _read_parts(files, manifest, m)
    _read_library(files, m)
    return result


def _read_parts(files: Mapping[str, str], manifest: Mapping[str, Any], m: ExportModel) -> None:
    """native parts and the units whose content they hold."""
    for p in manifest.get("parts") or []:
        if p.get("kind") == "common":
            continue
        root, kind = str(p["path"]), str(p["kind"])
        prefix = root + "/"
        m.native_parts.append(
            NativePart(
                kind,
                root,
                {
                    r[len(prefix) :]: files[r].encode("utf-8")
                    for r in sorted(files)
                    if r.startswith(prefix)
                },
            )
        )
        for row in _json(files, f"parts/{kind}.json", []):
            m.units.append(
                ExportUnit(
                    row["name"],
                    row["kind"],
                    row.get("language", ""),
                    tuple(row["files"]),
                    number=row.get("number"),
                    instance_of=row.get("instance_of"),
                    protected=bool(row.get("protected", False)),
                    attributes=dict(row.get("attributes") or {}),
                    safety=bool(row.get("safety", False)),
                    folder=row.get("folder"),
                )
            )


def _read_library(files: Mapping[str, str], m: ExportModel) -> None:
    lib = _json(files, "library.json", None)
    if lib is not None:
        m.library = LibraryModel(
            name=lib["name"],
            version=lib.get("version"),
            kind=lib["kind"],
            company=bool(lib.get("company", False)),
            duplicate_of=lib.get("duplicate_of"),
            types=tuple(
                LibraryType(
                    t["name"],
                    t["folder"],
                    t["kind"],
                    tuple(
                        TypeVersion(
                            v["version"],
                            v["status"],
                            v.get("author"),
                            v.get("date"),
                            dict(v.get("comment") or {}),
                            v.get("content_part", "none"),
                            v.get("content_path"),
                            v.get("gap_reason"),
                        )
                        for v in t.get("versions", [])
                    ),
                )
                for t in lib.get("types", [])
            ),
            master_copies=tuple(
                MasterCopy(
                    c["name"], c["folder"], tuple(c.get("objects") or ()), c.get("content_path")
                )
                for c in lib.get("master_copies", [])
            ),
        )
    links = _json(files, "library_links.json", {}) or {}
    m.library_links = [
        LibraryLink(
            k["object"],
            k["object_kind"],
            k["type_name"],
            k["type_folder"],
            k["version"],
            k["status"],
            k.get("original_library"),
        )
        for k in links.get("links", [])
    ]


def read_export(export_dir: Path) -> ReadExport:
    files = {
        p.relative_to(export_dir).as_posix(): p.read_text(encoding="utf-8")
        for p in sorted(export_dir.rglob("*"))
        if p.is_file()
    }
    return read_files(files)
