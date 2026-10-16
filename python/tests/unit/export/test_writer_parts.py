"""native parts, libraries and link facts in the common format
(contracts/common-format-tia.md §1-§4)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime

from plcexport.format.reader import read_files
from plcexport.format.validate import validate_files
from plcexport.format.writer import ManifestInfo, native_part_checksum, render
from plcexport.model import (
    CATEGORIES,
    CategoryCoverage,
    Coverage,
    ExportModel,
    ExportProject,
    ExportUnit,
    LibraryLink,
    LibraryModel,
    LibraryType,
    NativePart,
    TypeVersion,
    Upgrade,
)

INFO = ManifestInfo(
    source_path="Werk1/Line3/Line3.zap19",
    checksum="sha256:" + "0" * 64,
    exported_at=datetime(2026, 10, 9, tzinfo=UTC),
)

S7DCL = (
    "FUNCTION_BLOCK \"FB_Conveyor\"\r\n{ S7_Optimized_Access := 'TRUE' }\r\nEND_FUNCTION_BLOCK\r\n"
)
S7RES = "﻿Title:\r\n  en-US: Conveyor\r\n"


def _coverage() -> Coverage:
    cats = {c: CategoryCoverage("unavailable", "not_in_project") for c in CATEGORIES}
    cats["program_units"] = CategoryCoverage("delivered")
    return Coverage(categories=cats)


def _model(**kw: object) -> ExportModel:
    m = ExportModel(
        project=ExportProject(
            "siemens-tia",
            "V21",
            "6ES7 516-3AN02-0AB0",
            None,
            "tia",
            "1.0.0",
            ("en-US",),
            device="PLC_1",
        ),
        units=[
            ExportUnit(
                "FB_Conveyor",
                "FB",
                "SCL",
                ("sd/Conveyor/FB_Conveyor.s7dcl", "sd/Conveyor/FB_Conveyor.s7res"),
                number=12,
                folder="Conveyor",
            )
        ],
        native_parts=[
            NativePart(
                "siemens-simatic-sd",
                "sd",
                {
                    "Conveyor/FB_Conveyor.s7dcl": S7DCL.encode("utf-8"),
                    "Conveyor/FB_Conveyor.s7res": S7RES.encode("utf-8"),
                },
            )
        ],
        coverage=_coverage(),
    )
    for k, v in kw.items():
        setattr(m, k, v)
    return m


def _bytes(files: dict[str, str]) -> dict[str, bytes]:
    return {k: v.encode("utf-8") for k, v in files.items()}


def test_native_files_are_written_byte_exact() -> None:
    files = render(_model(), INFO)
    assert files["sd/Conveyor/FB_Conveyor.s7dcl"].encode("utf-8") == S7DCL.encode("utf-8")
    assert files["sd/Conveyor/FB_Conveyor.s7res"].encode("utf-8") == S7RES.encode("utf-8")
    # an SD unit gets no common-format unit file
    assert not any(p.startswith("units/") for p in files)


def test_manifest_lists_parts_with_checksum() -> None:
    m = _model()
    manifest = json.loads(render(m, INFO)["manifest.json"])
    part = m.native_parts[0]
    assert manifest["parts"] == [
        {"kind": "common", "path": "."},
        {
            "kind": "siemens-simatic-sd",
            "path": "sd",
            "files": 2,
            "checksum": native_part_checksum(part.files),
        },
    ]
    assert manifest["device"] == "PLC_1"
    assert "kind" not in manifest  # default "project" is not written


def test_part_checksum_covers_paths_and_contents() -> None:
    a = native_part_checksum({"x.s7dcl": b"1", "y.s7res": b"2"})
    assert a == native_part_checksum({"y.s7res": b"2", "x.s7dcl": b"1"})
    assert a != native_part_checksum({"x.s7dcl": b"1", "y.s7res": b"3"})
    assert a != native_part_checksum({"z.s7dcl": b"1", "y.s7res": b"2"})
    assert a.startswith("sha256:") and len(a) == len("sha256:") + len(hashlib.sha256().hexdigest())


def test_index_lists_sd_units_with_their_sd_path() -> None:
    index = render(_model(), INFO)["index.md"]
    assert "| unit (SD) | FB_Conveyor | sd/Conveyor/FB_Conveyor.s7dcl |" in index
    assert "| part | siemens-simatic-sd | parts/siemens-simatic-sd.json |" in index


def test_export_with_native_part_is_valid() -> None:
    assert validate_files(_bytes(render(_model(), INFO))) == []


def test_validation_reports_a_changed_native_file() -> None:
    files = _bytes(render(_model(), INFO))
    files["sd/Conveyor/FB_Conveyor.s7dcl"] += b"// changed\r\n"
    assert any("checksum" in v for v in validate_files(files))


def test_upgrade_messages_and_library_kind_in_manifest() -> None:
    m = _model()
    m.project = replace(
        m.project, kind="library", upgrade=Upgrade("V19", "V21", "TIA Portal V21", ("upgraded",))
    )
    manifest = json.loads(render(m, INFO)["manifest.json"])
    assert manifest["kind"] == "library"
    assert manifest["upgrade"]["messages"] == ["upgraded"]


def _library() -> LibraryModel:
    v = TypeVersion(
        "1.2.0", "released", None, "2025-03-14", {"en-US": "Speed ramp"}, "sd",
        "sd/Conveyor/1.2.0/FB_Conveyor.s7dcl",
    )  # fmt: skip
    conveyor = LibraryType("Conveyor", "Types/Material", "plc_block", (v,))
    return LibraryModel("Project library", None, "project", types=(conveyor,))


def test_library_and_link_facts_are_written_canonically() -> None:
    m = _model(
        library=_library(),
        library_links=[
            LibraryLink(
                "FB_Conveyor",
                "unit",
                "Conveyor",
                "Types/Material",
                "1.2.0",
                "released",
                "ACME_Standard",
            )
        ],
        platform_files={
            "library_ids.json": {"Types/Material/Conveyor": "0f8fad5b-d9cb-469f-a165-70867728950e"}
        },
    )
    files = render(m, INFO)
    lib = json.loads(files["library.json"])
    assert lib["types"][0]["versions"][0]["version"] == "1.2.0"
    links = json.loads(files["library_links.json"])
    assert links["compared_with"] == []
    assert links["links"] == [
        {
            "comparison": "not_compared",
            "library": None,
            "newest_released": None,
            "object": "FB_Conveyor",
            "object_kind": "unit",
            "origin": "unknown_library",
            "original_library": "ACME_Standard",
            "status": "released",
            "type_folder": "Types/Material",
            "type_name": "Conveyor",
            "version": "1.2.0",
        }
    ]
    assert "platform/siemens-tia/library_ids.json" in files
    assert validate_files(_bytes(files)) == []


def test_round_trip_keeps_parts_library_and_links() -> None:
    m = _model(
        library=_library(),
        library_links=[
            LibraryLink(
                "FB_Conveyor", "unit", "Conveyor", "Types/Material", "1.2.0", "released", None
            )
        ],
    )
    files = render(m, INFO)
    again = render(read_files(files).model, INFO)
    assert again == files


def test_export_without_new_fields_is_unchanged() -> None:
    m = ExportModel(
        project=ExportProject("synthetic", "1", "CPU", "Line", "synthetic", "1", ("de",)),
        units=[ExportUnit("Main", "OB", "LAD", (), number=1)],
        coverage=_coverage(),
    )
    manifest = json.loads(render(m, INFO)["manifest.json"])
    assert "parts" not in manifest and "kind" not in manifest and "device" not in manifest
    assert "library.json" not in render(m, INFO)
