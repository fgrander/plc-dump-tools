"""Test helpers shared by unit, contract and integration tests."""

from __future__ import annotations

import os
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FIXTURE_REPO = FIXTURES / "repo"
REPO_ROOT = Path(__file__).resolve().parents[2]
# real projects for the reference tests, shared with the C# tests (git-ignored)
S7_SAMPLES = Path(os.environ.get("S7DUMP_SAMPLES_DIR") or REPO_ROOT / "samples" / "s7classic")
TIA_SAMPLES = Path(os.environ.get("TIADUMP_SAMPLES_DIR") or REPO_ROOT / "samples" / "tia-portal")
