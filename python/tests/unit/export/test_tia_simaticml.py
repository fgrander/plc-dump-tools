"""SimaticML → units, interfaces and NTN bodies, on real TIA V21 exports (never
hand-written SimaticML; fixtures from the tank sample, see tests/fixtures/tiadump/README.md)."""

from __future__ import annotations

from pathlib import Path

import pytest

from plcexport.extractors.tia.simaticml import parse_tag_table, parse_unit
from tests.conftest import FIXTURES

TANK = FIXTURES / "tiadump" / "tank_v19" / "simaticml" / "Tank application"
SAMPLES = FIXTURES / "tiadump" / "simaticml_tank"


def _unit(path: Path):  # type: ignore[no-untyped-def]
    return parse_unit(path.read_bytes())


def test_library_type_version_wrapper_is_unwrapped() -> None:
    """``LibraryTypeVersion.Export`` (TIA V21) puts the block inside
    ``<SW.Blocks.CodeBlockLibraryTypeVersion><ObjectList>`` with
    ``CompositionName="ContentObject"``, as seen on the LBCFC library. That dump stays local
    (SIOS download), so the wrapper is put around a recorded block here; the block itself is
    unchanged TIA output."""
    import xml.etree.ElementTree as ET

    plain = SAMPLES / "LSim_PT1.xml"
    doc = ET.parse(plain)  # noqa: S314 - recorded fixture
    root = doc.getroot()
    block = next(e for e in root if e.tag.startswith("SW.Blocks."))
    root.remove(block)
    wrapper = ET.SubElement(root, "SW.Blocks.CodeBlockLibraryTypeVersion", {"ID": "0"})
    ET.SubElement(ET.SubElement(wrapper, "AttributeList"), "VersionNumber").text = "1.0.0"
    block.set("CompositionName", "ContentObject")
    ET.SubElement(wrapper, "ObjectList").append(block)
    wrapped = parse_unit(ET.tostring(root, encoding="utf-8", xml_declaration=True))
    expected = _unit(plain)
    assert (wrapped.name, wrapped.kind, wrapped.number, wrapped.language) == (
        expected.name,
        expected.kind,
        expected.number,
        expected.language,
    )
    assert wrapped.body == expected.body and wrapped.members == expected.members


def test_document_without_a_block_is_rejected() -> None:
    with pytest.raises(ValueError, match="no block or PLC data type"):
        parse_unit(b"<Document><SW.Blocks.CodeBlockLibraryTypeVersion ID='0'/></Document>")


def test_graph_becomes_steps_actions_and_transitions() -> None:
    u = _unit(TANK / "units" / "Programmbausteine" / "FB_5_CIP_Simulation_Graph.xml")
    assert (u.name, u.kind, u.number, u.language) == ("FB_5_CIP_Simulation_Graph", "FB", 7, "GRAPH")
    assert u.body.language == "ntn" and not u.partial
    code = u.body.networks[0].code
    assert code.startswith('INITIAL STEP "Initial step";')
    assert "  ACTION N { #statTemperature := 0 }" in code
    assert "  ACTION N { (* Simulate random abnomalies *) }" in code  # comment cannot eat code
    assert "ACTION N {  }" not in code  # empty action lines are left out
    assert (
        'TRANSITION "Initial step" -> "Step1: pre-rinse" WHEN #cip.cipStep1; // Start step 1'
        in code
    )
    assert 'TRANSITION "Step4: final-rinse" -> Reset WHEN NOT #cip.cipActive; // End' in code
    assert "TRANSITION Reset -> END WHEN TRUE; // Trans8" in code  # no condition, end of chain


def test_graph_branches_link_steps_through_the_branch() -> None:
    """An alternative branch (``AltBegin``/``AltEnd`` nodes between steps and transitions), as in
    ``Baustein_Graph`` of the reference sample ``myTiaProject1``: every transition names its
    steps, none is ``"?"``."""
    u = _unit(
        FIXTURES / "tiadump" / "conn_v21" / "simaticml" / "PLC_1" / "units" / "Programmbausteine"
        / "Baustein_Graph.xml"
    )  # fmt: skip
    assert u.language == "GRAPH" and not u.partial
    transitions = [ln for ln in u.body.networks[0].code.splitlines() if ln.startswith("TRANSITION")]
    assert transitions == [
        "TRANSITION Step1 -> Step2 WHEN TRUE; // Trans1",
        "TRANSITION Step2 -> Step3 WHEN TRUE; // Trans2",
        "TRANSITION Step3 -> Step5 WHEN TRUE; // Trans3",
        "TRANSITION Step3 -> Step4 WHEN TRUE; // Trans4",
        "TRANSITION Step4 -> Step6 WHEN TRUE; // Trans5",
        "TRANSITION Step5 -> Step6 WHEN TRUE; // Trans6",
        "TRANSITION Step6 -> END WHEN TRUE; // Trans7",
    ]


def test_interface_sections_types_comments() -> None:
    u = _unit(TANK / "units" / "Programmbausteine" / "FB_5_CIP_Simulation_Graph.xml")
    sections = {m.section for m in u.members}
    assert {"IN", "OUT", "STATIC", "TEMP"} <= sections
    stat = next(m for m in u.members if m.name == "statTemperature")
    assert stat.section == "STATIC" and stat.data_type == "Real"


def test_lad_with_scl_networks_and_system_instructions() -> None:
    u = _unit(SAMPLES / "FB_Generate_Serial_Number.xml")
    assert u.language == "LAD" and u.body.language == "ntn" and not u.partial
    nw1, nw2, nw3 = (n.code for n in u.body.networks[:3])
    assert '"FC_2_GetStringSizeOfNumber"(number := #batchId, stringSize => #sizeBatch);' in nw1
    edge = "IF P_TRIG(#pTrigAux_1, #trigger) THEN "
    assert edge + "RD_LOC_T(OUT := #localTime, RET_VAL := #retVal); END_IF;" in nw2
    assert edge + "S_Move(in := String#'', out => #batchString); END_IF;" in nw2
    assert nw3.startswith("#serialNumber := CONCAT(IN1 := REPLACE(IN1 := DELETE(IN := #dateString")
    assert "<call>" not in nw3 and "<GlobalVariable>" not in nw1


def test_fbd_boxes_edges_and_flipflops() -> None:
    u = _unit(SAMPLES / "FB_2_Filling.xml")
    assert u.language == "FBD" and u.body.language == "ntn"
    nw1, nw2, nw3 = (n.code for n in u.body.networks[:3])
    assert nw1 == "Mul(in1 := #model.bottle.maxLevel, in2 := 1000.0, out => #tempBottleMaxLevel);"
    assert nw2 == (
        "IF P_TRIG(#statFillingTankTrigger, #operate.state.FillingTank) THEN "
        "Add(in1 := #process.batchId, in2 := UDInt#1, out => #process.batchId); END_IF;"
    )
    assert "Sr(operand := #statHmiDoShift, r1 := #operate.state.ShiftingBottle, s := " in nw3
    assert "MOVE(#signals.bottleSignals.actLevel, #statHmiBottleLevel);" in nw3
    assert u.body.networks[0].title == {"en-US": "Calculation of params"}


def test_scl_block_keeps_its_source() -> None:
    u = _unit(SAMPLES / "LSim_PT1.xml")
    assert (u.language, u.body.language) == ("SCL", "scl")
    assert "(c)Copyright 2017 All Rights Reserved" in u.body.networks[0].code


def test_prodiag_instance_db_has_its_members() -> None:
    u = _unit(TANK / "units" / "Programmbausteine" / "Block_1_DB.xml")
    assert (u.kind, u.language) == ("IDB", "DB")
    assert [m.name for m in u.members] == ["PC_Flags", "State"]


def test_tag_table_with_user_constants() -> None:
    name, tags = parse_tag_table(
        (TANK / "tags" / "PLC-Variablen" / "Default tag table.xml").read_bytes()
    )
    assert name == "Default tag table" and len(tags) == 34
    manipulator = next(t for t in tags if t.name == "Manipulator")
    assert (manipulator.address, manipulator.data_type, manipulator.constant) == (
        "%MW0",
        "Int",
        False,
    )
    assert any(t.constant for t in tags)  # ERROR_* user constants
    assert [t.name for t in tags] == sorted(t.name for t in tags)


def test_untrusted_xml_entities_are_refused() -> None:
    bomb = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><Document>&a;</Document>'
    with pytest.raises(Exception, match=r"(?i)entit"):
        parse_unit(bomb)
