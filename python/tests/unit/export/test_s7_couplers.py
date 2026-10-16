"""PN/PN and DP/DP couplers in the exported hardware, with their transfer areas."""

from __future__ import annotations

from plcexport.extractors.s7classic.couplers import kind_of
from plcexport.extractors.s7classic.mapping import MappingOptions, to_model
from plcexport.format.validate import validate_model
from plcexport.model import CONNECTIONS, ExportModel
from tests.contract.export.s7helpers import load_dump

OPTS = MappingOptions("s7classic-direct", "1.0.0", text_language="de")
PN = "SIMATIC 300(1)/PROFINET-IO-System #2"
DP = "SIMATIC 300(1)/DP master system #5"


def model() -> ExportModel:
    m = to_model(load_dump("couplers"), OPTS)
    assert validate_model(m) == []
    return m


def test_kind_by_order_number() -> None:
    assert kind_of("6ES7 158-3AD10-0XA0") == "pn_pn" and kind_of("6ES7158-3AD01-0XA0") == "pn_pn"
    assert kind_of("6ES7 158-0AD01-0XA0") == "dp_dp"
    assert kind_of("6ES7 151-3BA23-0AB0") is None and kind_of(None) is None


def test_couplers_with_transfer_areas_and_symbols() -> None:
    couplers = {c.ref: c for c in model().connections.couplers}
    assert set(couplers) == {PN, DP}  # the drive on the same IO system is no coupler
    pn = couplers[PN]
    assert (pn.kind, pn.order_no, pn.safety) == ("pn_pn", "6ES7 158-3AD10-0XA0", True)
    assert [(t.direction, t.range, t.length_bytes) for t in pn.transfer_areas] == [
        ("in", "%I2.0-%I13.7", 12),
        ("out", "%Q2.0-%Q7.7", 6),
    ]
    assert pn.transfer_areas[0].module == f"{PN}.2"
    assert pn.transfer_areas[0].symbols == ('"I_Release_From_B"',)
    assert pn.transfer_areas[1].symbols == ()
    dp = couplers[DP]
    assert (dp.kind, dp.order_no, dp.safety, dp.address) == (
        "dp_dp", "6ES7 158-0AD01-0XA0", False, None,
    )  # fmt: skip
    assert [(t.direction, t.length_bytes) for t in dp.transfer_areas] == [("in", 4), ("out", 4)]


def test_couplers_alone_deliver_the_category() -> None:
    m = model()
    assert m.connections.connections == () and m.connections.item_count() == 2
    assert m.coverage.categories[CONNECTIONS].state == "delivered"


def test_project_without_coupler_has_none() -> None:
    assert to_model(load_dump("connections"), OPTS).connections.couplers == ()
