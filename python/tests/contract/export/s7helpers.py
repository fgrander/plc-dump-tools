"""Helpers for the 004 STEP 7 tests: fixture project folders driven by the s7dump stub."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from plcexport.config import get_settings
from tests.conftest import FIXTURES

S7DUMP_FIXTURES = FIXTURES / "s7dump"
STUB = S7DUMP_FIXTURES / "stub_s7dump.py"


def use_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PLCEXPORT_S7DUMP_PATH", str(STUB))
    get_settings.cache_clear()


def make_project(parent: Path, name: str, fixture: str) -> Path:
    """A folder that looks like a STEP 7 project (``<name>.s7p``) and names its dump fixture."""
    d = parent / name
    d.mkdir(parents=True)
    (d / f"{name}.s7p").write_bytes(b"S7P\x00 fixture project header\n")
    (d / "hOmSave7").mkdir()
    (d / "hOmSave7" / "s7hstatx").write_bytes(b"\x01\x02")
    (d / "s7dump.fixture").write_bytes(fixture.encode() + b"\n")  # LF on every OS (checksum)
    return d


def load_dump(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (S7DUMP_FIXTURES / f"{name}.json").read_text(encoding="utf-8")
    )
    return data
