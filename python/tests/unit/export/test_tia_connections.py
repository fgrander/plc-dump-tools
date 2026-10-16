"""Dump entries of ``configured_connections`` -> ``Connection``.

Values are the owner-confirmed ones of the reference sample."""

from __future__ import annotations

from typing import Any

from plcexport.extractors.tia.connections import VALUE_NOT_AVAILABLE, map_connections
from plcexport.format.connections import check_doc, to_doc
from plcexport.model import ConnectionEnd, ConnectionPartner, ConnectionsModel

STATION = "S7-1500/ET200MP-Station_1"
PLC = "PLC_1"
MODULE = f"{STATION}/PLC_1"
NET = f"{STATION}/X2/Ethernet"


def entry(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "class": "S7Connection",
        "type": "S7Connection",
        "type_value": 0,
        "owner_item": "PLC_1",
        "local_name": "S7_Verbindung_1",
        "local_id": "100",
        "local_address": "192.168.1.1",
        "local_interface": "X2",
        "local_node_type": "Ethernet",
        "local_subnet": "PN/IE_1",
        "local_rack": 0,
        "local_slot": 1,
        "local_tsap": "14.01",
        "use_acc": False,
        "local_active": True,
        "partner_name": None,
        "partner_id": None,
        "partner_address": "192.168.1.50",
        "partner_rack": 0,
        "partner_slot": 2,
        "partner_tsap": "15.02",
        "partner_active": False,
        "valid": True,
    }
    return base | kw


def mapped(*entries: dict[str, Any]):  # type: ignore[no-untyped-def]
    return map_connections(list(entries), station=STATION, plc=PLC, module=MODULE, networks={NET})


def test_s7_connection_of_the_reference_sample() -> None:
    (c,), findings, _ = mapped(entry())
    assert findings == []
    assert c.ref == f"{STATION}/{PLC}/0x0100"
    assert (c.name, c.kind, c.details, c.active) == ("S7_Verbindung_1", "s7", "read", True)
    assert c.local == ConnectionEnd("0x0100", MODULE, NET, "192.168.1.1", "14.01")
    assert c.partner == ConnectionPartner(False, None, None, "192.168.1.50", 0, 2, "15.02")
    assert c.one_way is None and not c.sources and not c.differences


def test_local_id_is_read_as_hex() -> None:
    ids = [c.local.id for c in mapped(entry(local_id="101"), entry(local_id="1F"))[0]]
    assert ids == ["0x001F", "0x0101"]  # sorted by ref


def test_partner_plc_of_the_same_project_is_named_not_specified() -> None:
    (c,), _, _ = mapped(
        entry(
            local_id="102",
            local_name="S7_Verbindung_3",
            local_tsap="SIMATIC-ACC10201",
            use_acc=True,
            local_active=False,
            partner_name="PLC_2",
            partner_id="110",
            partner_address="192.168.1.5",
            partner_slot=1,
            partner_tsap="SIMATIC-ACC11001",
            partner_active=True,
        )
    )
    assert c.partner == ConnectionPartner(
        False, "PLC_2", None, "192.168.1.5", 0, 1, "SIMATIC-ACC11001"
    )
    assert c.local.tsap == "SIMATIC-ACC10201" and c.active is False


def test_other_connection_types_are_listed_not_read() -> None:
    (c,), _, _ = mapped(
        entry(**{"class": "TcpConnection", "type": "TcpConnection", "type_value": 3})
    )
    assert (c.kind, c.type_id, c.details) == ("other", 3, "not_read")
    assert c.local.tsap is None and c.partner == ConnectionPartner()


def test_a_tsap_of_neither_form_is_left_out_with_a_finding() -> None:
    (c,), findings, warnings = mapped(entry(local_tsap="1402", partner_tsap=""))
    assert c.local.tsap is None and c.partner.tsap is None  # empty means: not given
    assert [(f.code, f.connection) for f in findings] == [(VALUE_NOT_AVAILABLE, c.ref)]
    assert any("local_tsap" in w.message for w in warnings)


def test_an_interface_not_in_the_export_is_left_out() -> None:
    (c,), _, _ = map_connections([entry()], station=STATION, plc=PLC, module=MODULE, networks=set())
    assert c.local.interface is None and c.local.module == MODULE


def test_the_mapped_connections_pass_the_format_check() -> None:
    conns, _, _ = mapped(
        entry(),
        entry(local_id="102", local_tsap="SIMATIC-ACC10201", partner_tsap="SIMATIC-ACC11001"),
        entry(**{"class": "UdpConnection", "type": "UdpConnection", "type_value": 4,
                 "local_id": "103"}),
    )  # fmt: skip
    doc = to_doc(ConnectionsModel(connections=tuple(conns)))
    assert check_doc(doc, units=set(), modules={MODULE}, networks={NET}, racks=set()) == []
