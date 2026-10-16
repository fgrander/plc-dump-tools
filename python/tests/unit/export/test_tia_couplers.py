"""PN/PN and DP/DP couplers of a TIA PLC. The device
entries have the shape of the recorded sample ``conn_v21``; values are the owner-confirmed ones."""

from __future__ import annotations

from typing import Any

from plcexport.extractors.tia.connections import (
    LENGTH_MISMATCH,
    SIDE_WITHOUT_CONTROLLER,
    map_couplers,
)
from plcexport.model import ExportVariable, TransferArea

CONTROLLER = "S7-1500/ET200MP-Station_1/PLC_1"


def area(
    name: str, typ: str, p2l: int, l2p: int, *addresses: tuple[str, int, int]
) -> dict[str, Any]:
    return {
        "name": name, "type": typ, "direction": "x", "position": 1,
        "local_to_partner_bytes": l2p, "partner_to_local_bytes": p2l,
        "controller_addresses": [
            {"io": io, "start": start, "bits": bits, "controller": "PLC_1"}
            for io, start, bits in addresses
        ],
    }  # fmt: skip


def pn_coupler(
    name: str, order: str, x1_areas: list[dict[str, Any]], x2_areas: list[dict[str, Any]]
) -> dict[str, Any]:
    def side(s: str, areas: list[dict[str, Any]], controller: str | None) -> list[dict[str, Any]]:
        head = {
            "name": f"{name}.{s}",
            "path": f"{name}.{s}",
            "rack": f"{name}.{s}",
            "slot": 0,
            "order_no": order,
            "addresses": [],
            "interfaces": [],
        }
        iface: dict[str, Any] = {
            "name": f"PROFINET-Schnittstelle {s}",
            "path": f"{name}.{s}/PROFINET-Schnittstelle {s}",
            "rack": f"{name}.{s}",
            "slot": 1,
            "order_no": None,
            "addresses": [],
            "interfaces": [{"node": s, "type": "Ethernet", "address": "192.168.1.20/24"}],
            "transfer_areas": areas,
        }
        if controller:
            iface["io_system"] = {
                "name": "PROFINET IO-System",
                "number": 100,
                "controller": controller,
            }
        return [head, iface]

    return {"name": name, "items": side("X1", x1_areas, CONTROLLER) + side("X2", x2_areas, None)}


def test_pn_pn_side_of_the_plc_with_its_transfer_areas() -> None:
    dev = pn_coupler("PNPN Coupler", "6ES7 158-3AD01-0XA0", [
        area("Transferbereich_IN1", "IN", 10, 0, ("input", 500, 80)),
        area("Transferbereich_3", "OUT", 0, 1, ("output", 8, 8)),
        area("Transferbereich_6", "IN_OUT", 1, 1, ("input", 38, 8), ("output", 10, 8)),
    ], [area("Transferbereich_IN1", "OUT", 0, 10)])  # fmt: skip
    tags = [ExportVariable("IO", "global_tag", '"Coupler_In"', "Byte", address="%IB500"),
            ExportVariable("IO", "global_tag", '"Other"', "Bool", address="%I2.0")]  # fmt: skip
    (k,), findings, warnings = map_couplers([dev], plc="PLC_1", variables=tags)
    assert (k.ref, k.kind, k.order_no, k.address) == (
        "PNPN Coupler/PNPN Coupler.X1", "pn_pn", "6ES7 158-3AD01-0XA0", "192.168.1.20",
    )  # fmt: skip
    module = "PNPN Coupler/PNPN Coupler.X1"
    assert k.transfer_areas == (
        TransferArea(module, "in", "%I500.0-%I509.7", 10, ('"Coupler_In"',)),
        TransferArea(module, "out", "%Q8.0-%Q8.7", 1),
        TransferArea(module, "in", "%I38.0-%I38.7", 1),
        TransferArea(module, "out", "%Q10.0-%Q10.7", 1),
    )
    # X2 is connected to no IO system: reported, not exported as a coupler
    assert [(f.code, f.coupler) for f in findings] == [
        (SIDE_WITHOUT_CONTROLLER, "PNPN Coupler/PNPN Coupler.X2")
    ]
    assert any("PNPN Coupler.X2" in w.message for w in warnings)


def test_area_length_differs_from_its_address() -> None:
    """Coupler_1 of the sample: the area says 1 byte, PLC_1's address is 16 bits."""
    dev = pn_coupler("PNPN Coupler_1", "6ES7 158-3AD10-0XA0",
                     [area("Transferbereich_1", "IN", 1, 0, ("input", 36, 16))], [])  # fmt: skip
    (k,), findings, warnings = map_couplers([dev], plc="PLC_1", variables=[])
    assert k.transfer_areas[0].range == "%I36.0-%I37.7" and k.transfer_areas[0].length_bytes == 2
    assert (LENGTH_MISMATCH, "PNPN Coupler_1/PNPN Coupler_1.X1") in [
        (f.code, f.coupler) for f in findings
    ]
    assert any("Transferbereich_1" in w.message and "1 byte" in w.message for w in warnings)


def test_a_side_of_another_plc_is_not_in_this_export() -> None:
    dev = pn_coupler("K", "6ES7 158-3AD10-0XA0", [area("A", "IN", 1, 0, ("input", 1, 8))], [])
    couplers, findings, _ = map_couplers([dev], plc="PLC_2", variables=[])
    assert couplers == [] and findings == []  # X1 belongs to PLC_1; X2 has no areas


def test_dp_dp_coupler_from_its_modules() -> None:
    dev = {"name": "GSD-Geraet_1", "items": [
        {"name": "Slave_1", "path": "Slave_1", "rack": "Slave_1", "slot": 0,
         "order_no": "6ES7 158-0AD01-0XA0", "addresses": [], "interfaces": [],
         "io_system": {"name": "DP-Mastersystem", "number": 1, "controller": CONTROLLER}},
        {"name": "16 Bytes Eingang_1", "path": "16 Bytes Eingang_1", "rack": "16 Bytes Eingang_1",
         "slot": 1, "order_no": None, "addresses": [{"io": "input", "start": 10, "length": 128}]},
        {"name": "4 Bytes Ausgang_1", "path": "4 Bytes Ausgang_1", "rack": "4 Bytes Ausgang_1",
         "slot": 2, "order_no": None, "addresses": [{"io": "output", "start": 4, "length": 32}]},
    ]}  # fmt: skip
    (k,), findings, _ = map_couplers([dev], plc="PLC_1", variables=[])
    assert (k.ref, k.kind, k.order_no) == ("GSD-Geraet_1/Slave_1", "dp_dp", "6ES7 158-0AD01-0XA0")
    assert [(t.module, t.direction, t.range, t.length_bytes) for t in k.transfer_areas] == [
        ("GSD-Geraet_1/16 Bytes Eingang_1", "in", "%I10.0-%I25.7", 16),
        ("GSD-Geraet_1/4 Bytes Ausgang_1", "out", "%Q4.0-%Q7.7", 4),
    ]
    assert findings == []


def test_other_devices_are_no_couplers() -> None:
    dev = {"name": "ET 200S", "items": [
        {"name": "IO-Device_1", "path": "IO-Device_1", "rack": "IO-Device_1", "slot": 0,
         "order_no": "6ES7 151-3BA23-0AB0", "addresses": [], "interfaces": [],
         "io_system": {"name": "PROFINET IO-System", "number": 100, "controller": CONTROLLER}},
    ]}  # fmt: skip
    assert map_couplers([dev], plc="PLC_1", variables=[]) == ([], [], [])
