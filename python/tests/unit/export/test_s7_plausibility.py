"""plausibility checks route unreliable dumps to the fallback."""

from __future__ import annotations

import copy

from plcexport.extractors.s7classic.direct import plausibility
from plcexport.extractors.s7classic.mapping import MappingOptions, to_model
from tests.contract.export.s7helpers import load_dump


def test_clean_dump_passes() -> None:
    assert plausibility(load_dump("press_s7300"), set()) == []


def test_decoding_error_fails_naming_the_block() -> None:
    problems = plausibility(load_dump("decode_error"), set())
    assert any("FC5" in p and "MC7 decoding failed" in p for p in problems)


def test_catalog_mismatch_fails_with_counts() -> None:
    assert plausibility(load_dump("catalog_mismatch"), set()) == [
        "S7 Program(1): 9 of 10 blocks decoded"
    ]


def test_code_block_without_networks_fails() -> None:
    d = load_dump("press_s7300")
    fc = next(b for b in d["programs"][0]["blocks"] if b["symbolic_name"] == "FC_Scale")
    fc["networks"] = []
    assert plausibility(d, set()) == ["S7 Program(1)/FC5: MC7 code of 120 bytes but no networks"]


def test_implausibly_large_stl_fails() -> None:
    d = load_dump("press_s7300")
    fc = next(b for b in d["programs"][0]["blocks"] if b["symbolic_name"] == "FC_Scale")
    fc["mc7_size"] = 1
    assert "implausibly large" in plausibility(d, set())[0]


def test_protected_blocks_are_not_checked_for_networks() -> None:
    assert plausibility(load_dump("all_protected"), set()) == []


def test_symbol_count_mismatch_fails() -> None:
    d = load_dump("press_s7300")
    d["programs"][0]["catalog"]["symbols"] += 2
    assert "symbols read" in plausibility(d, set())[0]


def test_extra_languages_only_fail_when_configured() -> None:
    d = copy.deepcopy(load_dump("press_s7300"))
    d["project"]["languages"] = {"stored": "de", "maintained": ["de", "en"]}
    assert plausibility(d, set()) == []
    assert "comment languages en" in plausibility(d, {"languages"})[0]
    gaps = to_model(d, MappingOptions("x", "1")).coverage.gaps
    assert any(g.reason == "other:additional comment languages need the worker route"
               for g in gaps)  # fmt: skip


def test_empty_block_with_only_be_is_fine() -> None:
    """Real case (snap7 example): an empty OB1 has 2 bytes of MC7 and no networks."""
    d = load_dump("press_s7300")
    ob = next(b for b in d["programs"][0]["blocks"] if b["symbolic_name"] == "Main")
    ob["networks"], ob["mc7_size"] = [], 2
    assert plausibility(d, set()) == []


def test_commented_out_statements_are_not_code() -> None:
    """Real case (Deutschmann and plcs.net samples): a block whose statements are all
    commented out compiles to BE alone (2 bytes), while its networks keep the text."""
    d = load_dump("press_s7300")
    ob = next(b for b in d["programs"][0]["blocks"] if b["symbolic_name"] == "Main")
    ob["mc7_size"] = 2
    ob["networks"] = [
        {**ob["networks"][0], "stl": ["//      CALL  FB   125 , DB125", "//       RESET :="] * 20}
    ]
    assert plausibility(d, set()) == []
    ob["networks"][0]["stl"] = [
        '      L     "Speed"   // a comment after code',
        "      T     MW 20",
    ] * 20
    assert "implausibly large" in plausibility(d, set())[0]
