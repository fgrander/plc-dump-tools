"""s7dump → ExportModel mapping, one test per rule of data-model §2–4."""

from __future__ import annotations

import pytest

from plcexport.extractors.s7classic.direct import plausibility
from plcexport.extractors.s7classic.mapping import (
    COLLECTIVE_SIGNATURE,
    HARDWARE_REASON,
    SAFETY_REASON_NO_SIGNATURE,
    MappingOptions,
    readable_labels,
    to_model,
)
from plcexport.format.validate import validate_model
from plcexport.model import ExportModel
from tests.contract.export.s7helpers import load_dump

OPTS = MappingOptions("s7classic-direct", "1.0.0", text_language="de")


def model(name: str = "press_s7300") -> ExportModel:
    m = to_model(load_dump(name), OPTS)
    assert validate_model(m) == []
    return m


def unit(m: ExportModel, name: str):  # type: ignore[no-untyped-def]
    return next(u for u in m.units if u.name == name)


def test_blocks_are_named_by_symbol_with_address_attribute() -> None:
    fb = unit(model(), "FB_Heating")
    assert fb.kind == "FB" and fb.number == 10
    assert fb.attributes["address"] == "FB 10"
    assert fb.attributes["family"] == "HEAT" and fb.attributes["author"] == "Max Mustermann"
    vat = unit(model(), "VAT1")  # no symbol: absolute name
    assert vat.kind == "OTHER" and vat.attributes["type"] == "VAT"


def test_original_language_and_stl_body() -> None:
    m = model()
    assert unit(m, "Main").language == "LAD"  # KOP
    assert unit(m, "FB_Heating").language == "FBD"  # FUP
    assert unit(m, "FC_Scale").language == "STL"  # AWL
    assert m.unit_bodies["Main"].language == "stl"
    assert m.unit_bodies["Main"].networks[0].title == {"de": "Pumpe Start/Stopp"}


def test_interface_sections_scopes_and_start_values() -> None:
    m = model()
    v = {x.symbolic_path: x for x in m.variables if x.declared_in == "FB_Heating"}
    assert v['"FB_Heating".TempLimit'].section == "STATIC"
    assert v['"FB_Heating".TempLimit'].start_value == "2.500000e+002"
    assert v['"FB_Heating".TempLimit'].comments == {"de": "Maximale Plattentemperatur"}
    assert v['"FB_Heating".TempActual'].scope == "fb_interface"
    assert {x.section for x in m.variables if x.declared_in == "FC_Scale"} == {"IN", "RETURN"}
    db = {x.symbolic_path: x for x in m.variables if x.declared_in == "DB_Recipe"}
    assert db['"DB_Recipe".Limits.Max'].parent_path == '"DB_Recipe".Limits'
    assert db['"DB_Recipe".Counter'].scope == "db_member"
    assert unit(m, "UDT_Limits").variable_scope == "udt_member"


def test_instance_db_and_system_blocks() -> None:
    m = model()
    idb = unit(m, "DB_Heating")
    assert idb.kind == "IDB" and idb.instance_of == "FB_Heating"
    ton = unit(m, "TON")
    assert ton.kind == "OTHER" and ton.attributes == {"address": "SFB 4", "type": "SFB",
                                                     "system": "true"}  # fmt: skip


def test_sources_are_units_and_linked_to_blocks() -> None:
    m = model()
    src = unit(m, "FB_Valve.scl")
    assert src.kind == "OTHER" and src.language == "SCL"
    assert m.unit_bodies["FB_Valve.scl"].language == "scl"
    assert "FUNCTION_BLOCK FB 11" in (m.unit_bodies["FB_Valve.scl"].code or "")
    assert unit(m, "FB_Valve").attributes["generated_from"] == "FB_Valve.scl"


def test_symbols_are_global_tags_with_io_direction() -> None:
    m = model()
    tags = {v.symbolic_path: v for v in m.variables if v.scope == "global_tag"}
    assert tags['"I_Start"'].io_direction == "input" and tags['"I_Start"'].address == "I 0.0"
    assert tags['"I_TempPlate"'].io_direction == "input"  # PIW
    assert tags['"Q_Pump"'].io_direction == "output"
    assert tags['"M_Run"'].io_direction == "memory"
    assert '"FB_Heating"' not in tags  # block symbols name blocks, they are not tags
    assert tags['"I_Stop"'].comments == {"de": "Stopp Taster (Öffner)"}


def test_xrefs_from_stl() -> None:
    m = model()
    got = {(x.from_unit, x.target_text, x.access, x.network_no, x.via_param) for x in m.xrefs}
    assert ("Main", '"I_Start"', "read", 1, None) in got
    assert ("Main", '"Q_Pump"', "write", 1, None) in got
    assert ("Main", "FB_Heating", "call", 2, None) in got
    assert ("Main", '"I_TempPlate"', "read", 2, "TempActual") in got
    assert ("Main", '"Q_Heater_On"', "write", 2, "HeaterOn") in got
    # CALL #Valve (multi-instance) is listed as a call of its FB type
    assert ("FB_Heating", "FB_Valve", "call", 2, None) in got
    assert ("FC_Scale", "DB_Recipe", "read", 2, None) in got  # OPN DB 20 → unit
    assert ("FC_Scale", "T 5", "write", 2, None) in got
    # no block-local (#HeaterOn passed to Open), stack or register-indirect targets
    assert ("FB_Heating", "#HeaterOn", "read", 2, "Open") not in got
    assert ("FC_Scale", "IW [AR1,P#0.0]", "indirect", 2, None) not in got
    assert not [t for (_, t, *_rest) in got if t.startswith("#") or t.startswith("L")]


def test_coverage_rules() -> None:
    cats = model().coverage.categories
    assert cats["hardware"].state == "partial" and cats["hardware"].reason == HARDWARE_REASON
    assert cats["hmi"].state == "unavailable" and cats["hmi"].reason == "unsupported"
    assert cats["program_units"].state == "delivered"
    assert cats["datatypes"].state == "delivered"


def test_pcs7_charts_are_listed_as_gaps() -> None:
    gaps = [(g.item, g.reason) for g in model("pcs7").coverage.gaps]
    assert ("CFC Plant/Unit1/Mixer1", "not_exported_cfc_sfc") in gaps
    assert ("SFC Plant/Unit2/Batch", "not_exported_cfc_sfc") in gaps


def test_protected_block_has_interface_but_no_body() -> None:
    m = model("protected")
    assert unit(m, "FB_Heating").protected
    assert "FB_Heating" not in m.unit_bodies
    assert any(v.declared_in == "FB_Heating" for v in m.variables)
    assert ("FB_Heating", "protected") in [(g.item, g.reason) for g in m.coverage.gaps]


def test_two_programs_prefix_units_and_symbols() -> None:
    m = model("two_programs")
    names = {u.name for u in m.units}
    assert {"S7 Program(1)/Main", "S7 Program(2)/Main"} <= names
    tags = {v.symbolic_path for v in m.variables if v.scope == "global_tag"}
    assert {'"S7 Program(1)/I_Start"', '"S7 Program(2)/I_Start"'} <= tags
    assert any(x.from_unit == "S7 Program(2)/Main" and x.target_text == '"S7 Program(2)/I_Start"'
               for x in m.xrefs)  # fmt: skip
    assert {f.path for f in m.structure.folders} == {"S7 Program(1)", "S7 Program(2)"}


def test_platform_part_and_project() -> None:
    m = model("library")
    assert m.platform["library"] is True and m.platform["mnemonic"] == "en"
    assert m.project.platform_id == "siemens-step7-classic"
    assert m.project.controller == "CPU 315-2 PN/DP"
    assert m.project.languages == ("de",)
    assert m.hardware.networks[0].address == "192.168.0.10"


def test_f_blocks_are_safety_units_with_their_checksums() -> None:
    """F-blocks (header flag) are exported as found and marked as safety."""
    m = model("safety")
    assert {u.name for u in m.units if u.safety} == {"F_EStop", "F_DB_EStop", "F_GLOBDB"}
    assert m.safety.units == ("F_DB_EStop", "F_EStop", "F_GLOBDB")
    assert [(g.scope, g.value, g.kind) for g in m.safety.signatures] == [
        ("F_DB_EStop", "4711", "mc7_checksum"),
        ("F_EStop", "23100", "mc7_checksum"),
        ("F_GLOBDB", "10574", "mc7_checksum"),
        # the actual value wins over the start value DW#16#0
        ("F_GLOBDB.F_PROG_SIG", "DW#16#626E0828", COLLECTIVE_SIGNATURE),
    ]
    assert m.unit_bodies["F_EStop"].networks[0].code.startswith("U     #ESTOP")  # body as found
    assert m.coverage.categories["safety"].state == "delivered"


def test_f_blocks_without_collective_signature_are_partial() -> None:
    dump = load_dump("safety")
    glob = next(b for b in dump["programs"][0]["blocks"] if b["symbolic_name"] == "F_GLOBDB")
    glob["interface"][1]["actual"] = None  # start value DW#16#0 only: no signature
    m = to_model(dump, OPTS)
    assert COLLECTIVE_SIGNATURE not in {g.kind for g in m.safety.signatures}
    cov = m.coverage.categories["safety"]
    assert (cov.state, cov.reason) == ("partial", SAFETY_REASON_NO_SIGNATURE)
    # the V5.3 example keeps the signature in the start value
    glob["interface"][1]["start"] = "DW#16#336783DF"
    sig = [g for g in to_model(dump, OPTS).safety.signatures if g.kind == COLLECTIVE_SIGNATURE]
    assert [g.value for g in sig] == ["DW#16#336783DF"]


def test_safety_coverage_without_f_blocks() -> None:
    dump = load_dump("safety")
    blocks = dump["programs"][0]["blocks"]
    dump["programs"][0]["blocks"] = [b for b in blocks if not b["f_block"]]
    dump["programs"][0]["catalog"]["blocks"] -= 3
    m = to_model(dump, OPTS)
    assert m.safety.units == () and not any(u.safety for u in m.units)
    assert m.coverage.categories["safety"].state == "unavailable"
    assert m.coverage.categories["safety"].reason == "not_in_project"
    # a flag that s7dump could not determine (block table unreadable) leaves the answer open
    fc = next(b for b in dump["programs"][0]["blocks"] if b["symbolic_name"] == "FC_Scale")
    fc["f_block"] = None
    reason = to_model(dump, OPTS).coverage.categories["safety"].reason
    assert reason == (
        "other:no F-blocks found, but 1 block(s) could not be checked for the F-block flag"
    )


def test_dump_without_f_block_flag_says_detection_did_not_run() -> None:
    cov = model("press_s7300").coverage.categories["safety"]  # older s7dump
    assert (cov.state, cov.reason) == (
        "unavailable",
        "other:safety program detection is not built yet",
    )


def test_a_source_that_is_not_text_is_corrupt_not_fatal() -> None:
    """Seen in Siemens example AS-FE-I-006 V1.0: a "source" whose file is 12 binary bytes."""
    dump = load_dump("press_s7300")
    src = dump["programs"][0]["sources"][0]
    src["text"] = "��\x16\x04�\x00J\x11?\x92A"
    m = to_model(dump, OPTS)
    assert validate_model(m) == []
    name = f"{src['name']}.{src['kind']}"
    assert name not in m.unit_bodies and any(u.name == name for u in m.units)
    assert ("program_units", name, "corrupt") in [
        (g.category, g.item, g.reason) for g in m.coverage.gaps
    ]
    assert m.coverage.categories["program_units"].state == "partial"
    assert [w.code for w in m.warnings if w.unit == name] == ["source_not_text"]


def test_ethernet_interfaces_and_unknown_modules() -> None:
    """IP addresses come from the project's network table for every CPU, CP and PROFINET IO
    device; a CP the library does not know becomes a module, a drive gets its own device "rack"."""
    hw = model("ethernet").hardware
    modules = {(m.ref, m.type, m.rack, m.slot) for m in hw.modules}
    assert ("SIMATIC 300(1)/0.4", "CP 343-1", "SIMATIC 300(1)/R0", 4) in modules
    assert (
        "SIMATIC 300(1)/PROFINET-IO-System #1.1",
        "AKD-PN",
        "SIMATIC 300(1)/PROFINET-IO-System #1",
        1,
    ) in modules
    assert len([m for m in hw.modules if m.rack == "SIMATIC 300(1)/R0" and m.slot == 2]) == 1
    assert {(n.ref, n.address) for n in hw.networks if n.interface == "ethernet"} == {
        ("SIMATIC 300(1)/CPU 315-2 PN/DP/ethernet", "192.168.0.10/24"),
        ("SIMATIC 300(1)/CP 343-1/ethernet", "10.1.2.20/16"),
        ("SIMATIC 300(1)/AKD-PN #1/ethernet", "192.168.0.11/24"),
    }


def test_repeated_program_names_are_qualified_by_station() -> None:
    """Every station of a multi-station project may call its program "S7-Programm(1)"."""
    dump = load_dump("two_programs")
    for prog, station in zip(dump["programs"], ("Station A", "Station B"), strict=True):
        prog["name"], prog["station"] = "S7-Programm(1)", station
    m = to_model(dump, OPTS)
    assert validate_model(m) == []
    assert sorted(f.path for f in m.structure.folders) == [
        "Station A/S7-Programm(1)",
        "Station B/S7-Programm(1)",
    ]
    assert "Station B/S7-Programm(1)/Main" in {u.name for u in m.units}


def test_every_module_with_address_ranges_and_io_channels() -> None:
    """all modules of the hardware tables; each I/O symbol is linked to its module."""
    hw = model("modules").hardware
    by_ref = {m.ref: m for m in hw.modules}
    di = by_ref["SIMATIC 300(1)/0.4"]
    assert (di.type, di.order_no, di.address_ranges) == (
        "DI16xDC24V",
        "6ES7 321-1BH02-0AA0",
        ("%I0.0-%I1.7",),
    )
    assert by_ref["SIMATIC 300(1)/0.5"].order_no is None  # shortened catalog key: not guessed
    assert by_ref["SIMATIC 300(1)/0.2"].order_no == "6ES7 315-2EH14-0AB0"  # library's CPU entry
    assert by_ref["SIMATIC 300(1)/0.2"].firmware == "V3.2"
    drive = by_ref["SIMATIC 300(1)/PROFINET-IO-System #1.2"]
    assert drive.address_ranges == ("%I300.0-%I309.7", "%Q300.0-%Q323.7")
    assert "AKD-PN (device 1 on PROFINET-IO-System)" in {r.name for r in hw.racks}
    # the CP 343-1 of the library list has no hardware-table module: it is kept
    assert by_ref["SIMATIC 300(1)/0.7"].type == "CP 343-1"
    # a library CP without station is the hardware-table module of the same name and slot
    assert by_ref["SIMATIC 300(1)/0.8"].order_no == "6GK7 443-1EX40-0XE0"
    assert not [m.ref for m in hw.modules if m.ref.startswith("-/")]
    assert "-/R0" not in {r.ref for r in hw.racks}
    links = {(c.symbol, c.module_ref) for c in hw.channels}
    assert links == {
        ('"I_Start"', "SIMATIC 300(1)/0.4"),
        ('"I_Stop"', "SIMATIC 300(1)/0.4"),
        ('"Q_Pump"', "SIMATIC 300(1)/0.5"),
        ('"Q_Heater_On"', "SIMATIC 300(1)/0.5"),
        ('"I_TempPlate"', "SIMATIC 300(1)/0.6"),
    }  # M_Run (memory) is not I/O


def test_io_symbol_reaching_into_the_next_module_is_linked_by_its_first_byte() -> None:
    """A word that starts in a module's range and ends behind it belongs to that module (seen:
    ``QD 342`` over two modules of one DP slave); a symbol that starts behind it does not."""
    dump = load_dump("modules")
    symbols = dump["programs"][0]["symbols"]
    symbols.append({"symbol": "Q_Wide", "address": "QW 5", "type": "WORD", "comment": None})
    symbols.append({"symbol": "Q_Behind", "address": "QB 6", "type": "BYTE", "comment": None})
    links = {c.symbol: c.module_ref for c in to_model(dump, OPTS).hardware.channels}
    assert links['"Q_Wide"'] == "SIMATIC 300(1)/0.5"  # DO16 has Q4.0-Q5.7
    assert '"Q_Behind"' not in links


def test_data_block_members_carry_the_library_offsets() -> None:
    """global and instance DB members get the dump's ``byte.bit`` offset,
    interface members of code blocks none."""
    m = model()
    off = {x.symbolic_path: x.offset for x in m.variables if x.scope == "db_member"}
    assert off['"DB_Recipe".Counter'] == "0.0"
    assert off['"DB_Recipe".Limits'] == "2.0" and off['"DB_Recipe".Limits.Min'] == "6.0"
    assert off['"DB_Recipe".Setpoint'] == "10.0"
    idb = {x.symbolic_path: x for x in m.variables if x.declared_in == "DB_Heating"}
    assert idb['"DB_Heating".HeaterOn'].offset == "4.0"
    assert idb['"DB_Heating".HeaterOn'].section == "OUT"
    assert idb['"DB_Heating".TempLimit'].section == "STATIC"
    assert idb['"DB_Heating".Valve'].offset == "10.0"
    assert all(x.offset is None for x in m.variables if x.declared_in == "FB_Heating")


def test_db_without_readable_actual_values_is_exported_with_a_warning() -> None:
    """s7dump reads a DB again without actual values when the library runs past their end
    (seen on instance DBs of library blocks). The DB is exported; the warning says what is
    missing, and the project does not need the fallback route for it."""
    dump = load_dump("press_s7300")
    recipe = next(b for p in dump["programs"] for b in p["blocks"] if b["number"] == 20)
    recipe["actual_values_read"] = False
    assert plausibility(dump, set()) == []
    m = to_model(dump, OPTS)
    assert [w.unit for w in m.warnings if w.code == "db_actual_values_unread"] == ["DB_Recipe"]
    assert any(x.declared_in == "DB_Recipe" for x in m.variables)


def test_db_whose_library_layout_misses_the_block_size_has_no_offsets() -> None:
    """arrays of odd-length strings, which the library lays out without fill bytes: the
    layout does not end at the block's data size, so that DB keeps no offsets and says why."""
    dump = load_dump("press_s7300")
    recipe = next(b for p in dump["programs"] for b in p["blocks"] if b["number"] == 20)
    recipe["mc7_size"] = 18
    m = to_model(dump, OPTS)
    assert all(x.offset is None for x in m.variables if x.declared_in == "DB_Recipe")
    assert any(x.offset for x in m.variables if x.declared_in == "DB_Heating")
    assert [w.unit for w in m.warnings if w.code == "db_layout_mismatch"] == ["DB_Recipe"]


def test_members_behind_a_compound_in_out_parameter_have_no_offset() -> None:
    """an IN_OUT struct/array is a 6-byte pointer in the instance DB; the parameter has its
    offset, the members it points to are not in the DB and get none."""
    dump = load_dump("press_s7300")
    idb = next(b for p in dump["programs"] for b in p["blocks"] if b["number"] == 30)
    idb["interface"].append(
        {
            "name": "Recipe",
            "section": "IN_OUT",
            "type": "STRUCT",
            "start": None,
            "comment": None,
            "offset": "14.0",
            "length": 6,
            "members": [
                {
                    "name": "Speed",
                    "section": None,
                    "type": "INT",
                    "start": None,
                    "comment": None,
                    "offset": "0.0",
                    "length": 2,
                    "members": [],
                }
            ],
        }
    )
    idb["mc7_size"] = 20
    v = {
        x.symbolic_path: x for x in to_model(dump, OPTS).variables if x.declared_in == "DB_Heating"
    }
    assert v['"DB_Heating".Recipe'].offset == "14.0"
    assert v['"DB_Heating".Recipe.Speed'].offset is None
    assert v['"DB_Heating".HeaterOn'].offset == "4.0"


def test_line_breaks_in_comments_do_not_depend_on_the_platform() -> None:
    """The library joins comment lines with the platform's line break (CRLF on Windows, LF in
    the Linux exporter): both dumps must give the same model."""
    windows, linux = load_dump("press_s7300"), load_dump("press_s7300")
    for d, nl in ((windows, "\r\n"), (linux, "\n")):
        block = d["programs"][0]["blocks"][0]
        block["description"] = f"Zeile 1{nl}Zeile 2"
        block["networks"][0]["comment"] = f"a{nl}b{nl}"
        block["networks"][0]["title"] = "Titel"
        d["programs"][0]["symbols"][5]["comment"] = f"x{nl}y"
    a, b = to_model(windows, OPTS), to_model(linux, OPTS)
    assert a == b
    assert "\r" not in repr(a)
    assert next(t.text for t in a.texts if t.kind == "comment" and t.unit == "Main") == (
        "Zeile 1\nZeile 2"
    )


def test_unreadable_jump_labels_get_generated_names() -> None:
    """Real case (INSEVIS examples): the library returns arbitrary bytes, also control
    characters, for the labels of a block. The export was rejected as invalid."""
    nets = [
        ["      L     5", "      ==I", "      SPB   \x03", "// SPB   \x03 stays in a comment"],
        [
            "\x03   : L     DB114.DBB3",
            "      SPB   \x02\u00d0n3",
            "      SPA   M001",
            "M001: NOP   0",
        ],
        ["\x02\u00d0n3: NOP   0", '      L     "x"'],
    ]
    fixed, count = readable_labels(nets)
    assert count == 2
    assert fixed == [
        ["      L     5", "      ==I", "      SPB   M002", "// SPB   \x03 stays in a comment"],
        ["M002: L     DB114.DBB3", "      SPB   M003", "      SPA   M001", "M001: NOP   0"],
        ["M003: NOP   0", '      L     "x"'],
    ]
    assert readable_labels([["M001: NOP 0", "      SPA   M001"]]) == (
        [["M001: NOP 0", "      SPA   M001"]],
        0,
    )


def test_block_with_unreadable_labels_is_exported_with_a_warning() -> None:
    dump = load_dump("press_s7300")
    fc = next(b for b in dump["programs"][0]["blocks"] if b["symbolic_name"] == "FC_Scale")
    fc["networks"][0]["stl"] = ["      SPA   \x0e", "\x0e   : NOP   0"]
    m = to_model(dump, OPTS)
    assert validate_model(m) == []
    assert [w.unit for w in m.warnings if w.code == "stl_label_unreadable"] == ["FC_Scale"]
    assert m.unit_bodies["FC_Scale"].networks[0].code == "      SPA   M001\nM001: NOP   0"


def test_symbol_table_rows_without_a_name_are_left_out() -> None:
    """Real case (plcs.net "Dust system": 38 of 192 rows): STEP 7 keeps rows that have an
    address but no symbol name. Each became a variable with an empty name; the export was
    rejected for the duplicates."""
    dump = load_dump("press_s7300")
    symbols = dump["programs"][0]["symbols"]
    before = len(to_model(load_dump("press_s7300"), OPTS).variables)
    symbols += [
        {"symbol": "", "address": "E       2.6", "type": "BOOL", "comment": None},
        {"symbol": "", "address": "E       2.7", "type": "BOOL", "comment": "spare"},
    ]
    dump["programs"][0]["catalog"]["symbols"] = len(symbols)
    assert plausibility(dump, set()) == []
    m = to_model(dump, OPTS)
    assert validate_model(m) == []
    assert len(m.variables) == before
    assert [w.message for w in m.warnings if w.code == "symbol_without_name"] == [
        "Symbols: 2 symbol table row(s) have an address but no name and are left out "
        "(1 of them with a comment)"
    ]


# ----------------------------------------------------------------- 009: data type offsets
def _m(name: str, typ: str, offset: str | None, length: int, *members: dict) -> dict:
    """One interface member as s7dump writes it."""
    m = {"name": name, "section": None, "type": typ, "start": None, "comment": None,
         "members": list(members)}  # fmt: skip
    if offset is not None:
        m["offset"], m["length"] = offset, length
    return m


def _with_udt(*members: dict) -> dict:
    """The press fixture with the members of its data type ``UDT_Limits`` (UDT 1) replaced."""
    dump = load_dump("press_s7300")
    udt = next(b for b in dump["programs"][0]["blocks"] if b["type"] == "UDT")
    udt["interface"] = list(members)
    return dump


def _udt_vars(m: ExportModel) -> list:
    return [x for x in m.variables if x.declared_in == "UDT_Limits"]


def _udt_warnings(m: ExportModel) -> list:
    return [w for w in m.warnings if w.code == "udt_layout_mismatch"]


def test_data_type_members_carry_offsets_in_memory_order() -> None:
    """a data type gets the dump's offsets, counted from its start."""
    m = to_model(
        _with_udt(
            _m("Enable", "BOOL", "0.0", 1),
            _m("Mode", "BYTE", "1.0", 1),
            _m("Speed", "INT", "2.0", 2),
            _m("Position", "DINT", "4.0", 4),
        ),
        OPTS,
    )
    assert validate_model(m) == []
    assert {x.symbolic_path: x.offset for x in _udt_vars(m)} == {
        '"UDT_Limits".Enable': "0.0",
        '"UDT_Limits".Mode': "1.0",
        '"UDT_Limits".Speed': "2.0",
        '"UDT_Limits".Position': "4.0",
    }
    assert all(x.scope == "udt_member" for x in _udt_vars(m))
    assert _udt_warnings(m) == []


def test_nested_members_of_a_data_type_count_from_the_start_of_the_type() -> None:
    m = to_model(
        _with_udt(
            _m("Head", "INT", "0.0", 2),
            _m(
                "Limits",
                "STRUCT",
                "2.0",
                8,
                _m("Max", "REAL", "2.0", 4),
                _m("Min", "REAL", "6.0", 4),
            ),
        ),
        OPTS,
    )
    off = {x.symbolic_path: x.offset for x in _udt_vars(m)}
    assert off['"UDT_Limits".Limits.Max'] == "2.0" and off['"UDT_Limits".Limits.Min'] == "6.0"
    assert _udt_warnings(m) == []


def test_bits_of_a_data_type_share_a_byte() -> None:
    m = to_model(
        _with_udt(
            _m("A", "BOOL", "0.0", 1),
            _m("B", "BOOL", "0.1", 1),
            _m("C", "BOOL", "0.2", 1),
            _m("Word", "WORD", "2.0", 2),
        ),
        OPTS,
    )
    assert [x.offset for x in _udt_vars(m)] == ["0.0", "0.1", "0.2", "2.0"]
    assert _udt_warnings(m) == []


@pytest.mark.parametrize(
    ("members", "reason"),
    [
        ([_m("A", "INT", "2.0", 2), _m("B", "INT", "4.0", 2)], "first member"),
        ([_m("A", "INT", "0.0", 2), _m("B", "INT", "1.0", 2)], "B"),
        ([_m("A", "INT", "0.0", 2), _m("B", "INT", "0.0", 2)], "B"),
        ([_m("A", "INT", "0.0", 2), _m("B", "INT", None, 0)], "B"),
        (
            [_m("S", "STRUCT", "0.0", 4, _m("X", "INT", "0.0", 2), _m("Y", "INT", "4.0", 2))],
            "S.Y",
        ),
        (
            [_m("N", "INT", "0.0", 2), _m("T", "ARRAY [1..3] OF STRING[5]", "2.0", 21)],
            "odd-length strings",
        ),
        (
            [
                _m("N", "INT", "0.0", 2),
                _m("S", "STRUCT", "2.0", 22, _m("T", "array[0..1] of string [ 7 ]", "2.0", 18)),
            ],
            "odd-length strings",
        ),
    ],
)
def test_data_type_without_a_reliable_layout_has_no_offsets(members: list, reason: str) -> None:
    """no offsets, declaration order, one warning with the reason; never estimated."""
    m = to_model(_with_udt(*members), OPTS)
    assert validate_model(m) == []
    assert all(x.offset is None for x in _udt_vars(m))
    top = [x for x in _udt_vars(m) if x.parent_path is None]
    assert [x.position for x in top] == list(range(len(top)))
    assert [x.symbolic_path.rsplit(".", 1)[1] for x in sorted(top, key=lambda x: x.position)] == [
        mm["name"] for mm in members
    ]
    (w,) = _udt_warnings(m)
    assert w.unit == "UDT_Limits" and reason in w.message
    assert w.message.endswith("members exported without offsets")


def test_array_of_even_length_strings_keeps_the_offsets() -> None:
    m = to_model(
        _with_udt(_m("N", "INT", "0.0", 2), _m("T", "ARRAY [1..3] OF STRING[4]", "2.0", 18)), OPTS
    )
    assert [x.offset for x in _udt_vars(m)] == ["0.0", "2.0"]
    assert _udt_warnings(m) == []


def test_data_block_and_code_block_members_are_unchanged() -> None:
    """only data types change."""
    before = load_dump("press_s7300")
    for b in before["programs"][0]["blocks"]:
        if b["type"] == "UDT":
            for mm in b["interface"]:
                mm.pop("offset", None), mm.pop("length", None)
    old, new = to_model(before, OPTS), model()

    def others(m: ExportModel) -> list:
        return [
            (x.declared_in, x.symbolic_path, x.offset, x.section, x.data_type, x.start_value)
            for x in m.variables
            if x.scope != "udt_member"
        ]

    assert others(old) == others(new)
    assert [x.offset for x in _udt_vars(new)] == ["0.0", "4.0"]


def _db_using_the_type(children: tuple[str, str], fits: bool = True) -> dict:
    """The press fixture plus ``DB 40`` with a member ``Motor`` of ``UDT 1`` at 12.0."""
    dump = load_dump("press_s7300")
    blocks = dump["programs"][0]["blocks"]
    db = dict(next(b for b in blocks if b["number"] == 20 and b["type"] == "DB"))
    db.update(number=40, symbolic_name="DB_Line", mc7_size=20 if fits else 99)
    db["interface"] = [
        _m("Pad", "ARRAY [0..11] OF BYTE", "0.0", 12),
        _m(
            "Motor",
            "UDT 1",
            "12.0",
            8,
            _m("Max", "REAL", children[0], 4),
            _m("Min", "REAL", children[1], 4),
        ),
    ]
    blocks.append(db)
    dump["programs"][0]["catalog"]["blocks"] = len(blocks)
    return dump


def test_data_type_that_agrees_with_a_data_block_keeps_its_offsets() -> None:
    """member offset in the data block + offset in the type = the element."""
    m = to_model(_db_using_the_type(("12.0", "16.0")), OPTS)
    assert validate_model(m) == []
    assert [x.offset for x in _udt_vars(m)] == ["0.0", "4.0"]
    assert _udt_warnings(m) == []


def test_data_type_that_contradicts_a_data_block_has_no_offsets() -> None:
    m = to_model(_db_using_the_type(("12.0", "20.0")), OPTS)
    assert validate_model(m) == []
    assert all(x.offset is None for x in _udt_vars(m))
    assert [x.position for x in _udt_vars(m)] == [0, 1]
    (w,) = _udt_warnings(m)
    assert w.unit == "UDT_Limits" and "DB_Line" in w.message and "Motor.Min" in w.message


def test_a_data_block_with_an_unreliable_layout_is_no_witness() -> None:
    m = to_model(_db_using_the_type(("12.0", "20.0"), fits=False), OPTS)
    assert [x.offset for x in _udt_vars(m)] == ["0.0", "4.0"]
    assert _udt_warnings(m) == []


@pytest.mark.parametrize(
    ("members", "reliable"),
    [
        # real case (PN/ADP gateway sample): the library puts the BOOL at the odd byte
        ([_m("port", "STRING[5]", "0.0", 7), _m("reset", "BOOL", "7.0", 1)], False),
        ([_m("port", "STRING[5]", "0.0", 7), _m("reset", "BOOL", "8.0", 1)], True),
        ([_m("raw", "ARRAY [0..2] OF BYTE", "0.0", 3), _m("b", "BYTE", "3.0", 1)], False),
        ([_m("raw", "ARRAY [0..2] OF BYTE", "0.0", 3), _m("b", "BYTE", "4.0", 1)], True),
        ([_m("b", "BYTE", "0.0", 1), _m("text", "STRING[4]", "1.0", 6)], False),
        ([_m("b", "BYTE", "0.0", 1), _m("c", "BYTE", "1.0", 1)], True),
    ],
)
def test_member_after_a_string_or_array_starts_on_an_even_byte(
    members: list, reliable: bool
) -> None:
    """the library leaves out the fill byte after a string or array of odd length."""
    m = to_model(_with_udt(*members), OPTS)
    assert (_udt_warnings(m) == []) is reliable
    assert all((x.offset is not None) is reliable for x in _udt_vars(m))
    if not reliable:
        assert "even byte" in _udt_warnings(m)[0].message
