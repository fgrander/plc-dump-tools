"""source facts without TIA Portal, the cases of tiadump's ProbeTests."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from plcexport.extractors.tia.facts import parse_project_info, source_facts
from plcexport.extractors.tia.versions import TiaVersion

# ProjectInfo.txt as TIA V21 writes it (Step7.zap21 sample), with Update 4
PROJECT_INFO_V21 = (
    "TiaPortal:\r\n  MinimumRequired:\r\n  - Version: V21.0\r\n"
    "  - TechnicalVersion: 21.00.00.00\r\n"
    "  LastUsed:\r\n  - Version: V21\r\n  - TechnicalVersion: 21.00.04.00\r\n\r\n"
    "UsedProducts:\r\n- Name: STEP 7 Professional\r\n  Version: V21\r\n"
    "  TechnicalVersion: 21.00.00.00\r\n"
    "- Name: STEP 7 Safety\r\n  Version: V21\r\n  TechnicalVersion: 21.00.00.00\r\n\r\n"
    "UsedSupportPackages:\r\n- Name: S7-1500 Motion Control\r\n  Version: V17\r\n"
    "  TechnicalVersion: 17.00.00.00\r\n"
)


def _file(tmp_path: Path, name: str, content: str = "") -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("name", "kind", "major"),
    [
        ("Line3.ap18", "project", 18),
        ("Line3.zap19", "project", 19),
        ("Std.al21", "library", 21),
        ("Std.zal20", "library", 20),
        ("ThreeTank.zap20.zap20", "project", 20),
        ("Line3.als21", "local_session", 21),
    ],
)
def test_kind_and_major_version_from_the_suffix(
    tmp_path: Path, name: str, kind: str, major: int
) -> None:
    facts = source_facts(_file(tmp_path, name))
    assert facts is not None
    assert (facts.kind, facts.saved.major) == (kind, major)


def test_not_a_tia_file_has_no_facts(tmp_path: Path) -> None:
    assert source_facts(_file(tmp_path, "readme.txt")) is None


def test_archive_project_info_gives_update_products_and_support_packages(tmp_path: Path) -> None:
    path = tmp_path / "Line3.zap21"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("ProjectInfo.txt", PROJECT_INFO_V21)
        z.writestr("Line3.ap21", "")
    facts = source_facts(path)
    assert facts is not None
    assert facts.saved == TiaVersion(21, 4)
    assert facts.used_products == (("STEP 7 Professional", "V21"), ("STEP 7 Safety", "V21"))
    assert facts.used_support_packages == (("S7-1500 Motion Control", "V17"),)


def test_project_info_next_to_a_project_file(tmp_path: Path) -> None:
    _file(tmp_path, "ProjectInfo.txt", PROJECT_INFO_V21)
    facts = source_facts(_file(tmp_path, "Line3.ap21"))
    assert facts is not None and facts.saved == TiaVersion(21, 4)
    assert ("STEP 7 Safety", "V21") in facts.used_products


def test_without_project_info_the_lists_are_empty(tmp_path: Path) -> None:
    facts = source_facts(_file(tmp_path, "Line3.zap19", "fixture: tank_v19"))
    assert facts is not None
    assert facts.saved == TiaVersion(19, None)
    assert facts.used_products == () and facts.used_support_packages == ()


def test_update_level_from_the_project_header_when_present(tmp_path: Path) -> None:
    path = _file(tmp_path, "Line3.ap20", "<Project><Version>TIA Portal V20 Update 4</Version>")
    facts = source_facts(path)
    assert facts is not None and facts.saved == TiaVersion(20, 4)


def test_update_level_of_another_version_is_ignored(tmp_path: Path) -> None:
    facts = source_facts(_file(tmp_path, "Line3.ap20", "<Project>created with V19 Update 2"))
    assert facts is not None and facts.saved.update is None


def test_technical_version_without_update_gives_no_update() -> None:
    info = parse_project_info(
        "TiaPortal:\n  LastUsed:\n  - Version: V21\n  - TechnicalVersion: 21.00.00.00\n"
    )
    assert info.last_used_technical_version == "21.00.00.00"
    assert info.update is None


def test_the_reference_sample_lists_its_products() -> None:
    sample = Path("samples/tia-portal/myTiaProject1/myTiaProject1/myTiaProject1.ap21")
    if not sample.is_file():
        pytest.skip("samples/tia-portal/myTiaProject1 is not checked out")
    facts = source_facts(sample)
    assert facts is not None
    assert ("STEP 7 Safety", "V21") in facts.used_products
    assert ("WinCC Basic/Comfort/Advanced", "V11 Update 2") in facts.used_products
