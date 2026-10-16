"""library dumps, project libraries and link facts -> export models.

The library metadata here is synthetic (no recorded library dump exists yet); the content
of a type version is a real TIA V21 SimaticML export from the tank sample."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from plcexport.extractors.tia.library import (
    R_HMI_METADATA,
    R_PROJECT_LIBRARY,
    CompanyLibrary,
    company_status,
    library_ids,
    library_model,
    load_company_libraries,
    project_library_name,
    to_library_model,
)
from plcexport.extractors.tia.mapping import MappingOptions, to_bundle
from plcexport.format.validate import validate_files
from plcexport.format.writer import ManifestInfo, render
from plcexport.model import validate_library
from tests.conftest import FIXTURES

INFO = ManifestInfo(
    source_path="Bibliotheken/ACME_Standard.zal21",
    checksum="sha256:" + "0" * 64,
    exported_at=datetime(2026, 10, 10, tzinfo=UTC),
)
SCL = FIXTURES / "tiadump" / "simaticml_tank" / "LSim_PT1.xml"
GUID = "0f8fad5b-d9cb-469f-a165-70867728950e"
NO_CONTENT = "project library: the linked units hold the content"  # tiadump's text


def _version(v: str, status: str = "released", part: str = "common", **kw: Any) -> dict[str, Any]:
    path = f"library/simaticml/LSim_PT1/{v}.xml" if part == "common" else None
    return {
        "version": v, "status": status, "author": "Author A", "date": "2025-03-14",
        "comment": {"en-US": f"version {v}"}, "guid": f"g-{v}",
        "content": {"part": part, "path": path, "error": kw.get("error")},
    }  # fmt: skip


def _library_dump(tmp_path: Path) -> dict[str, Any]:
    for v in ("1.0.0", "1.2.0", "1.10.0", "1.11.0"):
        target = tmp_path / "library" / "simaticml" / "LSim_PT1" / f"{v}.xml"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(SCL, target)
    return {
        "dump_version": 1,
        "tool": {"name": "tiadump", "version": "1.0.0"},
        "source": {"file": "ACME_Standard.zal21", "kind": "library", "saved_version": "V21"},
        "tia": {"version": "V21", "upgrade": None},
        "languages": {"project": []},
        "multiuser": {"kind": "none"},
        "missing_packages": [],
        "counts": {"_library": {"types": 3, "type_versions": 6, "master_copies": 1}},
        "cleanup": {"outside_work": []},
        "compiled_units": [],
        "devices": [],
        "hardware": {"devices": [], "subnets": []},
        "project_library": None,
        "library": {
            "name": "ACME_Standard",
            "version": "3.2",
            "kind": "global",
            "types": [
                {"name": "LSim_PT1", "folder": "Simulation", "kind": "plc_block", "guid": GUID,
                 "versions": [_version("1.10.0"), _version("1.0.0"), _version("1.2.0"),
                              _version("1.11.0", "in_work")]},
                {"name": "Valve_Face", "folder": "HMI", "kind": "faceplate", "guid": "f-1",
                 "versions": [_version("2.0.0", part="none", error="HMI type: metadata only")]},
                {"name": "Secret", "folder": "", "kind": "plc_block", "guid": "s-1",
                 "versions": [_version("1.0.0", part="none",
                                       error="The block is know-how protected")]},
            ],
            "master_copies": [
                {"name": "Station template", "folder": "Templates",
                 "objects": ["PLC_1 (Device)"], "path": None},
            ],
        },
        "errors": [],
    }  # fmt: skip


def test_library_export_has_every_version_in_numeric_order(tmp_path: Path) -> None:
    m = to_library_model(_library_dump(tmp_path), tmp_path, "tia", "1.0.0", "TIA Portal V21")
    assert m.project.kind == "library" and m.library is not None
    validate_library(m.library)
    lsim = next(t for t in m.library.types if t.name == "LSim_PT1")
    assert [v.version for v in lsim.versions] == ["1.0.0", "1.2.0", "1.10.0", "1.11.0"]
    v110 = lsim.versions[2]
    assert (v110.status, v110.author, v110.date, v110.comment) == (
        "released", "Author A", "2025-03-14", {"en-US": "version 1.10.0"},
    )  # fmt: skip
    assert v110.content_part == "common"
    assert v110.content_path == "units/FB/LSim_PT1@1.10.0.md"
    assert lsim.versions[3].status == "in_work" and lsim.versions[3].content_part == "common"


def test_type_versions_become_units_with_their_body(tmp_path: Path) -> None:
    m = to_library_model(_library_dump(tmp_path), tmp_path, "tia", "1.0.0", None)
    names = sorted(u.name for u in m.units)
    assert names == ["LSim_PT1@1.0.0", "LSim_PT1@1.10.0", "LSim_PT1@1.11.0", "LSim_PT1@1.2.0"]
    assert m.unit_bodies["LSim_PT1@1.2.0"].language == "scl"
    unit = next(u for u in m.units if u.name == "LSim_PT1@1.2.0")
    assert unit.attributes["library_type"] == "LSim_PT1" and unit.folder == "Simulation"


def test_faceplates_metadata_only_and_protected_versions_are_gaps(tmp_path: Path) -> None:
    m = to_library_model(_library_dump(tmp_path), tmp_path, "tia", "1.0.0", None)
    assert m.library is not None
    face = next(t for t in m.library.types if t.name == "Valve_Face")
    assert face.kind == "faceplate" and face.versions[0].gap_reason == R_HMI_METADATA
    assert {g.item: g.reason for g in m.coverage.gaps} == {"Secret@1.0.0": "protected"}
    assert m.library.master_copies[0].objects == ("PLC_1 (Device)",)
    assert m.coverage.categories["hmi"].state == "delivered"  # the faceplate version
    assert m.coverage.categories["structure"].state == "delivered"  # folders, master copy


def test_library_export_renders_and_validates(tmp_path: Path) -> None:
    m = to_library_model(_library_dump(tmp_path), tmp_path, "tia", "1.0.0", None)
    files = render(m, INFO)
    assert validate_files({k: v.encode() for k, v in files.items()}) == []
    manifest = json.loads(files["manifest.json"])
    assert manifest["kind"] == "library"
    lib = json.loads(files["library.json"])
    assert lib["name"] == "ACME_Standard" and lib["version"] == "3.2"
    path = lib["types"][0]["versions"][0]["content_path"]
    assert path is None or path in files
    content_paths = [v["content_path"] for t in lib["types"] for v in t["versions"]]
    assert all(p in files for p in content_paths if p)
    ids = json.loads(files["platform/siemens-tia/library_ids.json"])
    assert ids["types"]["Simulation/LSim_PT1"] == GUID


def test_completeness_mismatch_on_library_counts(tmp_path: Path) -> None:
    dump = _library_dump(tmp_path)
    dump["counts"]["_library"]["type_versions"] = 9
    m = to_library_model(dump, tmp_path, "tia", "1.0.0", None)
    assert any(w.code == "completeness_mismatch" for w in m.warnings)
    assert m.coverage.categories["program_units"].reason == "other:completeness mismatch"


# ------------------------------------------------------------------ company libraries
COMPANY = [CompanyLibrary("ACME_Standard", r"\\fileserver\libs\ACME_Standard\ACME_Standard.al21")]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (r"\\fileserver\libs\ACME_Standard\ACME_Standard.al21", (True, None)),
        (r"\\FILESERVER\libs\ACME_Standard", (True, None)),  # the folder of the library
        (r"D:\copies\ACME_Standard", (False, COMPANY[0].path)),  # same name elsewhere
        (None, (False, COMPANY[0].path)),
    ],
)
def test_company_status_by_location(source: str | None, expected: tuple[bool, str | None]) -> None:
    assert company_status("ACME_Standard", source, COMPANY) == expected


def test_other_libraries_are_not_company() -> None:
    assert company_status("Other", r"\\fileserver\libs\Other", COMPANY) == (False, None)


def test_company_flag_reaches_the_model(tmp_path: Path) -> None:
    m = to_library_model(
        _library_dump(tmp_path), tmp_path, "tia", "1.0.0", None,
        r"\\fileserver\libs\ACME_Standard\ACME_Standard.al21", COMPANY,
    )  # fmt: skip
    assert m.library is not None and m.library.company and m.library.duplicate_of is None
    copy = to_library_model(
        _library_dump(tmp_path), tmp_path, "tia", "1.0.0", None, r"D:\copy", COMPANY
    )
    assert copy.library is not None and copy.library.duplicate_of == COMPANY[0].path
    assert any(w.code == "library_copy" for w in copy.warnings)


def test_company_libraries_file(tmp_path: Path) -> None:
    f = tmp_path / "tia-libraries.yaml"
    f.write_text(
        "company_libraries:\n  - name: ACME\n    path: '\\\\srv\\ACME.al21'\n",
        encoding="utf-8",
    )
    assert load_company_libraries(f) == [CompanyLibrary("ACME", r"\\srv\ACME.al21")]
    assert load_company_libraries(tmp_path / "missing.yaml") == []


# ------------------------------------------------------------------ projects
def test_project_library_and_links_in_plc_exports() -> None:
    d = FIXTURES / "tiadump" / "tank_v19"
    dump = json.loads((d / "dump.json").read_text(encoding="utf-8"))
    dump["project_library"] = {
        "name": "tia-tank-application", "version": None, "kind": "project",
        "types": [{"name": "LGF_DTLToString_ISO", "folder": "LGF/06 Converter operations",
                   "kind": "plc_block", "guid": GUID,
                   "versions": [_version("3.0.1", part="none", error=NO_CONTENT)]}],
        "master_copies": [],
    }  # fmt: skip
    plc = next(x for x in dump["devices"] if x["kind"] == "plc")
    plc["library_links"] = [
        {"object": "LGF_DTLToString_ISO", "object_kind": "unit", "type_name": "LGF_DTLToString_ISO",
         "type_folder": "LGF/06 Converter operations", "version": "3.0.1", "status": "released",
         "original_library": "LGF", "type_guid": GUID},
    ]  # fmt: skip
    (m,) = to_bundle(dump, d, MappingOptions("tia", "1.0.0")).models
    assert m.library is not None and m.library.kind == "project"
    assert m.library.types[0].versions[0].gap_reason == R_PROJECT_LIBRARY
    (link,) = m.library_links
    assert (link.object, link.version, link.original_library) == (
        "LGF_DTLToString_ISO",
        "3.0.1",
        "LGF",
    )
    assert m.platform_files["library_ids.json"]["links"] == {"LGF_DTLToString_ISO": GUID}
    files = render(m, INFO)
    links = json.loads(files["library_links.json"])
    assert links["links"][0]["comparison"] == "not_compared"
    assert validate_files({k: v.encode() for k, v in files.items()}) == []


def test_library_ids_by_type_and_version(tmp_path: Path) -> None:
    lib = _library_dump(tmp_path)["library"]
    ids = library_ids(lib, [{"object": "FB_X", "type_guid": "abc"}])
    assert ids["types"]["Simulation/LSim_PT1"] == GUID and ids["types"]["Secret"] == "s-1"
    assert ids["type_versions"]["Simulation/LSim_PT1@1.2.0"] == "g-1.2.0"
    assert ids["links"] == {"FB_X": "abc"}


def test_library_model_sorts_and_keeps_company_only_for_global(tmp_path: Path) -> None:
    lib = _library_dump(tmp_path)["library"]
    m = library_model({**lib, "kind": "project"}, company=True)
    assert not m.company
    assert [t.name for t in m.types] == ["Secret", "Valve_Face", "LSim_PT1"]  # by folder, name


def test_two_versions_with_the_same_number_are_both_kept() -> None:
    # sample 156: two released 0.0.3 of one type, with different GUIDs, authors and dates
    d = FIXTURES / "tiadump" / "tank_v19"
    dump = json.loads((d / "dump.json").read_text(encoding="utf-8"))
    newer = {**_version("0.0.3", part="none", error=NO_CONTENT), "date": "2022-01-17",
             "guid": "3e8705a9-18f2-422d-9682-218b8bee57db"}  # fmt: skip
    older = {**_version("0.0.3", part="none", error=NO_CONTENT), "date": "2021-08-19",
             "guid": "7bfaf24d-ab80-41d0-b90a-c32f80bbc0dc"}  # fmt: skip
    dump["project_library"] = {
        "name": "TestProject1", "version": None, "kind": "project",
        "types": [{"name": "ErrTyp", "folder": "Common", "kind": "plc_type", "guid": GUID,
                   "versions": [newer, older]}],
        "master_copies": [],
    }  # fmt: skip
    (m,) = to_bundle(dump, d, MappingOptions("tia", "1.0.0")).models
    assert m.library is not None
    validate_library(m.library)
    assert [v.version for v in m.library.types[0].versions] == ["0.0.3", "0.0.3~3e8705a9"]
    assert [v.date for v in m.library.types[0].versions] == ["2021-08-19", "2022-01-17"]
    assert m.platform_files["library_ids.json"]["type_versions"] == {
        "Common/ErrTyp@0.0.3": older["guid"],
        "Common/ErrTyp@0.0.3~3e8705a9": newer["guid"],
    }
    (w,) = [w for w in m.warnings if w.code == "library_version_duplicate"]
    assert "Common/ErrTyp" in w.message and "0.0.3~3e8705a9" in w.message
    files = render(m, INFO)
    assert validate_files({k: v.encode() for k, v in files.items()}) == []


def test_project_library_of_an_upgraded_project_keeps_the_project_name() -> None:
    up = {"from": "V19", "to": "V21", "messages": []}
    assert project_library_name("LLCCA_PID_V21", up) == "LLCCA_PID"
    assert project_library_name("Line3_V21_V21", up) == "Line3_V21"  # only TIA's own suffix
    assert project_library_name("LLCCA_PID_V21", None) == "LLCCA_PID_V21"  # not upgraded
    assert project_library_name("_V21", up) == "_V21"
    # the recorded V19 project: its own types name "LLCCA_PID" as their original library
    d = FIXTURES / "tiadump" / "pid_v19"
    dump = json.loads((d / "dump.json").read_text(encoding="utf-8"))
    assert dump["project_library"]["name"] == "LLCCA_PID_V21"
    (m,) = to_bundle(dump, d, MappingOptions("tia", "1.0.0")).models
    assert m.library is not None and m.library.name == "LLCCA_PID"
    assert "LLCCA_PID" in {k.original_library for k in m.library_links}
