"""one failing case per model validation rule."""

from __future__ import annotations

from dataclasses import replace

import pytest

from plcexport.common import ExtractText
from plcexport.format.validate import validate_model
from plcexport.model import (
    CATEGORIES,
    CategoryCoverage,
    Coverage,
    ExportModel,
    ExportProject,
    ExportUnit,
    ExportVariable,
    ExportXref,
    Gap,
    HardwareModel,
    HmiModel,
    HmiObject,
    HmiScreen,
    HwChannel,
    HwModule,
    SafetyModel,
)


def coverage(**states: str) -> Coverage:
    cats = {c: CategoryCoverage("unavailable", "not_in_project") for c in CATEGORIES}
    for c, s in states.items():
        cats[c] = CategoryCoverage(s)  # type: ignore[arg-type]
    return Coverage(categories=cats)


def base_model() -> ExportModel:
    return ExportModel(
        project=ExportProject("testfixture", "fixture-1", "CPU", "Press 3", "testfixture", "1"),
        units=[
            ExportUnit("Main", "OB", "LAD", ("units/OB/Main.md",)),
            ExportUnit("PLC_Tags", "TAG_TABLE", None, ("units/TAG_TABLE/PLC_Tags.md",)),
        ],
        variables=[ExportVariable("PLC_Tags", "global_tag", '"I_Start"', "Bool", address="%I0.0")],
        xrefs=[ExportXref("Main", "variable", '"I_Start"', "read", 1, 3)],
        coverage=coverage(program_units="delivered", symbols="delivered"),
    )


def test_valid_model_has_no_violations() -> None:
    assert validate_model(base_model()) == []


def test_duplicate_unit_per_kind() -> None:
    m = base_model()
    m.units.append(ExportUnit("Main", "OB", "LAD", ()))
    assert any("duplicate unit OB 'Main'" in v for v in validate_model(m))


def test_same_name_different_kind_is_allowed() -> None:
    m = base_model()
    m.units.append(ExportUnit("Main", "FC", "SCL", ()))
    assert validate_model(m) == []


def test_duplicate_variable_path_key() -> None:
    m = base_model()
    m.variables.append(ExportVariable("PLC_Tags", "global_tag", "I_START", "Bool"))
    assert any("duplicate variable path_key" in v for v in validate_model(m))


def test_variable_in_unknown_unit() -> None:
    m = base_model()
    m.variables.append(ExportVariable("Nowhere", "global_tag", '"X"', "Bool"))
    assert any("unknown unit 'Nowhere'" in v for v in validate_model(m))


def test_xref_without_target_text() -> None:
    m = base_model()
    m.xrefs.append(ExportXref("Main", "variable", "  ", "read"))
    assert any("without target_text" in v for v in validate_model(m))


def test_dangling_channel_ref() -> None:
    m = base_model()
    m.xrefs[0] = replace(m.xrefs[0], channel_ref="ch-404")
    assert any("channel_ref 'ch-404' does not exist" in v for v in validate_model(m))


def test_existing_channel_and_hmi_refs_are_accepted() -> None:
    m = base_model()
    m.hardware = HardwareModel(
        modules=(HwModule("m1", "DI 16x24VDC"),), channels=(HwChannel("ch-1", "m1", "%I0.0"),)
    )
    m.hmi = HmiModel(screens=(HmiScreen("Main", "HMI_1", (HmiObject("Btn", "Button"),)),))
    m.xrefs[0] = replace(m.xrefs[0], channel_ref="ch-1")
    m.xrefs.append(
        ExportXref("hmi:Main", "variable", '"I_Start"', "unknown_direction", hmi_ref="Main/Btn")
    )
    m.coverage = coverage(
        program_units="delivered", symbols="delivered", hardware="delivered", hmi="delivered"
    )
    assert validate_model(m) == []


def test_dangling_hmi_ref() -> None:
    m = base_model()
    m.xrefs.append(ExportXref("hmi:Main", "variable", '"I_Start"', "read", hmi_ref="Main/Nope"))
    assert any("hmi_ref 'Main/Nope' does not exist" in v for v in validate_model(m))


def test_hmi_xref_must_come_from_its_screen() -> None:
    m = base_model()
    m.xrefs[0] = replace(m.xrefs[0], hmi_ref="Main/Btn")
    assert any("must come from its screen, not 'Main'" in v for v in validate_model(m))


def test_hmi_screen_name_may_contain_a_slash() -> None:
    m = base_model()
    m.hmi = HmiModel(screens=(HmiScreen("08-AnalogI/O", "HMI_1", (HmiObject("Btn", "Button"),)),))
    m.xrefs.append(
        ExportXref("hmi:08-AnalogI/O", "variable", '"I_Start"', "read", hmi_ref="08-AnalogI/O/Btn")
    )
    m.coverage = coverage(program_units="delivered", symbols="delivered", hmi="delivered")
    assert validate_model(m) == []


def test_variable_scope_must_match_unit() -> None:
    m = base_model()
    m.units.append(ExportUnit("FB_X", "FB", "SCL", (), variable_scope="fb_interface"))
    m.variables.append(ExportVariable("FB_X", "db_member", '"FB_X".a', "Bool"))
    assert any("differs from variable_scope" in v for v in validate_model(m))


def test_network_texts_belong_in_bodies() -> None:
    m = base_model()
    m.texts.append(ExtractText("Main", "title", "de", "NW title", network_no=1))
    assert any("belongs in unit_bodies" in v for v in validate_model(m))


def test_channel_with_unknown_module() -> None:
    m = base_model()
    m.hardware = HardwareModel(channels=(HwChannel("ch-1", "m-404", "%I0.0"),))
    assert any("module_ref 'm-404'" in v for v in validate_model(m))


def test_coverage_needs_exactly_seven_categories() -> None:
    m = base_model()
    cats = dict(m.coverage.categories)
    del cats["hmi"]
    cats["video"] = CategoryCoverage("unavailable", "unsupported")
    m.coverage = Coverage(categories=cats)
    (msg,) = [v for v in validate_model(m) if "coverage categories" in v]
    assert "'hmi'" in msg and "'video'" in msg


def test_delivered_requires_items() -> None:
    m = base_model()
    m.coverage = coverage(program_units="delivered", symbols="delivered", hardware="delivered")
    assert any("hardware: delivered but no items" in v for v in validate_model(m))


def test_unavailable_requires_reason() -> None:
    m = base_model()
    cats = dict(m.coverage.categories)
    cats["safety"] = CategoryCoverage("unavailable", None)
    m.coverage = Coverage(categories=cats)
    assert any("safety: unavailable without reason" in v for v in validate_model(m))


@pytest.mark.parametrize("reason", ["because", "other:", "PROTECTED"])
def test_invalid_reasons(reason: str) -> None:
    m = base_model()
    m.coverage = Coverage(
        categories=m.coverage.categories, gaps=(Gap("program_units", "FB1", reason),)
    )
    assert any("invalid reason" in v for v in validate_model(m))


def test_other_reason_with_text_is_valid() -> None:
    m = base_model()
    m.coverage = Coverage(
        categories=m.coverage.categories, gaps=(Gap("program_units", "FB1", "other:locked lib"),)
    )
    assert validate_model(m) == []


def test_safety_unit_must_be_listed_in_safety() -> None:
    m = base_model()
    m.units.append(ExportUnit("F_Main", "FB", "FBD", (), safety=True))
    assert any("safety units differ" in v and "F_Main" in v for v in validate_model(m))
    m.safety = SafetyModel(units=("F_Main",))
    m.coverage = coverage(program_units="delivered", symbols="delivered", safety="delivered")
    assert validate_model(m) == []


def test_safety_tag_listed_but_not_flagged() -> None:
    m = base_model()
    m.safety = SafetyModel(tags=('"I_Start"',))
    assert any("safety tags differ" in v for v in validate_model(m))


def test_guid_outside_platform_is_rejected() -> None:
    m = base_model()
    m.texts.append(ExtractText("Main", "comment", "de", "id 0f8fad5b-d9cb-469f-a165-70867728950e"))
    assert any("GUID-like value" in v for v in validate_model(m))
    m.texts.clear()
    m.platform = {"guid": "0f8fad5b-d9cb-469f-a165-70867728950e"}
    assert validate_model(m) == []


def test_binary_content_is_rejected() -> None:
    m = base_model()
    m.texts.append(ExtractText("Main", "comment", "de", "bad \x00 byte"))
    assert any("binary" in v for v in validate_model(m))


def test_text_for_unknown_unit() -> None:
    m = base_model()
    m.texts.append(ExtractText("Ghost", "title", "de", "x"))
    assert any("text for unknown unit 'Ghost'" in v for v in validate_model(m))


# ------------------------------------------------------------------ parts and libraries
def test_native_unit_file_missing_from_part() -> None:
    from plcexport.model import NativePart

    m = base_model()
    m.native_parts = [NativePart("siemens-simatic-sd", "sd", {"FB_A.s7dcl": b"x"})]
    m.units.append(ExportUnit("FB_A", "FB", "SCL", ("sd/FB_A.s7dcl", "sd/FB_A.s7res")))
    assert any("not in native part 'sd'" in v for v in validate_model(m))


def test_native_part_root_must_be_free_folder_name() -> None:
    from plcexport.model import NativePart

    m = base_model()
    m.native_parts = [NativePart("siemens-simatic-sd", "units", {"a.s7dcl": b"x"})]
    assert any("free top-level folder" in v for v in validate_model(m))


def test_native_part_files_must_be_utf8() -> None:
    from plcexport.model import NativePart

    m = base_model()
    m.native_parts = [NativePart("siemens-simatic-sd", "sd", {"a.s7dcl": b"\xff\xfe"})]
    assert any("not UTF-8" in v for v in validate_model(m))


def test_invalid_library_is_reported() -> None:
    from plcexport.model import LibraryModel

    m = base_model()
    m.library = LibraryModel("Proj", None, "project", company=True)
    assert any('library: company only on kind="global"' in v for v in validate_model(m))


def test_library_guid_must_stay_in_platform_part() -> None:
    from plcexport.model import LibraryLink

    m = base_model()
    m.library_links = [
        LibraryLink(
            "Main", "unit", "0f8fad5b-d9cb-469f-a165-70867728950e", "T", "1.0", "released", None
        )
    ]
    assert any("GUID-like value outside platform/ at library_links" in v for v in validate_model(m))


def test_link_from_unknown_unit() -> None:
    from plcexport.model import LibraryLink

    m = base_model()
    m.library_links = [LibraryLink("FB_Missing", "unit", "Conveyor", "T", "1.0", "released", None)]
    assert any("library link from unknown unit 'FB_Missing'" in v for v in validate_model(m))
