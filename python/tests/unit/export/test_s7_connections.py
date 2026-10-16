"""s7dump ``connections`` → export connections, one test per rule of data-model §2."""

from __future__ import annotations

from plcexport.codec import model_from_json, model_to_json
from plcexport.extractors.s7classic.connections import tsap
from plcexport.extractors.s7classic.mapping import MappingOptions, to_model
from plcexport.format.validate import validate_model
from plcexport.model import (
    CONNECTIONS,
    CallValue,
    Connection,
    ConnectionUse,
    ExportModel,
)
from tests.contract.export.s7helpers import load_dump

OPTS = MappingOptions("s7classic-direct", "1.0.0", text_language="de")
CPU = "SIMATIC 300(1)/CPU 315-2 PN/DP"


def model(name: str = "connections") -> ExportModel:
    m = to_model(load_dump(name), OPTS)
    assert validate_model(m) == []
    return m


def by_id(m: ExportModel) -> dict[str, Connection]:
    return {c.local.id: c for c in m.connections.connections}


def test_tsap_from_resource_rack_and_slot() -> None:
    assert tsap(17, 0, 2) == "11.02"
    assert tsap(3, 0, 0) == "03.00"  # NetPro prints 3.00
    assert tsap(16, 1, 3) == "10.23"  # rack in the upper three bits
    assert tsap(None, 0, 2) is None and tsap(16, 0, None) is None


def test_refs_ids_and_local_end() -> None:
    c = by_id(model())["0x0010"]  # stored as 16, shown as 10 in NetPro
    assert c.ref == f"{CPU}/0x0010" and c.name == "S7-Verbindung 2" and c.kind == "s7"
    assert (c.local.module, c.local.interface, c.local.address) == (
        "SIMATIC 300(1)/0.2",
        f"{CPU}/ethernet",
        "192.168.0.10",
    )


def test_both_sources_equal() -> None:
    c = by_id(model())["0x0001"]
    assert (c.local.tsap, c.partner.tsap, c.active, c.one_way) == ("10.02", "10.02", True, True)
    p = c.partner
    assert (p.specified, p.name, p.address, p.rack, p.slot) == (
        False,
        "HomePLC2",
        "10.101.10.20",
        0,
        2,
    )
    assert c.sources == {"tsaps": "both", "partner_address": "both", "active": "both"}
    assert c.differences == ()


def test_difference_between_tables_and_compiled_data_is_kept_and_reported() -> None:
    m = model()
    c = by_id(m)["0x0010"]
    assert c.partner.tsap == "10.04"  # the compiled value
    (d,) = c.differences
    assert (d.field, d.tables, d.compiled) == ("partner_tsap", "10.03", "10.04")
    assert ("tables_compiled_differ", c.ref) in {
        (f.code, f.connection) for f in m.connections.findings
    }


def test_partner_inside_the_project() -> None:
    c = by_id(model())["0x0002"]
    assert c.partner.specified is True
    assert (c.partner.name, c.partner.module, c.partner.address) == (
        "CP 343-1",
        "SIMATIC 300(1)/0.4",
        "10.1.2.20",
    )
    assert c.partner.tsap == "03.04" and c.sources["tsaps"] == "compiled"


def test_other_connection_type_is_listed_only() -> None:
    c = by_id(model())["0x0003"]
    assert (c.kind, c.type_id, c.details) == ("other", 1332999, "not_read")
    assert c.local.tsap is None and c.partner.address is None and c.active is None


def test_without_compiled_record_the_tables_give_the_tsaps() -> None:
    c = by_id(model())["0x0004"]
    assert (c.local.tsap, c.partner.tsap) == ("14.02", "03.00")
    assert c.sources == {"tsaps": "tables", "partner_address": "tables", "active": "tables"}


def test_list_without_owner_keeps_its_connection() -> None:
    m = model()
    c = by_id(m)["0x0005"]
    assert c.ref == "list 2/0x0005" and c.local.module is None and c.local.tsap is None
    assert c.partner.tsap == "10.02" and c.sources["tsaps"] == "tables"
    assert any(w.code == "connection_without_owner" for w in m.warnings)


def test_one_way_flag_is_exported_as_found_and_drives_nothing() -> None:
    dump = load_dump("connections")
    for c in dump["connections"]:
        c["one_way"] = False
    changed = to_model(dump, OPTS)
    assert all(c.one_way is False for c in changed.connections.connections if c.kind == "s7")
    assert changed.connections.findings == model().connections.findings


def test_coverage_states() -> None:
    assert model().coverage.categories[CONNECTIONS].state == "partial"
    reason = model().coverage.categories[CONNECTIONS].reason or ""
    assert "1 connection(s) listed only (type not read)" in reason
    assert "compiled connection data missing; TSAPs from the tables" in reason

    dump = load_dump("connections")
    dump["connections"] = dump["connections"][:1]
    prog = dump["programs"][0]  # without the calls and the protected caller
    prog["blocks"] = [
        b for b in prog["blocks"] if b["symbolic_name"] not in ("FB_Comm", "FB_Secret")
    ]
    assert to_model(dump, OPTS).coverage.categories[CONNECTIONS].state == "delivered"

    dump["connections"] = []  # the project has no connection
    cov = to_model(dump, OPTS).coverage.categories[CONNECTIONS]
    assert (cov.state, cov.reason) == ("unavailable", "not_in_project")

    # a dump of an older s7dump: no connection data, so the category is absent (not checked)
    old = model("press_s7300")
    assert CONNECTIONS not in old.coverage.categories and old.connections.item_count() == 0


# ------------------------------------------------------------------ calls
def uses(m: ExportModel) -> dict[int, ConnectionUse]:
    return {u.network_no or 0: u for u in m.connections.uses}


def test_call_is_linked_to_the_connection_its_id_names() -> None:
    m = model()
    get = uses(m)[1]
    assert (get.unit, get.block, get.called) == ("FB_Comm", "GET", "SFB 14 #Read")
    assert get.id == CallValue("0x0001") and get.r_id is None
    assert get.connection == f"{CPU}/0x0001" and get.findings == ()
    recv = uses(m)[3]  # the in-project connection
    assert (recv.block, recv.connection) == ("BRCV", f"{CPU}/0x0002")
    assert recv.r_id == CallValue("0x00000001")


def test_data_areas_name_the_members_they_cover() -> None:
    remote, local = uses(model())[1].areas
    assert (remote.param, remote.role, remote.pointer) == ("ADDR_1", "remote", "P#DB1.DBX0.0 INT 1")
    assert remote.db is None and remote.members == ()  # an area in the partner PLC
    assert (local.param, local.role, local.pointer) == ("RD_1", "receive", "P#DB20.DBX2.0 REAL 2")
    assert (local.db, local.start, local.length_bytes) == ("DB_Recipe", "2.0", 8)
    assert local.members == (
        '"DB_Recipe".Limits',
        '"DB_Recipe".Limits.Max',
        '"DB_Recipe".Limits.Min',
    )
    (send,) = uses(model())[2].areas
    assert send.members == ('"DB_Recipe".Setpoint',)
    (unassigned,) = uses(model())[3].areas
    assert unassigned.unassigned and unassigned.pointer is None


def test_values_stay_as_written_and_the_swap_is_only_a_hint() -> None:
    """ID AAAA and R_ID 10 are exported as the program has them; the call is
    not linked, and the hint names the connection whose ID the R_ID is."""
    send = uses(model())[2]
    assert send.id == CallValue("0xAAAA") and send.r_id == CallValue("0x00000010")
    assert send.len == CallValue(unresolved="MW 10")  # set at run time
    assert send.connection is None
    assert [(f.code, f.connection) for f in send.findings] == [
        ("id_not_configured", None),
        ("id_r_id_maybe_swapped", f"{CPU}/0x0010"),
    ]


def test_no_swap_hint_when_the_r_id_is_no_local_id() -> None:
    dump = load_dump("connections")
    comm = next(b for b in dump["programs"][0]["blocks"] if b["symbolic_name"] == "FB_Comm")
    raw = comm["networks"][1]["raw_stl"]
    raw[raw.index("      L     L#16")] = "      L     L#99"
    send = uses(to_model(dump, OPTS))[2]
    assert [f.code for f in send.findings] == ["id_not_configured"]


def test_unused_connections_are_reported_but_not_listed_only_ones() -> None:
    unused = {f.connection for f in model().connections.findings if f.code == "connection_unused"}
    assert unused == {f"{CPU}/0x0004", f"{CPU}/0x0010"}  # 0x0003 is kind other, 0x0005 has no owner


def test_protected_caller_is_reported() -> None:
    """FB_Secret may call a communication block; that cannot be read."""
    m = model()
    assert ("connections", "FB_Secret", "protected") in {
        (g.category, g.item, g.reason) for g in m.coverage.gaps
    }
    assert "calls in 1 protected block(s) not readable" in (
        m.coverage.categories[CONNECTIONS].reason or ""
    )
    # the protected communication blocks themselves are no callers
    assert not [g for g in m.coverage.gaps if g.category == "connections" and g.item == "BSEND"]


def test_safety_caller_marks_use_and_connection() -> None:
    """a call in an F-block is safety content; a connection used only by such calls too."""
    dump = load_dump("connections")
    for b in dump["programs"][0]["blocks"]:
        b["f_block"] = b["symbolic_name"] == "FB_Comm"
        b["header_attribute"], b["checksum"] = (64, 1234) if b["f_block"] else (0, None)
    m = to_model(dump, OPTS)
    assert all(u.safety for u in m.connections.uses)
    assert by_id(m)["0x0001"].safety is True and by_id(m)["0x0004"].safety is False


def test_user_block_with_a_communication_block_number_triggers_nothing() -> None:
    """Seen in the OSCAT libraries: their own FB 12 and protected blocks, no communication."""
    dump = load_dump("connections")
    prog = dump["programs"][0]
    prog["blocks"] = [
        b for b in prog["blocks"] if b["symbolic_name"] not in ("FB_Comm", "BSEND", "BRCV", "GET")
    ]
    own = next(b for b in prog["blocks"] if b["symbolic_name"] == "FB_Valve")
    prog["blocks"].append({**own, "number": 12, "symbolic_name": "FB_Own12"})
    m = to_model(dump, OPTS)
    assert not [g for g in m.coverage.gaps if g.category == CONNECTIONS]
    assert m.connections.uses == ()


def test_model_survives_the_codec_between_export_processes() -> None:
    """The extractor runs in a child process; its model crosses as JSON, gaps included."""
    m = model()
    back = model_from_json(model_to_json(m))
    assert back.connections == m.connections
    assert back.coverage == m.coverage
