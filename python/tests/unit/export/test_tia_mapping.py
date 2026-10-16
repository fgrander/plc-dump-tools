"""tiadump dump -> ExportBundle, on the recorded fixtures and on small synthetic dumps for
cases the samples do not contain."""

from __future__ import annotations

import copy
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from plcexport.extractors.tia.mapping import (
    PROJECT_DEVICE,
    R_INCONSISTENT,
    R_MISMATCH,
    R_UNSUPPORTED,
    MappingOptions,
    to_bundle,
)
from plcexport.format.validate import validate_files
from plcexport.format.writer import ManifestInfo, render
from plcexport.model import CATEGORIES, ExportBundle, ExportModel
from tests.conftest import FIXTURES

TIADUMP = FIXTURES / "tiadump"
OPTS = MappingOptions("tia", "1.0.0")
INFO = ManifestInfo(
    source_path="Werk1/Line3/project.zap19",
    checksum="sha256:" + "0" * 64,
    exported_at=datetime(2026, 10, 9, tzinfo=UTC),
)


def _load(name: str) -> tuple[dict[str, Any], Path]:
    d = TIADUMP / name
    return json.loads((d / "dump.json").read_text(encoding="utf-8")), d


def _bundle(name: str) -> ExportBundle:
    dump, d = _load(name)
    return to_bundle(dump, d, OPTS)


def _model(b: ExportBundle, device: str) -> ExportModel:
    return next(m for m in b.models if m.project.device == device)


def _gaps(m: ExportModel) -> dict[str, str]:
    return {g.item: g.reason for g in m.coverage.gaps}


# ------------------------------------------------------------------ recorded fixtures
@pytest.mark.parametrize("name", ["step7_v21", "tank_v19", "pid_v19"])
def test_every_model_validates_and_states_all_categories(name: str) -> None:
    for m in _bundle(name).models:
        assert set(m.coverage.categories) == set(CATEGORIES)
        files = {k: v.encode("utf-8") for k, v in render(m, INFO).items()}
        assert validate_files(files) == [], m.project.device
        assert not [w for w in m.warnings if w.code == "completeness_mismatch"]


def test_one_model_per_plc() -> None:
    b = _bundle("step7_v21")
    assert [m.project.device for m in b.models] == ["PLC_1", "PLC_2", "PLC_S120Democase"]
    m = _model(b, "PLC_1")
    assert (m.project.platform_id, m.project.controller) == ("siemens-tia", "6ES7 515-2UN03-0AB0")


def test_sd_units_are_listed_with_their_native_files() -> None:
    m = _model(_bundle("tank_v19"), "Tank application")
    main = next(u for u in m.units if u.name == "Main")
    assert main.files == (
        "sd/Programmbausteine/Main.s7dcl",
        "sd/Programmbausteine/Main.s7res",
    )
    assert "Main" not in m.unit_bodies  # body "none": the content is the SD part
    (part,) = m.native_parts
    assert (part.kind, part.root) == ("siemens-simatic-sd", "sd")
    # as TIA wrote it, except the text IDs, which are renumbered in a stable order
    recorded = (
        TIADUMP / "tank_v19" / "sd" / "Tank application" / "Programmbausteine" / "Main.s7dcl"
    ).read_bytes()
    text_id = re.compile(rb"MLC_[0-9A-Za-z]+")
    exported = part.files["Programmbausteine/Main.s7dcl"]
    assert text_id.sub(b"MLC_x", exported) == text_id.sub(b"MLC_x", recorded)


def test_each_unit_is_in_exactly_one_part() -> None:
    m = _model(_bundle("tank_v19"), "Tank application")
    for u in m.units:
        in_sd = bool(u.files) and all(f.startswith("sd/") for f in u.files)
        in_common = u.name in m.unit_bodies
        assert not (in_sd and in_common), u.name
    graph = next(u for u in m.units if u.name == "FB_5_CIP_Simulation_Graph")
    assert graph.files == () and m.unit_bodies[graph.name].language == "ntn"
    assert graph.attributes["route"] == "simaticml"


def test_simaticml_units_bring_their_interface() -> None:
    m = _model(_bundle("tank_v19"), "Tank application")
    stat = next(
        v for v in m.variables if v.symbolic_path == '"FB_5_CIP_Simulation_Graph".statTemperature'
    )
    assert (stat.scope, stat.section, stat.data_type) == ("fb_interface", "STATIC", "Real")


def test_tag_tables_become_global_tags_and_constants() -> None:
    m = _model(_bundle("tank_v19"), "Tank application")
    table = next(u for u in m.units if u.kind == "TAG_TABLE")
    assert table.name == "Default tag table"
    tags = [v for v in m.variables if v.scope == "global_tag"]
    assert len(tags) == 34
    manipulator = next(v for v in tags if v.symbolic_path == '"Manipulator"')
    assert (manipulator.address, manipulator.io_direction) == ("%MW0", "memory")
    assert any(v.section == "CONSTANT" for v in tags)


def test_protected_and_unsupported_units_are_names_with_gaps() -> None:
    m = _model(_bundle("step7_v21"), "PLC_S120Democase")
    assert _gaps(m)["MC_Servo"] == "protected"
    servo = next(u for u in m.units if u.name == "MC_Servo")
    assert servo.protected and servo.parse_quality == "names_only"
    tank = _model(_bundle("tank_v19"), "Tank application")
    assert _gaps(tank)["FB_Prodiag"] == R_UNSUPPORTED


def test_f_units_are_safety_units() -> None:
    m = _model(_bundle("step7_v21"), "PLC_1")
    assert m.safety.units == ("Main_Safety_RTG1", "Main_Safety_RTG1_DB")
    assert next(u for u in m.units if u.name == "Main_Safety_RTG1").safety
    assert m.coverage.categories["safety"].state == "partial"  # no signatures in this dump


def test_hardware_controller_modules_and_networks() -> None:
    m = _model(_bundle("tank_v19"), "Tank application")
    assert [c.name for c in m.hardware.controllers] == ["Tank application"]
    cpu = next(x for x in m.hardware.modules if x.type == "Tank application")
    assert (cpu.order_no, cpu.firmware, cpu.slot) == ("6ES7 513-1AL02-0AB0", "V2.8", 1)
    net = next(n for n in m.hardware.networks if n.ref == "S71500/ET200MP station_1/X1/Ethernet")
    assert (net.address, net.subnet) == ("192.168.112.1/24", "PN/IE_1")


def test_comfort_hmi_with_screens_bindings_and_xrefs() -> None:
    m = _model(_bundle("tank_v19"), "Tank application")  # single PLC: the HMIs belong to it
    assert {(d.name, d.type) for d in m.hmi.devices} == {
        ("HMI_RT_5", "comfort"),
        ("MTP1500_Runtime", "unified"),
    }
    assert len(m.hmi.hmi_tags) == 70
    assert [s.name for s in m.hmi.screens] == ["10_Startscreen", "30_Diagnostics"]
    io = next(o for s in m.hmi.screens for o in s.objects if "tankTemperature" in o.tag_bindings)
    assert io.type == "IOField"
    assert any(x.hmi_ref and x.target_text == "tankTemperature" for x in m.xrefs)
    assert any(w.code == "hmi_plc_tag_unknown" for w in m.warnings)


def test_missing_package_is_a_gap_on_the_device() -> None:
    m = _model(_bundle("tank_v19"), "Tank application")
    reason = "other:missing package WinCC Unified Comfort V21"
    assert _gaps(m)["MTP1500_Runtime"] == reason
    assert m.coverage.categories["hmi"].state == "partial"
    assert _gaps(m)["HMI_RT_5 alarms"] == "unsupported"


def test_plc_alarms_and_inherited_texts() -> None:
    m = _model(_bundle("step7_v21"), "PLC_S120Democase")
    assert m.hmi.alarms and all(a.id.startswith("plc:") for a in m.hmi.alarms)
    assert any(w.code == "alarm_text_inherited" for w in m.warnings)


def test_upgrade_and_platform_facts() -> None:
    m = _model(_bundle("tank_v19"), "Tank application")
    assert m.project.upgrade is not None
    assert (m.project.upgrade.from_version, m.project.upgrade.to_version) == ("V19", "V21")
    assert m.project.upgrade.messages
    assert m.platform["compiled_units"] == [
        "Block_1_DB",
        "FB_5_CIP_Simulation_Graph",
        "FB_Prodiag",
        "ProDiagOB",
    ]
    assert "WinCC Unified Comfort V21" in m.platform["missing_packages"]


def test_structure_has_folders_obs_and_devices() -> None:
    m = _model(_bundle("tank_v19"), "Tank application")
    assert "Main" in {t.name for t in m.structure.tasks}
    folder = next(f for f in m.structure.folders if f.path == "Programmbausteine")
    assert "Main" in folder.units
    assert {d.name for d in m.structure.devices} >= {"S71500/ET200MP station_1"}


def test_mapping_is_deterministic() -> None:
    a, b = _bundle("pid_v19"), _bundle("pid_v19")
    assert [render(m, INFO) for m in a.models] == [render(m, INFO) for m in b.models]


# ------------------------------------------------------------------ synthetic dumps
def _synthetic(tmp_path: Path) -> dict[str, Any]:
    """Two PLCs with I/O, an F-signature, a unit that failed to compile, an HMI connected to
    both PLCs and one of an unknown family."""
    tbl = tmp_path / "simaticml" / "PLC_A" / "tags" / "IO.xml"
    tbl.parent.mkdir(parents=True)
    tbl.write_text(
        '<?xml version="1.0" encoding="utf-8"?><Document><SW.Tags.PlcTagTable ID="0">'
        "<AttributeList><Name>IO</Name></AttributeList><ObjectList>"
        '<SW.Tags.PlcTag ID="1" CompositionName="Tags"><AttributeList>'
        "<DataTypeName>Bool</DataTypeName><LogicalAddress>%I2.3</LogicalAddress>"
        "<Name>Start</Name></AttributeList></SW.Tags.PlcTag>"
        '<SW.Tags.PlcTag ID="2" CompositionName="Tags"><AttributeList>'
        "<DataTypeName>Word</DataTypeName><LogicalAddress>%QW8</LogicalAddress>"
        "<Name>Speed</Name></AttributeList></SW.Tags.PlcTag>"
        "</ObjectList></SW.Tags.PlcTagTable></Document>",
        encoding="utf-8",
    )
    unit = {
        "name": "FB_Bad", "kind": "FB", "number": 3, "language": "LAD", "folder": "Program",
        "protected": False, "safety": False, "consistent": False, "attributes": {},
        "part": "none", "files": [], "error": "compile failed: syntax", "sd_error": "x",
    }  # fmt: skip
    plc = {
        "kind": "plc", "family": "S7-1500", "firmware": "V3.1", "library_links": [],
        "connected_hmis": [], "alarms": {"texts_file": None, "supervisions_file": None},
    }  # fmt: skip
    io = {"name": "DI 16x24VDC", "path": "DI 16x24VDC", "rack": "Rail_0", "slot": 2,
          "order_no": "6ES7 521-1BH00-0AB0", "firmware": "V2.1",
          "addresses": [{"io": "input", "start": 2, "length": 16}], "interfaces": []}  # fmt: skip
    dq = {**io, "name": "DQ 16", "path": "DQ 16", "slot": 3, "order_no": "6ES7 522-1BH00-0AB0",
          "addresses": [{"io": "output", "start": 8, "length": 16}]}  # fmt: skip
    cpu = {"name": "PLC_A", "path": "PLC_A", "rack": "Rail_0", "slot": 1, "addresses": [],
           "order_no": "6ES7 516-3AN02-0AB0", "firmware": "V3.1", "interfaces": []}  # fmt: skip
    return {
        "dump_version": 1,
        "tool": {"version": "1.0.0"},
        "source": {"file": "p.zap21", "kind": "project", "saved_version": "V21"},
        "tia": {"version": "V21", "upgrade": None},
        "languages": {"project": ["de-DE"], "editing": "de-DE", "reference": "de-DE"},
        "multiuser": {"kind": "none"},
        "missing_packages": [],
        "devices": [
            {
                **plc,
                "name": "PLC_A",
                "order_no": "6ES7 516-3AN02-0AB0",
                "units": [unit],
                "tag_tables": [
                    {"name": "IO", "folder": "Tags", "file": "simaticml/PLC_A/tags/IO.xml"}
                ],
                "safety": {
                    "signatures": [{"kind": "CollectiveOfflineSignature", "value": "0x1A2B3C4D"}]
                },
            },
            {
                **plc,
                "name": "PLC_B",
                "order_no": "6ES7 511-1AK02-0AB0",
                "units": [],
                "tag_tables": [],
                "safety": {"signatures": []},
            },
            {
                "kind": "hmi",
                "name": "HMI_Both",
                "hmi_family": "unified",
                "alarms": [],
                "library_links": [],
                "screens": [],
                "tags": [{"name": "T1", "plc_tag": "Start"}],
                "connections": [{"Partner": "PLC_A"}, {"Partner": "PLC_B"}],
            },
            {
                "kind": "hmi",
                "name": "Panel_Old",
                "hmi_family": "basic_panel",
                "alarms": [],
                "library_links": [],
                "screens": [],
                "tags": [],
                "connections": [],
            },
        ],
        "hardware": {
            "devices": [
                {"name": "Station_A", "items": [cpu, io, dq]},
                {
                    "name": "Station_B",
                    "items": [
                        {**cpu, "name": "PLC_B", "path": "PLC_B", "order_no": "6ES7 511-1AK02-0AB0"}
                    ],
                },
                {
                    "name": "Drive_1",
                    "items": [
                        {
                            **io,
                            "name": "G120",
                            "path": "G120",
                            "order_no": "6SL3 246-0BA22-1FA0",
                            "addresses": [],
                        }
                    ],
                },
            ],
            "subnets": [],
        },
        "project_library": None,
        "library": None,
        "compiled_units": ["PLC_A/FB_Bad"],
        "counts": {
            "PLC_A": {"units": 1, "tag_tables": 1, "tags": 2},
            "PLC_B": {"units": 0, "tag_tables": 0, "tags": 0},
            "HMI_Both": {"hmi_tags": 1, "screens": 0},
            "_hardware": {"modules": 5},
        },
        "errors": [{"kind": "compile_failed", "where": "PLC_A/FB_Bad", "message": "syntax"}],
        "cleanup": {"outside_work": []},
    }


def test_project_model_takes_shared_hmis_and_plc_less_hardware(tmp_path: Path) -> None:
    b = to_bundle(_synthetic(tmp_path), tmp_path, OPTS)
    assert [m.project.device for m in b.models] == ["PLC_A", "PLC_B", PROJECT_DEVICE]
    proj = _model(b, PROJECT_DEVICE)
    assert [d.name for d in proj.hmi.devices] == ["HMI_Both", "Panel_Old"]
    assert [x.type for x in proj.hardware.modules] == ["G120"]
    assert proj.units == [] and proj.project.controller is None
    assert _gaps(proj)["Panel_Old"] == "unsupported"
    assert proj.hmi.hmi_tags[0].plc_tag == "Start"


def test_io_tags_are_linked_to_module_channels(tmp_path: Path) -> None:
    m = _model(to_bundle(_synthetic(tmp_path), tmp_path, OPTS), "PLC_A")
    di = next(x for x in m.hardware.modules if x.type == "DI 16x24VDC")
    assert di.address_ranges == ("%I2.0-%I3.7",)
    assert {(c.symbol, c.module_ref) for c in m.hardware.channels} == {
        ('"Start"', "Station_A/DI 16x24VDC"),
        ('"Speed"', "Station_A/DQ 16"),
    }


def test_signatures_unchanged_and_inconsistent_unit_gap(tmp_path: Path) -> None:
    m = _model(to_bundle(_synthetic(tmp_path), tmp_path, OPTS), "PLC_A")
    (sig,) = m.safety.signatures
    assert (sig.kind, sig.value) == ("CollectiveOfflineSignature", "0x1A2B3C4D")
    assert _gaps(m)["FB_Bad"] == R_INCONSISTENT
    assert not [w for w in m.warnings if w.code == "completeness_mismatch"]


def test_completeness_mismatch_is_reported(tmp_path: Path) -> None:
    dump = copy.deepcopy(_synthetic(tmp_path))
    dump["counts"]["PLC_A"]["units"] = 3
    dump["counts"]["_hardware"]["modules"] = 9
    m = _model(to_bundle(dump, tmp_path, OPTS), "PLC_A")
    codes = [w.message for w in m.warnings if w.code == "completeness_mismatch"]
    assert any("program_units" in c and "3" in c for c in codes)
    assert any("hardware" in c for c in codes)
    assert m.coverage.categories["program_units"].state == "partial"
    assert m.coverage.categories["program_units"].reason == R_MISMATCH
    assert m.coverage.categories["hardware"].reason == R_MISMATCH


def test_missing_base_product_gaps_the_program(tmp_path: Path) -> None:
    dump = _synthetic(tmp_path)
    plc_b = dump["devices"][1]
    plc_b["missing_package"] = "STEP 7 Professional V21"
    dump["counts"]["PLC_B"]["units"] = 7
    m = _model(to_bundle(dump, tmp_path, OPTS), "PLC_B")
    assert _gaps(m)["PLC_B (program)"] == "other:missing package STEP 7 Professional V21"
    assert m.coverage.categories["program_units"].state == "unavailable"
    assert not [w for w in m.warnings if w.code == "completeness_mismatch"]


# ------------------------------------------------------------------ 010 connections
def _with_connections(**per_plc: Any) -> ExportBundle:
    """step7_v21 with ``configured_connections`` (or an error text) on the named PLCs."""
    dump, d = _load("step7_v21")
    dump = copy.deepcopy(dump)
    for dev in dump["devices"]:
        if dev["name"] in per_plc:
            value = per_plc[dev["name"]]
            if isinstance(value, str):
                dev["configured_connections"] = []
                dev["configured_connections_error"] = value
            else:
                dev["configured_connections"] = value
    return to_bundle(dump, d, OPTS)


def _conn(ident: str, partner: str = "192.168.1.50", **kw: Any) -> dict[str, Any]:
    return {
        "class": "S7Connection", "type": "S7Connection", "type_value": 0, "owner_item": "PLC_1",
        "local_name": f"S7_{ident}", "local_id": ident, "local_address": "192.168.1.3",
        "local_interface": "X2", "local_node_type": "Ethernet", "local_tsap": "14.01",
        "local_active": True, "partner_address": partner, "partner_rack": 0, "partner_slot": 2,
        "partner_tsap": "15.02", "valid": True,
    } | kw  # fmt: skip


def test_connections_go_into_their_plcs_export() -> None:
    b = _with_connections(PLC_1=[_conn("100"), _conn("101")], PLC_2=[])
    p1, p2 = _model(b, "PLC_1"), _model(b, "PLC_2")
    assert [c.ref for c in p1.connections.connections] == [
        "PLC_1/PLC_1/0x0100",
        "PLC_1/PLC_1/0x0101",
    ]
    c = p1.connections.connections[0]
    assert (c.local.module, c.local.interface) == ("PLC_1/PLC_1", "PLC_1/X2/Ethernet")
    cov1 = p1.coverage.categories["connections"]  # PLC_1 has know-how protected blocks
    assert (cov1.state, cov1.reason) == (
        "partial",
        "other:calls in 1 protected block(s) not readable",
    )
    assert p2.connections.item_count() == 0
    cov = p2.coverage.categories["connections"]
    assert (cov.state, cov.reason) == ("unavailable", "not_in_project")
    # an export without the dump key (older tiadump) says nothing about connections
    assert "connections" not in _model(b, "PLC_S120Democase").coverage.categories


def test_unreadable_connections_are_partial() -> None:
    b = _with_connections(PLC_1="TIA Portal failed: no access")
    m = _model(b, "PLC_1")
    cov = m.coverage.categories["connections"]
    assert (
        cov.state == "partial"
        and cov.reason == "other:connections not readable: TIA Portal failed: no access"
    )
    assert validate_files({k: v.encode("utf-8") for k, v in render(m, INFO).items()}) == []


def test_connection_exports_validate_and_are_deterministic() -> None:
    acc = _conn(
        "102",
        "192.168.1.5",
        partner_name="PLC_2",
        local_tsap="SIMATIC-ACC10201",
        partner_tsap="SIMATIC-ACC11001",
    )
    b1 = _with_connections(PLC_1=[_conn("100"), acc])
    b2 = _with_connections(PLC_1=[acc, _conn("100")])
    files1 = render(_model(b1, "PLC_1"), INFO)
    assert files1 == render(_model(b2, "PLC_1"), INFO)  # order of the dump does not matter
    assert "connections.json" in files1
    assert validate_files({k: v.encode("utf-8") for k, v in files1.items()}) == []


def test_address_lengths_are_bits() -> None:
    """Openness gives I/O address lengths in bits; a
    16-byte module at I10 has length 128 and covers I10..I25, a 2-bit module one byte."""
    from plcexport.extractors.tia.mapping import _address_range

    assert _address_range({"io": "input", "start": 10, "length": 128}) == "%I10.0-%I25.7"
    assert _address_range({"io": "output", "start": 4, "length": 32}) == "%Q4.0-%Q7.7"
    assert _address_range({"io": "input", "start": 2, "length": 16}) == "%I2.0-%I3.7"
    assert _address_range({"io": "input", "start": 5, "length": 2}) == "%I5.0-%I5.7"


def test_calls_are_linked_with_findings_on_the_reference_sample() -> None:
    """Connections of the recorded sample."""
    b = _bundle("conn_v21")
    p1, p2 = _model(b, "PLC_1"), _model(b, "PLC_2")
    ref = "S7-1500/ET200MP-Station_1/PLC_1/"
    assert [(u.block, u.network_no, u.connection, u.findings) for u in p1.connections.uses] == [
        ("BSEND", 1, ref + "0x0100", ()),
        ("BRCV", 2, ref + "0x0101", ()),
    ]
    assert [(f.code, f.connection) for f in p1.connections.findings if f.connection] == [
        ("connection_unused", ref + "0x0102")
    ]
    # the couplers PLC_1 controls, the X2 sides without controller, Coupler_1's area
    assert [k.ref for k in p1.connections.couplers] == [
        "GSD-Geraet_1/Slave_1", "PNPN Coupler/PNPN Coupler.X1", "PNPN Coupler_1/PNPN Coupler_1.X1",
    ]  # fmt: skip
    assert sorted(f.code for f in p1.connections.findings if not f.connection) == [
        "coupler_side_without_controller", "coupler_side_without_controller",
        "transfer_area_length_mismatch",
    ]  # fmt: skip
    # FOB_RTG1 is know-how protected: a call in it cannot be read
    cov = p1.coverage.categories["connections"]
    assert cov.state == "partial" and "protected" in (cov.reason or "")
    assert ("connections", "FOB_RTG1", "protected") in {
        (g.category, g.item, g.reason) for g in p1.coverage.gaps
    }
    assert [f.code for f in p2.connections.findings] == ["connection_unused"]


def test_two_sends_with_one_r_id_are_reported(tmp_path: Path) -> None:
    """Call linking on the sample's program with a second BSEND of the same connection and R_ID."""
    import shutil

    src = TIADUMP / "conn_v21"
    shutil.copytree(src, tmp_path / "d")
    main = tmp_path / "d" / "sd" / "PLC_1" / "Programmbausteine" / "Main.s7dcl"
    text = main.read_bytes().decode("utf-8")
    first = text.index('"BSEND_DB".BSEND(')
    end = text.index(")", first) + 1
    main.write_bytes(text.replace("END_ORGANIZATION_BLOCK", text[first:end].replace(
        '"BSEND_DB"', '"BSEND_DB_2"') + "\r\nEND_ORGANIZATION_BLOCK").encode("utf-8"))  # fmt: skip
    dump = json.loads((tmp_path / "d" / "dump.json").read_text(encoding="utf-8"))
    m = _model(to_bundle(dump, tmp_path / "d", OPTS), "PLC_1")
    sends = [u for u in m.connections.uses if u.block == "BSEND"]
    assert len(sends) == 2
    assert all([f.code for f in u.findings] == ["duplicate_r_id"] for u in sends)
