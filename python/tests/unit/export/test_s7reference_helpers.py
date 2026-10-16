"""the independent table reader ignores order numbers of RJ45 port rows."""

from __future__ import annotations

import zipfile
from pathlib import Path

from tests.s7reference import siemens_order_numbers_in_zip


def _row(*cells: str) -> bytes:
    return b"".join(bytes([len(c)]) + c.encode("latin-1") for c in cells) + bytes(2)


def test_port_rows_carry_no_expected_order_number(tmp_path: Path) -> None:
    table = (
        _row("  0", "PN-PN-Coupler", "  0", "PN-PN-Coupler", "6ES7 158-3AD10-0XA0", " ")
        + _row("  X2 P1 R", "Port 1 RJ45", "  X2 P1 R", "Port 1 RJ45", "6ES7 193-6AR00-0AA0", " ")
        + _row("  X2 P2 R", "Port 2 rj45", "  X2 P2 R", "Port 2 rj45", "6ES7 193-6AR00-0AA0", " ")
        + _row("  4", "DI16xDC24V", "  4", "DI16xDC24V", "6ES7 321-1BH02-0AA0", " ")
    )
    archive = tmp_path / "p.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("P/hOmSave7/s7hstatx/1.s7h", table)
    assert siemens_order_numbers_in_zip(archive) == {
        "P/hOmSave7/s7hstatx/1.s7h": {"6ES7 158-3AD10-0XA0", "6ES7 321-1BH02-0AA0"}
    }
