"""communication block calls in SIMATIC SD text. The first
case is the reference sample's ``Main`` as recorded (fixture ``conn_v21``)."""

from __future__ import annotations

import pytest

from plcexport.extractors.tia.comm_calls import sd_calls
from plcexport.model import CallValue, DataArea
from tests.conftest import FIXTURES

MAIN = FIXTURES / "tiadump" / "conn_v21" / "sd" / "PLC_1" / "Programmbausteine" / "Main.s7dcl"


def test_bsend_and_brcv_of_the_reference_sample() -> None:
    send, recv = sd_calls("Main", MAIN.read_text(encoding="utf-8-sig"))
    assert (send.unit, send.block, send.called, send.network_no) == (
        "Main", "BSEND", '"BSEND_DB".BSEND', 1,
    )  # fmt: skip
    assert send.id == CallValue("0x0100") and send.r_id == CallValue("0x0000000B")
    assert send.areas == (
        DataArea("SD_1", "send", '"Datenbaustein_1".write', "Datenbaustein_1",
                 members=('"Datenbaustein_1".write',)),
    )  # fmt: skip
    assert send.len == CallValue(unresolved='"Datenbaustein_1".Len1')
    assert (recv.block, recv.network_no, recv.id, recv.r_id) == (
        "BRCV", 2, CallValue("0x0101"), CallValue("0x0000000A"),
    )  # fmt: skip
    assert recv.areas[0].param == "RD_1" and recv.areas[0].role == "receive"
    assert recv.len == CallValue(unresolved='"Datenbaustein_1".Len2')
    assert send.connection is None and send.findings == ()  # linking comes later


def _scl(body: str) -> str:
    return (
        'FUNCTION_BLOCK "Comm"\n   VAR\n      g {S7_SetPoint := "False"} : GET;\n   END_VAR\n'
        + body
    )


def test_literals_variables_and_unassigned_values() -> None:
    text = """    NETWORK
        RUNG wire#powerrail
            "PUT_DB".PUT(REQ := , ID := W#16#1F, ADDR_1 := P#DB10.DBX4.0 BYTE 10,
                         SD_1 := "Send".buf, DONE => , ERROR => )
            "USEND_DB".USEND(REQ := , ID := WORD#16#20, R_ID := DW#16#7, SD_1 := #area)
            "URCV_DB".URCV(EN_R := , ID := 32, R_ID := #rid, RD_1 := )
        END_RUNG
    END_NETWORK
"""
    put, usend, urcv = sd_calls("Comm", text)
    assert put.id == CallValue("0x001F") and put.r_id is None  # PUT has no R_ID
    remote, local = put.areas
    assert remote == DataArea("ADDR_1", "remote", "P#DB10.DBX4.0 BYTE 10", start="4.0",
                              length_bytes=10)  # fmt: skip
    assert (local.param, local.role, local.db) == ("SD_1", "send", "Send")
    assert (usend.id, usend.r_id) == (CallValue("0x0020"), CallValue("0x00000007"))
    assert usend.areas == (DataArea("SD_1", "send", unresolved="#area"),)
    assert urcv.id == CallValue("0x0020") and urcv.r_id == CallValue(unresolved="#rid")
    assert urcv.areas == (DataArea("RD_1", "receive", unassigned=True),)
    assert put.len is None  # PUT has no LEN


def test_absolute_pointer_names_its_data_block() -> None:
    text = (
        'NETWORK\n"GET_DB".GET(ID := 16#1, ADDR_1 := P#DB10.DBX0.0 BYTE 4,\n'
        "RD_1 := P#DB2.DBX8.0 WORD 2)\nEND_NETWORK\n"
    )
    (get,) = sd_calls("U", text, db_number={2: "Recv"}.get)
    remote, rd = get.areas
    assert remote.db is None  # a remote area lies in the partner PLC
    assert (rd.db, rd.start, rd.length_bytes) == ("Recv", "8.0", 4)


def test_scl_calls_have_a_line_and_no_network() -> None:
    text = _scl(
        "BEGIN\n   #g(REQ := TRUE,\n      ID := 16#100,\n      ADDR_1 := #remote,\n"
        "      RD_1 := #local);\nEND_FUNCTION_BLOCK\n"
    )
    (get,) = sd_calls("Comm", text, statics={"g": "GET"})
    assert (get.block, get.called, get.network_no, get.line) == ("GET", "#g", None, 6)
    assert get.id == CallValue("0x0100")


def test_other_blocks_and_unknown_instances_are_ignored() -> None:
    text = (
        'NETWORK\n"TSEND_C_DB".TSEND_C(REQ := , ID := 16#1, DATA := "x".y)\n'
        '"Some_DB"(ID := 16#1)\n#other(ID := 16#1)\nEND_NETWORK\n'
    )
    assert sd_calls("U", text, statics={"other": "MyFB"}) == []


@pytest.mark.xfail(reason="no SimaticML sample with a communication call")
def test_simaticml_calls() -> None:
    """Units SD refuses (S7-300/400 in TIA, GRAPH) are exported as SimaticML; their GET/PUT/
    BSEND/BRCV/USEND/URCV calls need a recorded sample before the route is built."""
    found = sorted(
        p for p in (FIXTURES / "tiadump").rglob("*.xml")
        if any(f'Name="{b}"' in p.read_text(encoding="utf-8", errors="ignore")
               for b in ("GET", "PUT", "BSEND", "BRCV", "USEND", "URCV"))
    )  # fmt: skip
    assert found, "no recorded SimaticML unit with a communication call"
