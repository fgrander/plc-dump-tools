"""TIA libraries and library links (contracts/common-format-tia.md
§3-§4).

A global library dump becomes one ``ExportModel`` with ``project.kind="library"``: every type
with every version in ``library.json``, PLC type versions with content as units named
``<Type>@<version>``. A project's library goes into each PLC export (``kind="project"``,
metadata only: the linked units are the content). Link facts are copied as recorded; GUIDs go to
``platform/siemens-tia/library_ids.json`` for ``relink``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path, PureWindowsPath
from typing import Any, cast

import yaml

from plcexport.common import ExtractText, ExtractWarning, UnitKind
from plcexport.extractors.tia.simaticml import member_variables, parse_unit
from plcexport.format.canonical import file_names
from plcexport.model import (
    CATEGORIES,
    CategoryCoverage,
    Coverage,
    ExportModel,
    ExportProject,
    ExportUnit,
    Gap,
    LibraryLink,
    LibraryModel,
    LibraryType,
    MasterCopy,
    TypeVersion,
    Upgrade,
)

_SOURCE_SUFFIX = re.compile(r"(\.z?al\d\d)+$", re.IGNORECASE)
R_HMI_METADATA = "other:HMI type – metadata only"
R_PROJECT_LIBRARY = "other:project library – the linked units hold the content"
R_EXPORT_FAILED = "other:export failed"
HMI_KINDS = ("hmi_type", "faceplate")
SCOPES = {"FB": "fb_interface", "FC": "fc_interface", "DB": "db_member", "IDB": "db_member",
          "UDT": "udt_member"}  # fmt: skip


# ------------------------------------------------------------------ company libraries
@dataclass(frozen=True)
class CompanyLibrary:
    name: str
    path: str


def load_company_libraries(path: Path | None) -> list[CompanyLibrary]:
    """The YAML file of ``PLCEXPORT_TIA_LIBRARIES_FILE``: the libraries that count as company
    libraries, as ``company_libraries: [{name, path}]``."""
    if path is None or not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [
        CompanyLibrary(str(e["name"]), str(e["path"]))
        for e in data.get("company_libraries") or []
        if e.get("name") and e.get("path")
    ]


def _norm(path: str) -> str:
    return str(PureWindowsPath(path)).rstrip("\\").lower()


def company_status(
    name: str, source_path: str | None, company: list[CompanyLibrary]
) -> tuple[bool, str | None]:
    """(company, duplicate_of): a company library only at a configured path; a library
    of the same name elsewhere is a copy of it."""
    if source_path is not None:
        src = _norm(source_path)
        for c in company:
            # the configured path may name the library file or the folder that holds it
            if src in (_norm(c.path), str(PureWindowsPath(_norm(c.path)).parent)):
                return True, None
    same_name = next((c for c in company if c.name == name), None)
    return False, same_name.path if same_name else None


# ------------------------------------------------------------------ dump -> model parts
def _gap_reason(kind: str, content: Mapping[str, Any]) -> str | None:
    if content.get("part") != "none":
        return None
    error = str(content.get("error") or "")
    if kind in HMI_KINDS:
        return R_HMI_METADATA
    if error.startswith("project library"):
        return R_PROJECT_LIBRARY
    if "protect" in error.lower():
        return "protected"
    return R_EXPORT_FAILED


def original_name(name: str, source_file: str | None, upgrade: Mapping[str, Any] | None) -> str:
    """TIA names an upgraded library copy ``<name>_V<major>`` (found in the first sample batch:
    ``JAN0837_DP_library.al20`` became ``JAN0837_DP_library_V21``). The export keeps the
    library's own name, which is also what projects record as ``original_library``."""
    if not upgrade or not source_file:
        return name
    stem = _SOURCE_SUFFIX.sub("", str(source_file))
    suffix = f"_{upgrade.get('to')}"
    return stem if name == stem + suffix else name


def project_library_name(name: str, upgrade: Mapping[str, Any] | None) -> str:
    """The project library is named after its project, and TIA names an upgraded project copy
    ``<name>_V<major>``. The export keeps the project's own name: it is what the
    project's types record as ``original_library``, so ``relink`` can tell them as project-only
    (found when the fixtures were re-recorded: ``LLCCA_PID`` became ``LLCCA_PID_V21``)."""
    suffix = f"_{upgrade.get('to')}" if upgrade else ""
    return name[: -len(suffix)] if suffix and name.endswith(suffix) and name != suffix else name


def unit_name(type_name: str, version: str) -> str:
    return f"{type_name}@{version}"


def unique_versions(lib: Mapping[str, Any]) -> tuple[dict[str, Any], list[ExtractWarning]]:
    """TIA can hold two versions of one type with the same number (sample 156: two released
    ``0.0.3`` with different GUIDs, authors and dates). The oldest keeps the number, each other
    one becomes ``<number>~<first 8 of its GUID>``, so version strings stay unique per type
    and no version is dropped."""
    warnings: list[ExtractWarning] = []
    types = []
    for t in lib.get("types") or []:
        seen: set[str] = set()
        renamed: dict[int, str] = {}
        by_age = sorted(
            enumerate(t.get("versions") or []),
            key=lambda iv: (str(iv[1].get("date") or ""), str(iv[1].get("guid") or ""), iv[0]),
        )
        for i, v in by_age:
            number = str(v["version"])
            if number in seen:
                renamed[i] = f"{number}~{str(v.get('guid') or i).replace('-', '')[:8]}"
                where = f"{t.get('folder')}/{t['name']}" if t.get("folder") else str(t["name"])
                warnings.append(
                    ExtractWarning(
                        "library_version_duplicate",
                        f"{where}: second version {number}, exported as {renamed[i]}",
                    )
                )
            seen.add(renamed.get(i, number))
        if renamed:
            t = {
                **t,
                "versions": [
                    {**v, "version": renamed[i]} if i in renamed else v
                    for i, v in enumerate(t["versions"])
                ],
            }
        types.append(t)
    return {**lib, "types": types}, warnings


def library_model(
    lib: Mapping[str, Any], company: bool = False, duplicate_of: str | None = None
) -> LibraryModel:
    types = []
    for t in lib.get("types") or []:
        versions = []
        for v in t.get("versions") or []:
            content = v.get("content") or {}
            part = str(content.get("part") or "none")
            versions.append(
                TypeVersion(
                    version=str(v["version"]),
                    status=v["status"],
                    author=v.get("author"),
                    date=v.get("date"),
                    comment=dict(v.get("comment") or {}),
                    content_part=cast(Any, part),
                    content_path=None,  # set by to_library_model for exported content
                    gap_reason=_gap_reason(str(t["kind"]), content),
                )
            )
        types.append(
            LibraryType(str(t["name"]), str(t.get("folder") or ""), t["kind"], tuple(versions))
        )
    copies = tuple(
        MasterCopy(str(c["name"]), str(c.get("folder") or ""), tuple(c.get("objects") or []))
        for c in lib.get("master_copies") or []
    )
    return LibraryModel(
        name=str(lib["name"]),
        version=lib.get("version"),
        kind=lib["kind"],
        company=company and lib["kind"] == "global",
        duplicate_of=duplicate_of,
        types=tuple(types),
        master_copies=copies,
    ).sorted()


def links(device: Mapping[str, Any]) -> list[LibraryLink]:
    return [
        LibraryLink(
            object=str(k["object"]),
            object_kind=k["object_kind"],
            type_name=str(k["type_name"]),
            type_folder=str(k.get("type_folder") or ""),
            version=str(k["version"]),
            status=k["status"],
            original_library=k.get("original_library"),
        )
        for k in device.get("library_links") or []
    ]


def library_ids(
    lib: Mapping[str, Any] | None, link_rows: Iterable[Mapping[str, Any]] = ()
) -> dict[str, Any]:
    """Type GUIDs for ``relink`` : by ``<folder>/<type>``, and per linked object."""
    types: dict[str, str] = {}
    versions: dict[str, str] = {}
    for t in (lib or {}).get("types") or []:
        key = f"{t.get('folder')}/{t['name']}" if t.get("folder") else str(t["name"])
        if t.get("guid"):
            types[key] = str(t["guid"])
        for v in t.get("versions") or []:
            if v.get("guid"):
                versions[f"{key}@{v['version']}"] = str(v["guid"])
    out: dict[str, Any] = {"types": types, "type_versions": versions}
    linked = {str(k["object"]): str(k["type_guid"]) for k in link_rows if k.get("type_guid")}
    if linked:
        out["links"] = linked
    return out


# ------------------------------------------------------------------ library export
def _coverage(m: ExportModel, gaps: list[Gap]) -> Coverage:
    counts = m.item_counts()
    cats: dict[str, CategoryCoverage] = {
        c: CategoryCoverage("delivered") if counts[c] else CategoryCoverage(
            "unavailable", "not_in_project")
        for c in CATEGORIES
    }  # fmt: skip
    if any(g.category == "program_units" and g.reason == R_EXPORT_FAILED for g in gaps):
        cats["program_units"] = CategoryCoverage("partial", R_EXPORT_FAILED)
    return Coverage(categories=cats, gaps=tuple(gaps))


def to_library_model(
    dump: Mapping[str, Any],
    dump_dir: Path,
    extractor_id: str,
    extractor_version: str,
    vendor_software: str | None,
    source_path: str | None = None,
    company: list[CompanyLibrary] | None = None,
) -> ExportModel:
    lib = dict(dump["library"])
    tia = dump.get("tia") or {}
    up = tia.get("upgrade")
    lib["name"] = original_name(str(lib["name"]), (dump.get("source") or {}).get("file"), up)
    is_company, duplicate_of = company_status(str(lib["name"]), source_path, company or [])
    m = ExportModel(
        project=ExportProject(
            platform_id="siemens-tia",
            platform_version=tia.get("version"),
            controller=None,
            line_or_machine=str(lib["name"]),
            extractor_id=extractor_id,
            extractor_version=extractor_version,
            upgrade=Upgrade(str(up["from"]), str(up["to"]),
                            vendor_software or f"TIA Portal {up['to']}",
                            tuple(str(x) for x in up.get("messages") or []))
            if up else None,
            kind="library",
        )
    )  # fmt: skip
    lib, duplicates = unique_versions(lib)
    m.warnings += duplicates
    model = library_model(lib, is_company, duplicate_of)
    gaps: list[Gap] = []
    paths: dict[tuple[str, str, str], str] = {}  # (folder, type, version) -> unit name
    for t in lib.get("types") or []:
        for v in t.get("versions") or []:
            content = v.get("content") or {}
            name = unit_name(str(t["name"]), str(v["version"]))
            reason = _gap_reason(str(t["kind"]), content)
            if content.get("part") == "common" and content.get("path"):
                parsed = parse_unit((dump_dir / str(content["path"])).read_bytes())
                kind = cast(UnitKind, parsed.kind if parsed.kind in SCOPES or parsed.kind
                            in ("OB",) else "OTHER")  # fmt: skip
                scope = SCOPES.get(kind)
                m.units.append(
                    ExportUnit(
                        name=name,
                        kind=kind,
                        language=None if kind in ("DB", "IDB", "UDT") else parsed.language,
                        files=(),
                        parse_quality="partial" if parsed.partial else "full",
                        number=parsed.number,
                        attributes={"library_type": str(t["name"]), "version": str(v["version"]),
                                    **parsed.attributes},
                        folder=str(t.get("folder") or "") or None,
                        path_prefix=f'"{name}"' if scope else None,
                        variable_scope=cast(Any, scope),
                    )
                )  # fmt: skip
                m.unit_bodies[name] = parsed.body
                for lang, text in sorted(parsed.title.items()):
                    m.texts.append(ExtractText(name, "title", lang, text))
                if scope:
                    m.variables += member_variables(name, cast(Any, scope), f'"{name}"',
                                                    parsed.members)  # fmt: skip
                paths[(str(t.get("folder") or ""), str(t["name"]), str(v["version"]))] = name
            elif reason is not None and reason != R_HMI_METADATA:
                gaps.append(Gap("program_units", name, reason))
    # content paths: the rendered unit file of each exported version
    by_dir: dict[str, list[ExportUnit]] = {}
    for u in m.units:
        by_dir.setdefault("datatypes" if u.kind == "UDT" else f"units/{u.kind}", []).append(u)
    unit_path = {
        name: f"{d}/{stem}.md"  # the first file; a split unit continues in .part-N files
        for d, us in by_dir.items()
        for name, stem in file_names(u.name for u in us).items()
    }
    m.library = replace(
        model,
        types=tuple(
            replace(
                t,
                versions=tuple(
                    replace(
                        v,
                        content_path=unit_path.get(paths.get((t.folder, t.name, v.version), "")),
                    )
                    for v in t.versions
                ),
            )
            for t in model.types
        ),
    )
    m.platform_files["library_ids.json"] = library_ids(lib)
    m.platform = {"tia_version": tia.get("version"),
                  "saved_version": (dump.get("source") or {}).get("saved_version"),
                  "tiadump": (dump.get("tool") or {}).get("version")}  # fmt: skip
    if duplicate_of:
        m.warnings.append(
            ExtractWarning(
                "library_copy",
                f"library {lib['name']} is not at its company location; copy of {duplicate_of}",
            )
        )
    _check_counts(m, dump, lib)
    m.coverage = _coverage(m, gaps)
    if any(w.code == "completeness_mismatch" for w in m.warnings):
        cats = dict(m.coverage.categories)
        cats["program_units"] = CategoryCoverage("partial", "other:completeness mismatch")
        m.coverage = Coverage(cats, m.coverage.gaps)
    for e in dump.get("errors") or []:
        m.warnings.append(
            ExtractWarning(f"tiadump_{e.get('kind')}", f"{e['where']}: {e['message']}")
        )
    return m.sorted()


def _check_counts(m: ExportModel, dump: Mapping[str, Any], lib: Mapping[str, Any]) -> None:
    want = (dump.get("counts") or {}).get("_library") or {}
    got = {
        "types": len(lib.get("types") or []),
        "type_versions": sum(len(t.get("versions") or []) for t in lib.get("types") or []),
        "master_copies": len(lib.get("master_copies") or []),
    }
    for key, n in got.items():
        if key in want and int(want[key]) != n:
            m.warnings.append(
                ExtractWarning(
                    "completeness_mismatch",
                    f"library {key}: {n} dumped, tiadump counted {want[key]}",
                )
            )
