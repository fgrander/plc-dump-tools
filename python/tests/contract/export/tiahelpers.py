"""Helpers for the 005 TIA tests: source files driven by the ``tiadump`` stub (like 004's
``s7helpers``)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from plcexport.config import get_settings
from tests.conftest import FIXTURES

TIADUMP_FIXTURES = FIXTURES / "tiadump"
STUB = TIADUMP_FIXTURES / "stub_tiadump.py"


def use_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PLCEXPORT_TIADUMP_PATH", str(STUB))
    get_settings.cache_clear()


def make_project(parent: Path, file_name: str, fixture: str) -> Path:
    """A single-file TIA source (e.g. ``Line3.zap21``) whose content names its dump fixture
    (or ``exit:<n>``)."""
    parent.mkdir(parents=True, exist_ok=True)
    path = parent / file_name
    path.write_bytes(f"fixture: {fixture}\n".encode())  # LF on every OS (checksum)
    return path


def load_dump(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (TIADUMP_FIXTURES / name / "dump.json").read_text(encoding="utf-8")
    )
    return data
