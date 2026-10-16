"""``connections.json``: write → read round trip, determinism, one case per rule."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime

from plcexport.format.reader import read_files
from plcexport.format.validate import validate_files, validate_model
from plcexport.format.writer import ManifestInfo, render
from plcexport.model import (
    CATEGORIES,
    CONNECTIONS,
    CallValue,
    CategoryCoverage,
    Connection,
    ConnectionEnd,
    ConnectionPartner,
    ConnectionsModel,
    ConnectionUse,
    Coupler,
    Coverage,
    DataArea,
    ExportModel,
    ExportProject,
    ExportUnit,
    HardwareModel,
    HwModule,
    HwNetwork,
    HwRack,
    InterfaceFinding,
    TransferArea,
    ValueDifference,
)

INFO = ManifestInfo(
    source_path="samples/x.zip",
    checksum="sha256:" + "0" * 64,
    exported_at=datetime(2026, 10, 10, tzinfo=UTC),
)
CPU = "SIMATIC 300(1)/0.2"
NET = "SIMATIC 300(1)/CPU 315-2 PN/DP/ethernet"
COUPLER_RACK = "SIMATIC 300(1)/PROFINET-IO-System #1"
REF = "SIMATIC 300(1)/CPU 315-2 PN/DP/0x0010"


def connection(**changes: object) -> Connection:
    base = Connection(
        ref=REF,
        name="S7-Verbindung 2",
        kind="s7",
        local=ConnectionEnd("0x0010", CPU, NET, "10.100.10.20", "11.02"),
        partner=ConnectionPartner(False, "HomePLC3", None, "10.102.10.20", 0, 3, "10.03"),
        active=False,
        one_way=True,
        sources={"tsaps": "both", "active": "both", "partner_address": "both"},
    )
    return replace(base, **changes)  # type: ignore[arg-type]


def use(**changes: object) -> ConnectionUse:
    base = ConnectionUse(
        unit="Comm",
        block="BSEND",
        called="FB 12 #Send",
        network_no=2,
        line=5,
        id=CallValue("0xAAAA"),
        r_id=CallValue("0x00000010"),
        areas=(
            DataArea("SD_1", "send", "P#DB4.DBX0.0 INT 1", "DB_Send", "0.0", 2, ('"DB_Send".X',)),
            DataArea("SD_2", "send", unassigned=True),
        ),
        len=CallValue(unresolved="MW 10"),
        findings=(
            InterfaceFinding("id_not_configured"),
            InterfaceFinding("id_r_id_maybe_swapped", connection=REF),
        ),
    )
    return replace(base, **changes)  # type: ignore[arg-type]


def model(cm: ConnectionsModel | None = None, with_category: bool = True) -> ExportModel:
    cats = {c: CategoryCoverage("unavailable", "not_in_project") for c in CATEGORIES}
    cats["program_units"] = CategoryCoverage("delivered")
    cats["hardware"] = CategoryCoverage("delivered")
    cm = cm if cm is not None else full()
    if with_category:
        cats[CONNECTIONS] = (
            CategoryCoverage("delivered")
            if cm.item_count()
            else CategoryCoverage("unavailable", "not_in_project")
        )
    return ExportModel(
        project=ExportProject("siemens-step7-classic", "V5.6", "CPU", "Press", "x", "1", ("de",)),
        units=[ExportUnit("Comm", "FB", "STL", (), number=3)],
        hardware=HardwareModel(
            racks=(HwRack("SIMATIC 300(1)/R0", "rack 0"), HwRack(COUPLER_RACK, "coupler")),
            modules=(
                HwModule(CPU, "CPU 315-2 PN/DP", "SIMATIC 300(1)/R0", 2),
                HwModule(f"{COUPLER_RACK}.2", "IN/OUT", COUPLER_RACK, 2),
            ),
            networks=(HwNetwork(NET, "ethernet", "10.100.10.20/24"),),
        ),
        coverage=Coverage(categories=cats),
        connections=cm,
    )


def full() -> ConnectionsModel:
    return ConnectionsModel(
        connections=(
            connection(),
            connection(
                ref="SIMATIC 300(1)/CPU 315-2 PN/DP/0x0001",
                local=ConnectionEnd("0x0001", CPU),
                kind="other",
                type_id=1332999,
                details="not_read",
                partner=ConnectionPartner(),
                active=None,
                one_way=None,
                sources={},
            ),
            connection(
                ref="SIMATIC 300(1)/CPU 315-2 PN/DP/0x0002",
                local=ConnectionEnd("0x0002", CPU, NET, "10.100.10.20", "12.02"),
                differences=(ValueDifference("partner_tsap", "10.03", "10.04"),),
                safety=True,
            ),
        ),
        uses=(use(),),
        couplers=(
            Coupler(
                COUPLER_RACK,
                "pn_pn",
                "6ES7 158-3AD10-0XA0",
                "10.100.10.10",
                (TransferArea(f"{COUPLER_RACK}.2", "in", "%I2.0-%I13.7", 12, ('"I_Release"',)),),
                safety=True,
            ),
        ),
        findings=(InterfaceFinding("connection_unused", connection=REF),),
    )


def files(m: ExportModel) -> dict[str, str]:
    return render(m, INFO)


def as_bytes(f: dict[str, str]) -> dict[str, bytes]:
    return {k: v.encode("utf-8") for k, v in f.items()}


def test_round_trip_and_determinism() -> None:
    m = model()
    assert validate_model(m) == []
    out = files(m)
    assert out == files(m)
    assert validate_files(as_bytes(out)) == []
    back = read_files(out).model
    assert back.connections == m.connections.sorted()
    assert back.coverage.categories[CONNECTIONS].state == "delivered"
    doc = json.loads(out["connections.json"])
    c = next(x for x in doc["connections"] if x["ref"] == REF)
    assert c["local"] == {"address": "10.100.10.20", "id": "0x0010", "interface": NET,
                          "module": CPU, "tsap": "11.02"}  # fmt: skip
    assert c["active"] is False and c["one_way"] is True and c["partner"]["specified"] is False
    other = next(x for x in doc["connections"] if x["kind"] == "other")
    assert set(other) == {"ref", "name", "kind", "type_id", "details", "local"}
    u = doc["uses"][0]
    assert u["id"] == {"value": "0xAAAA"} and u["len"] == {"unresolved": "MW 10"}
    assert u["areas"][1] == {"param": "SD_2", "role": "send", "unassigned": True}
    assert "connection" not in u  # a finding never links a call


def test_index_shows_the_connections_as_netpro_does() -> None:
    index = files(model())["index.md"]
    assert (
        "| conn | Connections (connections: 3, calls: 1, couplers: 1) | connections.json |" in index
    )
    section = index[index.index("## Connections") :]
    assert "| 10 | S7-Verbindung 2 | SIMATIC 300(1)/CPU 315-2 PN/DP | HomePLC3 | 10.102.10.20 " \
           "| 11.02 / 10.03 | partner | yes | – |" in section  # fmt: skip
    assert (
        "- Comm NW 2 (BSEND): ID AAAA, R_ID 10 (ID is not a configured connection; "
        "R_ID equals configured connection ID 10: ID and R_ID may be swapped)"
    ) in section
    assert "(pn_pn, 6ES7 158-3AD10-0XA0): %I2.0-%I13.7" in section


def test_project_without_connections_says_so_and_writes_no_file() -> None:
    out = files(model(ConnectionsModel()))
    assert "connections.json" not in out
    assert "No connections configured." in out["index.md"]
    assert validate_files(as_bytes(out)) == []


def test_export_without_the_category_is_valid_and_reads_as_empty() -> None:
    """older exports and extractors that do not read connections."""
    m = model(ConnectionsModel(), with_category=False)
    assert validate_model(m) == []
    out = files(m)
    assert "## Connections" not in out["index.md"] and "connections.json" not in out
    assert validate_files(as_bytes(out)) == []
    back = read_files(out).model
    assert back.connections == ConnectionsModel() and CONNECTIONS not in back.coverage.categories


def test_content_needs_the_coverage_category() -> None:
    assert any(
        "without the coverage category" in v for v in validate_model(model(with_category=False))
    )


def _violations(cm: ConnectionsModel) -> list[str]:
    return validate_model(model(cm))


def test_each_rule_is_checked() -> None:
    def one(**changes: object) -> ConnectionsModel:
        return ConnectionsModel(connections=(connection(**changes),))

    assert any("not unique" in v for v in _violations(
        ConnectionsModel(connections=(connection(), connection()))))  # fmt: skip
    assert any("local.id" in v for v in _violations(one(local=ConnectionEnd("16", CPU))))
    assert any("local TSAP" in v for v in _violations(
        one(local=ConnectionEnd("0x0010", CPU, NET, None, "1102"))))  # fmt: skip
    assert any("partner TSAP" in v for v in _violations(
        one(partner=ConnectionPartner(tsap="3.00"))))  # fmt: skip
    assert any(
        "local.module" in v for v in _violations(one(local=ConnectionEnd("0x0010", "x/0.9")))
    )
    assert any("local.interface" in v for v in _violations(
        one(local=ConnectionEnd("0x0010", CPU, "nowhere/ethernet"))))  # fmt: skip
    assert any("partner.module" in v for v in _violations(
        one(partner=ConnectionPartner(True, module="x/0.9"))))  # fmt: skip
    assert any("type_id" in v for v in _violations(one(kind="other")))
    assert any("type_id" in v for v in _violations(one(type_id=5)))
    full_use = ConnectionsModel(connections=(connection(),), uses=(use(unit="Nowhere"),))
    assert any("no unit file" in v for v in _violations(full_use))
    bad_id = ConnectionsModel(uses=(use(id=CallValue("AAAA"), findings=()),))
    assert any("id value" in v for v in _violations(bad_id))
    bad_link = ConnectionsModel(uses=(use(connection="x/0x0009", findings=()),))
    assert any("is not in the file" in v for v in _violations(bad_link))
    bad_finding = ConnectionsModel(uses=(use(),))  # the hint names a connection that is absent
    assert any("unknown connection" in v for v in _violations(bad_finding))
    bad_coupler = ConnectionsModel(couplers=(Coupler("nowhere", "pn_pn"),))
    assert any("not a rack" in v for v in _violations(bad_coupler))
    stray = TransferArea("x/1.1", "in", "%I0.0-%I0.7", 1)
    bad_area = ConnectionsModel(couplers=(Coupler(COUPLER_RACK, "dp_dp", transfer_areas=(stray,)),))
    assert any("transfer module" in v for v in _violations(bad_area))


def test_one_value_form_per_parameter_in_a_file() -> None:
    out = files(model())
    doc = json.loads(out["connections.json"])
    doc["uses"][0]["id"] = {"value": "0xAAAA", "unassigned": True}
    out["connections.json"] = json.dumps(doc, sort_keys=True, indent=2) + "\n"
    assert any("exactly one of" in v for v in validate_files(as_bytes(out)))


def test_simatic_acc_tsaps_are_valid() -> None:
    """a connection with SIMATIC ACC has text TSAPs, exported as TIA shows them."""

    def one(local: str, partner: str) -> ConnectionsModel:
        return ConnectionsModel(
            connections=(
                connection(
                    local=ConnectionEnd("0x0102", CPU, NET, None, local),
                    partner=ConnectionPartner(tsap=partner),
                ),
            )
        )

    assert _violations(one("SIMATIC-ACC10201", "SIMATIC-ACC11001")) == []
    for bad in ("SIMATIC-ACC", "simatic-acc10201", "ACC10201", "SIMATIC-ACC1020G"):
        assert any("TSAP" in v for v in _violations(one(bad, "15.02"))), bad
