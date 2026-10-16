"""communication block calls from raw STL (statements without call reconstruction)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from plcexport.extractors.s7classic.comm_calls import POINTER_CODE, constant, find_calls
from plcexport.model import CallValue


def io(name: str, section: str, type_: str, offset: str) -> dict[str, Any]:
    return {"name": name, "section": section, "type": type_, "offset": offset}


def any_params(*names_and_offsets: tuple[str, int]) -> list[dict[str, Any]]:
    return [io(n, "IN_OUT", "ANY", f"{o}.0") for n, o in names_and_offsets]


HEAD = [io("REQ", "IN", "BOOL", "0.0"), io("ID", "IN", "WORD", "2.0")]
R_ID = [io("R_ID", "IN", "DWORD", "4.0")]
BLOCKS: dict[str, dict[str, Any]] = {
    '"BSEND"': {"type": "FB", "number": 12, "interface": [
        *HEAD, *R_ID, *any_params(("SD_1", 12)), io("LEN", "IN_OUT", "WORD", "22.0")]},
    '"BRCV"': {"type": "FB", "number": 13, "interface": [
        *HEAD, *R_ID, *any_params(("RD_1", 12)), io("LEN", "IN_OUT", "WORD", "22.0")]},
    '"GET"': {"type": "SFB", "number": 14, "interface": [
        *HEAD, *any_params(("ADDR_1", 8), ("ADDR_2", 18), ("RD_1", 48), ("RD_2", 58))]},
    '"PUT"': {"type": "SFB", "number": 15, "interface": [
        *HEAD, *any_params(("ADDR_1", 8), ("SD_1", 48))]},
    '"USEND"': {"type": "SFB", "number": 8, "interface": [
        *HEAD, *R_ID, *any_params(("SD_1", 8), ("SD_2", 18), ("SD_3", 28), ("SD_4", 38))]},
    '"URCV"': {"type": "SFB", "number": 9, "interface": [
        *HEAD, *R_ID, *any_params(("RD_1", 8), ("RD_2", 18), ("RD_3", 28), ("RD_4", 38))]},
    # a user block that happens to have the number of BSEND
    '"MyFB12"': {"type": "FB", "number": 12, "interface": [io("Start", "IN", "BOOL", "0.0")]},
    '"Other"': {"type": "FB", "number": 40, "interface": []},
}  # fmt: skip
BLOCKS["FB12"] = BLOCKS['"BSEND"']
BLOCKS["SFB14"] = BLOCKS['"GET"']


def resolve(target: str) -> Mapping[str, Any] | None:
    return BLOCKS.get(target) or BLOCKS.get(target.replace(" ", ""))


def raw(*statements: str) -> list[str]:
    return [f"      {s}" for s in statements]


def any_at(first: str, offset: int, type_word: str, count: int, db: int, pointer: str) -> list[str]:
    return [f"L     {type_word}", f"T     {first}", f"L     {count}",
            f"T     DIW[AR2,P#{offset + 2}.0]", f"L     {db}", f"T     DIW[AR2,P#{offset + 4}.0]",
            f"L     {pointer}", f"T     DID[AR2,P#{offset + 6}.0]"]  # fmt: skip


def test_constants() -> None:
    assert constant("-21846") == -21846 and constant("L#16") == 16
    assert constant("W#16#1005") == 0x1005 and constant("DW#16#0000_0010") == 16
    assert constant("B#16#FF") == 255 and constant("2#101") == 5
    assert constant("MW 10") is None and constant("P#DBX 0.0") is None and constant("#x") is None


def test_ids_and_any_pointer_of_a_multi_instance_call() -> None:
    """The sample's BSEND: instance at 90, ID AAAA (16 bit), R_ID 16 (32 bit), SD_1 in DB 4."""
    (call,) = find_calls(
        raw("BLD   14", "TAR2  LD1", "L     -21846", "T     #Send.IN.ID", "L     L#16",
            "T     #Send.IN.R_ID",
            *any_at("#Send.IN_OUT.SD_1", 102, "W#16#1005", 1, 4, "P#DBX 0.0"),
            "+AR2  P#90.0", 'UC    "BSEND"', "BLD   15", "NOP   0"),
        resolve,
    )  # fmt: skip
    assert (call.block, call.called) == ("BSEND", "FB 12 #Send")
    assert call.id == CallValue("0xAAAA") and call.r_id == CallValue("0x00000010")
    assert call.len == CallValue(unassigned=True)
    (area,) = call.areas
    assert (area.param, area.role, area.pointer) == ("SD_1", "send", "P#DB4.DBX0.0 INT 1")
    assert (area.db_number, area.start, area.length_bytes) == (4, "0.0", 2)


def test_variable_makes_a_parameter_unresolved_and_none_makes_it_unassigned() -> None:
    (call,) = find_calls(
        raw("L     MW 10", "T     #Recv.IN.ID", "L     #Len", "T     #Recv.IN_OUT.LEN",
            "+AR2  P#0.0", 'UC    "BRCV"'),
        resolve,
    )  # fmt: skip
    assert call.id == CallValue(unresolved="MW 10") and call.len == CallValue(unresolved="#Len")
    assert call.r_id == CallValue(unassigned=True)
    assert call.areas[0].unassigned and call.areas[0].role == "receive"


def test_any_with_a_variable_part_is_unresolved_as_written() -> None:
    parts = any_at("#Send.IN_OUT.SD_1", 12, "W#16#1002", 8, 4, "P#DBX 0.0")
    parts[4] = "L     MW 20"  # the DB number comes from a variable
    (call,) = find_calls(raw("L     1", "T     #Send.IN.ID", *parts, 'UC    "BSEND"'), resolve)
    assert call.areas[0].unresolved == "W#16#1002, 8, MW 20, P#DBX 0.0"
    assert call.areas[0].pointer is None


def test_pointer_code_in_front_of_the_call_is_not_called_unassigned() -> None:
    (call,) = find_calls(
        raw("L     P##Data", "LAR1", "L     W [AR1,P#0.0]", "T     LW 10", "L     1",
            "T     #Send.IN.ID", 'UC    "BSEND"'),
        resolve,
    )  # fmt: skip
    assert call.id == CallValue("0x0001")
    assert call.r_id == CallValue(unresolved=POINTER_CODE)
    assert call.areas[0].unresolved == POINTER_CODE


def test_memory_areas_types_and_lengths() -> None:
    (call,) = find_calls(
        raw("L     1", "T     #P.IN.ID",
            *any_at("#P.IN_OUT.ADDR_1", 8, "W#16#1002", 8, 0, "P#M 10.0"),
            *any_at("#P.IN_OUT.SD_1", 48, "W#16#1001", 12, 0, "P#E 4.0"),
            "+AR2  P#0.0", 'UC    "PUT"'),
        resolve,
    )  # fmt: skip
    remote, send = call.areas
    assert (remote.role, remote.pointer, remote.length_bytes) == ("remote", "P#M 10.0 BYTE 8", 8)
    assert remote.db_number is None
    assert (send.role, send.pointer, send.length_bytes) == ("send", "P#I 4.0 BOOL 12", 2)
    assert call.block == "PUT" and call.r_id is None and call.len is None


def test_usend_and_urcv_have_four_areas() -> None:
    (send,) = find_calls(
        raw("L     W#16#3", "T     DIW 2", "L     DW#16#7", "T     DID 4",
            "L     W#16#1004", "T     DIW 8", "L     2", "T     DIW 10", "L     7", "T     DIW 12",
            "L     P#DBX 4.0", "T     DID 14", "OPN   DI 30", 'UC    "USEND"'),
        resolve,
    )  # fmt: skip
    assert (send.block, send.called) == ("USEND", "SFB 8 DB 30")
    assert send.id == CallValue("0x0003") and send.r_id == CallValue("0x00000007")
    assert [a.param for a in send.areas] == ["SD_1", "SD_2", "SD_3", "SD_4"]
    assert send.areas[0].pointer == "P#DB7.DBX4.0 WORD 2" and send.areas[0].length_bytes == 4
    assert all(a.unassigned for a in send.areas[1:])
    (recv,) = find_calls(raw("L     3", "T     DIW 2", 'UC    "URCV"'), resolve)
    assert recv.block == "URCV" and [a.role for a in recv.areas] == ["receive"] * 4


def test_absolute_call_and_two_calls_in_one_network() -> None:
    first, second = find_calls(
        raw("L     1", "T     #A.IN.ID", "+AR2  P#0.0", "UC    SFB   14",
            "L     2", "T     #B.IN.ID", "L     L#5", "T     #B.IN.R_ID", "+AR2  P#90.0",
            "UC    FB    12"),
        resolve,
    )  # fmt: skip
    assert (first.block, first.id, first.called) == ("GET", CallValue("0x0001"), "SFB 14 #A")
    assert (second.block, second.id) == ("BSEND", CallValue("0x0002"))
    assert second.r_id == CallValue("0x00000005")  # the first call's values do not leak


def test_other_blocks_and_a_user_fb_with_the_same_number_are_no_calls() -> None:
    assert find_calls(raw("L     1", "T     DIW 2", 'UC    "Other"'), resolve) == []
    assert find_calls(raw("L     1", "T     DIW 2", 'UC    "MyFB12"'), resolve) == []
    assert find_calls(raw("L     1", "T     DIW 2", 'UC    "Unknown"'), resolve) == []
    assert find_calls([], resolve) == []


def test_german_mnemonics() -> None:
    (call,) = find_calls(
        raw("AUF   DI 30", "L     W#16#1", "T     DIW 2", 'UC    "BSEND"'), resolve
    )
    assert call.called == "FB 12 DB 30" and call.id == CallValue("0x0001")
