"""product needs and whether an installation covers them."""

from __future__ import annotations

from plcexport.extractors.tia.needs import covers, expand, needs_from, normalize, uncovered


def test_normalize_drops_the_version_and_case() -> None:
    assert normalize("STEP 7 Safety V21") == "step 7 safety"
    assert normalize("WinCC Basic/Comfort/Advanced V11 Update 2") == "wincc basic/comfort/advanced"
    assert normalize("SINAMICS Startdrive V20 SP1") == "sinamics startdrive"
    assert normalize("  S7-1500 Motion   Control V17 Upd3 ") == "s7-1500 motion control"
    assert normalize("STEP 7 Safety") == "step 7 safety"


def test_bundles_expand_like_tiadump() -> None:
    assert expand("WinCC Basic/Comfort/Advanced V21") == {
        "wincc basic/comfort/advanced", "wincc basic", "wincc comfort", "wincc advanced",
    }  # fmt: skip


def test_the_engineering_base_is_never_a_need() -> None:
    rows = [
        ("STEP 7 Professional", "V21"),
        ("Totally Integrated Automation Portal", "V21"),
        ("STEP 7 Safety", "V21"),
        {"name": "SINAMICS Startdrive V20"},
        "STEP 7 Safety V21",
    ]
    assert needs_from(rows) == ["sinamics startdrive", "step 7 safety"]


def test_cover_by_name_whatever_the_version() -> None:
    packages = [
        {"name": "STEP 7 Professional", "version": "V21"},
        {"name": "STEP 7 Safety", "version": "V21"},
        {"name": "WinCC Basic/Comfort/Advanced", "version": "V21"},
    ]
    assert covers(packages, ["step 7 safety", "WinCC Comfort V20"])
    assert covers(packages, [])
    assert uncovered(packages, ["sinamics startdrive", "step 7 safety"]) == ["sinamics startdrive"]
    assert not covers([], ["step 7 safety"])
    assert covers([], ["STEP 7 Professional V20"])  # the base is always there
