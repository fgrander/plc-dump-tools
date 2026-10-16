"""version handling of TIA sources."""

from __future__ import annotations

from pathlib import Path

import pytest

from plcexport.extractors.tia.versions import (
    TiaVersion,
    handling,
    saved_major,
    source_kind,
    unsupported_reason,
)

HOST = TiaVersion(21, 1)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("V19", TiaVersion(19)),
        ("V20 Upd4", TiaVersion(20, 4)),
        ("V21 Update 2", TiaVersion(21, 2)),
        ("21", TiaVersion(21)),
        ("v20.0 upd 3", TiaVersion(20, 3)),
    ],
)
def test_parse(text: str, expected: TiaVersion) -> None:
    assert TiaVersion.parse(text) == expected


def test_parse_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        TiaVersion.parse("TIA Portal")


def test_str() -> None:
    assert str(TiaVersion(20, 4)) == "V20 Upd4" and str(TiaVersion(19)) == "V19"


@pytest.mark.parametrize(
    ("name", "kind", "major"),
    [
        ("Line3.zap19", "project", 19),
        ("Line3.ap21", "project", 21),
        ("Std.al20", "library", 20),
        ("Std.zal21", "library", 21),
        ("Line3.als21", "local_session", 21),
        ("ThreeTank.zap20.zap20", "project", 20),
        ("readme.txt", None, None),
    ],
)
def test_kind_and_major_from_suffix(name: str, kind: str | None, major: int | None) -> None:
    assert source_kind(Path(name)) == kind
    assert saved_major(Path(name)) == major


@pytest.mark.parametrize(
    ("name", "saved", "expected"),
    [
        ("Line3.zap19", None, "upgrade"),
        ("Line3.ap21", None, "open"),
        ("Line3.ap21", TiaVersion(21, 1), "open"),
        ("Line3.ap21", TiaVersion(21, 2), "newer_than_host"),
        ("Line3.ap22", None, "newer_than_host"),
        ("Std.al18", None, "upgrade"),
        ("Line3.als21", None, "local_session"),
    ],
)
def test_handling(name: str, saved: TiaVersion | None, expected: str) -> None:
    assert handling(Path(name), HOST, saved) == expected


def test_reasons() -> None:
    assert unsupported_reason("newer_than_host", Path("L.ap22"), HOST) == (
        "unsupported version: L.ap22 is newer than TIA Portal V21 Upd1 on this host"
    )
    assert unsupported_reason("local_session", Path("L.als21"), HOST) == (
        "multiuser local session – export the server project"
    )
    assert unsupported_reason("upgrade", Path("L.zap19"), HOST) is None
