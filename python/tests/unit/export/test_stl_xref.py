"""one test per row of contracts/stl-xref-rules.md."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from plcexport.extractors.s7classic.stl import analyze


def refs(lines: list[str], callees: Mapping[str, Mapping[str, str]] | None = None) -> list[tuple]:
    result = analyze(lines, (lambda n: (callees or {}).get(n)))
    return [(r.line, r.target_text, r.target_kind, r.access, r.via_param) for r in result.refs]


@pytest.mark.parametrize("op", ["A", "AN", "O", "ON", "X", "XN", "U", "UN"])
def test_bit_logic_reads(op: str) -> None:
    assert refs([f"      {op}     I      0.0"]) == [(0, "I 0.0", "variable", "read", None)]


@pytest.mark.parametrize("op", ["=", "S", "R"])
def test_assign_set_reset_write(op: str) -> None:
    assert refs([f"      {op}     Q 4.0"]) == [(0, "Q 4.0", "variable", "write", None)]


def test_edge_is_read_write() -> None:
    assert refs(["      FP    M 2.0"]) == [(0, "M 2.0", "variable", "read_write", None)]


def test_load_and_transfer() -> None:
    assert refs(["      L     MW 10", "      T     DBW 4"]) == [
        (0, "MW 10", "variable", "read", None),
        (1, "DBW 4", "variable", "write", None),
    ]


@pytest.mark.parametrize("op", ["SP", "SE", "SD", "SS", "SF", "SI", "SV", "SA", "CU", "CD",
                                "ZV", "ZR", "FR"])  # fmt: skip
def test_timer_and_counter_starts_write(op: str) -> None:
    assert refs([f"      {op}    T      5"])[0][3] == "write"


def test_timer_checks_and_loads_read() -> None:
    assert refs(["      A     T 5", "      L     T 5", "      LC    C 3"]) == [
        (0, "T 5", "variable", "read", None),
        (1, "T 5", "variable", "read", None),
        (2, "C 3", "variable", "read", None),
    ]


def test_open_db_is_a_unit_read() -> None:
    assert refs(["      OPN   DB    20", "      AUF   DI 30"]) == [
        (0, "DB 20", "unit", "read", None),
        (1, "DI 30", "unit", "read", None),
    ]


def test_fully_qualified_db_access() -> None:
    assert refs(['      =     "DB_Recipe".Ready', "      L     DB10.DBW 2"]) == [
        (0, '"DB_Recipe".Ready', "variable", "write", None),
        (1, "DB10.DBW 2", "variable", "read", None),
    ]


def test_call_with_instance_and_parameters_by_callee_section() -> None:
    lines = [
        '      CALL  "FB_Heating" , "DB_Heating"',
        '       TempActual:="I_TempPlate"',
        '       HeaterOn  :="Q_Heater_On"',
        "       Mode      :=MW 10",
        "       Limit     :=2.500000e+002",
        "      A     M 1.0",
    ]
    callee = {'"FB_Heating"': {"TempActual": "IN", "HeaterOn": "OUT", "Mode": "IN_OUT"}}
    assert refs(lines, callee) == [
        (0, '"FB_Heating"', "unit", "call", None),
        (0, '"DB_Heating"', "variable", "call", None),
        (1, '"I_TempPlate"', "variable", "read", "TempActual"),
        (2, '"Q_Heater_On"', "variable", "write", "HeaterOn"),
        (3, "MW 10", "variable", "read_write", "Mode"),
        (5, "M 1.0", "variable", "read", None),
    ]


def test_unknown_callee_gives_unknown_direction() -> None:
    assert refs(["      CALL  FC 99", "       X:=M 1.0"]) == [
        (0, "FC 99", "unit", "call", None),
        (1, "M 1.0", "variable", "unknown_direction", "X"),
    ]


@pytest.mark.parametrize("op", ["UC", "CC"])
def test_uc_cc_calls(op: str) -> None:
    assert refs([f"      {op}    FC 5"]) == [(0, "FC 5", "unit", "call", None)]


def test_register_indirect() -> None:
    assert refs(["      A     I [AR1,P#0.0]", "      L     W [AR2,P#2.0]"]) == [
        (0, "I [AR1,P#0.0]", "variable", "indirect", None),
        (1, "W [AR2,P#2.0]", "variable", "indirect", None),
    ]


def test_memory_indirect_reads_the_pointer() -> None:
    assert refs(["      L     MW [MD 10]", "      OPN   DB [MW 4]"]) == [
        (0, "MW [MD 10]", "variable", "indirect", None),
        (0, "MD 10", "variable", "read", None),
        (1, "DB [MW 4]", "variable", "indirect", None),
        (1, "MW 4", "variable", "read", None),
    ]


@pytest.mark.parametrize("line", ["      JC    M001", "      JU    END", "      SPB   M001",
                                  "M001: NOP   0", "      LOOP  M002"])  # fmt: skip
def test_jumps_and_labels_give_nothing(line: str) -> None:
    assert refs([line]) == []


@pytest.mark.parametrize("line", ["      NOT", "      SET", "      CLR", "      +I", "      TAK",
                                  "      BE", "      BEC", "      <R", "      L     S5T#5S",
                                  "      L     1.000000e+002", "      L     100"])  # fmt: skip
def test_status_and_constants_give_nothing(line: str) -> None:
    assert refs([line]) == []


def test_german_mnemonics() -> None:
    assert refs(["      U     E 0.0", "      =     A 4.0", "      ZV    Z 3"]) == [
        (0, "E 0.0", "variable", "read", None),
        (1, "A 4.0", "variable", "write", None),
        (2, "Z 3", "variable", "write", None),
    ]


def test_label_and_comment_are_ignored() -> None:
    assert refs(["M001: A     I 0.1   // start button"]) == [(0, "I 0.1", "variable", "read", None)]


def test_unclassified_line_warns_without_exception() -> None:
    result = analyze(["      FROB  M 1.0", "      A     M 1.1"])
    assert [(r.line, r.target_text) for r in result.refs] == [(1, "M 1.1")]
    assert result.warnings == [(0, "FROB  M 1.0")]


def test_real_call_syntax_with_parameter_list() -> None:
    """As s7dump writes it for a real project (PompesSy, S7-GRAPH FB with empty parameters)."""
    lines = [
        '      AN    "enGorL"',
        "      JNB   _001",
        '      CALL  "GRAFCET FB", DB1 (',
        "            OFF_SQ   := ,",
        '            S_ON     := "b1",',
        "            S_NO     := ",
        "      )",
        "_001: NOP   0",
        '      A     "b2"',
        '      CALL  "GRAFCET FB", DB1 (',
        '            S_ON     := "b3",',
        "            MAN_ON   := )",
        '      =     "P1"',
    ]
    callee = {'"GRAFCET FB"': {"OFF_SQ": "IN", "S_ON": "IN", "S_NO": "OUT"}}
    assert refs(lines, callee) == [
        (0, '"enGorL"', "variable", "read", None),
        (2, '"GRAFCET FB"', "unit", "call", None),
        (2, "DB1", "variable", "call", None),
        (4, '"b1"', "variable", "read", "S_ON"),
        (8, '"b2"', "variable", "read", None),
        (9, '"GRAFCET FB"', "unit", "call", None),
        (9, "DB1", "variable", "call", None),
        (10, '"b3"', "variable", "read", "S_ON"),
        (12, '"P1"', "variable", "write", None),
    ]


def test_label_with_spaces_before_colon_and_instance_db_addresses() -> None:
    lines = ["T1  : NOP   0             // Trans1 0001", '      A     "b1"', "      =     DIX414.0",
             "      L     DIB152"]  # fmt: skip
    assert refs(lines) == [
        (1, '"b1"', "variable", "read", None),
        (2, "DIX414.0", "variable", "write", None),
        (3, "DIB152", "variable", "read", None),
    ]


def test_array_element_is_the_array_variable_not_indirect() -> None:
    lines = ['L "DB_Rec".Speed[#i]', 'T "DB_Rec".Arr[3, "Idx"]', "T #tXY.XY[1, 0]"]
    got = [(r.line, r.target_text, r.access) for r in analyze(lines).refs]
    assert got == [
        (0, '"DB_Rec".Speed', "read"), (0, "#i", "read"),
        (1, '"DB_Rec".Arr', "write"), (1, '"Idx"', "read"),
        (2, "#tXY.XY", "write"),  # constant indexes give nothing
    ]  # fmt: skip


def test_array_element_as_call_parameter() -> None:
    lines = ['CALL "FB_X", "DB_X"', '  IN := "DB_Rec".Arr[#k]', ")"]
    got = {(r.target_text, r.access, r.via_param) for r in analyze(lines).refs}
    assert ('"DB_Rec".Arr', "unknown_direction", "IN") in got
    assert ("#k", "read", None) in got


@pytest.mark.parametrize(
    ("operand", "is_global"),
    [
        ("I 0.0", True), ("E 0.0", True), ("PIW 256", True), ("Q 4.2", True), ("MW 10", True),
        ("T 5", True), ("Z 3", True), ("DB20.DBX0.0", True), ("DBW 4", True), ('"Motor"', True),
        ('"Rec".Speed', True), ("DB10", True),
        ("#temp", False), ("L 0.1", False), ("LW 2", False), ("DIX 0.1", False), ("DID 6", False),
        ("DINO", False), ("BR", False), ("D[AR1,P#2.0]", False), ("1, 0", False),
    ],
)  # fmt: skip
def test_global_target_rule(operand: str, is_global: bool) -> None:
    from plcexport.extractors.s7classic.addresses import is_global_target

    assert is_global_target(operand) is is_global
