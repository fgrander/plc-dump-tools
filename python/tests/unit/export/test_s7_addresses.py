"""STEP 7 operand normalization."""

from __future__ import annotations

import pytest

from plcexport.extractors.s7classic.addresses import area, collapse, io_direction, normalize


@pytest.mark.parametrize(
    ("operand", "key"),
    [
        ("I 0.0", "I0.0"),
        ("E 0.0", "I0.0"),
        ("e0.0", "I0.0"),
        ("Q      4.2", "Q4.2"),
        ("A 4.2", "Q4.2"),
        ("PIW 256", "PIW256"),
        ("PEW 256", "PIW256"),
        ("PAW 512", "PQW512"),
        ("MW 20", "MW20"),
        ("MD    10", "MD10"),
        ("T 5", "T5"),
        ("C 3", "C3"),
        ("Z 3", "C3"),
        ("DB20.DBW    4", "DB20.DBW4"),
        ("DB10.DBX 2.0", "DB10.DBX2.0"),
        ("DBX 2.0", "DBX2.0"),
        ("DB 20", "DB20"),
        ("FB 10", "FB10"),
        ('"I_Start"', '"I_Start"'),
        ("#TempActual", "#TempActual"),
    ],
)
def test_normalize(operand: str, key: str) -> None:
    assert normalize(operand) == key


@pytest.mark.parametrize(
    ("operand", "expected"),
    [
        ("I 0.0", "input"),
        ("PEW 256", "input"),
        ("A 4.0", "output"),
        ("PQW 512", "output"),
        ("M 10.0", "memory"),
        ("L 0.0", "local"),
        ("#t", "local"),
        ("T 5", "timer"),
        ("Z 3", "counter"),
        ("DB20.DBW 4", "db"),
        ("FC 5", "block"),
        ('"Q_Pump"', "symbol"),
        ("S5T#5S", "other"),
        ("100", "other"),
    ],
)
def test_area(operand: str, expected: str) -> None:
    assert area(operand) == expected


def test_io_direction_and_collapse() -> None:
    assert io_direction("I 0.0") == "input"
    assert io_direction("Q 4.1") == "output"
    assert io_direction("M 10.0") == "memory"
    assert io_direction("DB20.DBW 4") is None
    assert io_direction(None) is None
    assert collapse("Q      4.2") == "Q 4.2"
