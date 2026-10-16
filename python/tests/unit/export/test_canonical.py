"""canonical serializers are byte-stable; file names are safe and collision-free."""

from __future__ import annotations

from pathlib import Path

import pytest

from plcexport.format.canonical import (
    Flow,
    dump_json,
    file_names,
    front_matter,
    sanitize,
    split_front_matter,
)


def test_json_is_sorted_indented_unicode_with_final_newline() -> None:
    out = dump_json({"b": 1, "a": {"ż": "Rębak", "c": [2, 1]}})
    expected = '{\n  "a": {\n    "c": [\n      2,\n      1\n    ],\n    "ż": "Rębak"\n  },\n'
    assert out == expected + '  "b": 1\n}\n'
    assert "\r" not in out


def test_json_is_independent_of_insertion_order() -> None:
    assert dump_json({"x": 1, "y": 2}) == dump_json({"y": 2, "x": 1})


def test_front_matter_keeps_fixed_key_order_and_flow_items() -> None:
    data = {
        "kind": "FB",
        "name": "FB_Heating",
        "interface": [Flow(name="TempLimit", type="Real", comment={"de": "Maximale Temperatur"})],
        "title": {"de": "Heizplatte", "en": "Heating plate"},
    }
    fm = front_matter(data, ["name", "kind", "title", "interface"])
    assert fm == (
        "---\n"
        "name: FB_Heating\n"
        "kind: FB\n"
        "title:\n"
        "  de: Heizplatte\n"
        "  en: Heating plate\n"
        "interface:\n"
        "- {name: TempLimit, type: Real, comment: {de: Maximale Temperatur}}\n"
        "---\n"
    )
    parsed, body = split_front_matter(fm + "\n# body\n")
    assert parsed["interface"][0]["comment"] == {"de": "Maximale Temperatur"}
    assert body == "\n# body\n"


def test_front_matter_rejects_unknown_keys() -> None:
    with pytest.raises(ValueError, match="fixed order"):
        front_matter({"name": "x", "surprise": 1}, ["name"])


def test_front_matter_never_wraps_long_values() -> None:
    long = "Wert " * 200
    fm = front_matter({"name": "x", "title": {"de": long.strip()}}, ["name", "title"])
    assert fm.count("\n") == 5


def test_front_matter_quotes_ambiguous_scalars() -> None:
    fm = front_matter({"name": "1.2", "kind": "yes"}, ["name", "kind"])
    parsed, _ = split_front_matter(fm)
    assert parsed == {"name": "1.2", "kind": "yes"}


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("FB_Heating", "FB_Heating"),
        ("Rębak_Główny", "Rębak_Główny"),
        ('"DB 10"', "_DB 10_"),
        ("A/B\\C:D", "A_B_C_D"),
        ("trailing.", "trailing"),
        (".hidden", "_hidden"),
        ("CON", "_CON"),
        ("lpt1.txt", "_lpt1.txt"),
        ("", "_"),
    ],
)
def test_sanitize(name: str, expected: str) -> None:
    assert sanitize(name) == expected


def test_safe_names_are_unchanged_and_get_no_suffix() -> None:
    assert file_names(["FB_Heating", "Main"]) == {"FB_Heating": "FB_Heating", "Main": "Main"}


def test_collision_suffixes_only_the_unsafe_name() -> None:
    names = file_names(["A_B", "A/B"])
    assert names["A_B"] == "A_B"
    assert names["A/B"].startswith("A_B-") and len(names["A/B"]) == len("A_B-") + 6


def test_case_insensitive_collision_is_resolved_deterministically() -> None:
    first = file_names(["Motor", "MOTOR"])
    assert first == file_names(["MOTOR", "Motor"])
    assert len({v.casefold() for v in first.values()}) == 2
    assert first["MOTOR"] == "MOTOR"  # first in sort order keeps its name


def test_source_checksum_order_is_case_sensitive_on_every_os(tmp_path: Path) -> None:
    """Windows sorts Paths case-insensitively; the checksum must not depend on that (CI parity)."""
    from plcexport.checksum import _files

    for name in ("F_Guard.txt", "FB_Heating.txt", "a.txt"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    assert [p.name for p in _files(tmp_path)] == ["FB_Heating.txt", "F_Guard.txt", "a.txt"]
