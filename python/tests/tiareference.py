"""real TIA Portal sample projects and libraries for the ``tiareference`` tests.

Archives and project folders live in ``samples/tia-portal/`` (git-ignored;
``TIADUMP_SAMPLES_DIR`` overrides it). They are only used on the TIA host: the tests open
copies with ``tiadump`` and TIA Portal Openness.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.conftest import TIA_SAMPLES

# .ap19 .zap20 .al21 .zal21 ...; downloads sometimes double the suffix (x.zap20.zap20)
TIA_SUFFIX = re.compile(r"\.(z?ap|z?al)(\d\d)$", re.IGNORECASE)


def tia_major(path: Path) -> int | None:
    """Major TIA version from the file suffix (``.zap19`` → 19), or None."""
    match = TIA_SUFFIX.search(path.name)
    return int(match.group(2)) if match else None


def is_library(path: Path) -> bool:
    match = TIA_SUFFIX.search(path.name)
    return bool(match and match.group(1).lower().endswith("al"))


def reference_projects(root: Path | None = None, *, libraries: bool = False) -> list[Path]:
    """TIA projects (or, with ``libraries=True``, global libraries) below ``root``."""
    root = root or TIA_SAMPLES
    if not root.is_dir():
        return []
    found = [p for p in root.rglob("*") if p.is_file() and TIA_SUFFIX.search(p.name)]
    return sorted(p for p in found if is_library(p) == libraries)


@pytest.fixture
def tia_reference_projects() -> list[Path]:
    projects = reference_projects()
    if not projects:
        pytest.skip("no TIA Portal sample projects in samples/tia-portal")
    return projects


@pytest.fixture
def tia_reference_libraries() -> list[Path]:
    libraries = reference_projects(libraries=True)
    if not libraries:
        pytest.skip("no TIA Portal global libraries in samples/tia-portal")
    return libraries
