"""model additions for TIA."""

from __future__ import annotations

import pytest

from plcexport.model import (
    ExportBundle,
    ExportModel,
    ExportProject,
    LibraryLink,
    LibraryModel,
    LibraryType,
    LibraryValidationError,
    NativePart,
    TypeVersion,
    Upgrade,
    as_bundle,
    validate_library,
    version_key,
)


def _project(**kw: object) -> ExportProject:
    return ExportProject("siemens-tia", "V21", "CPU 1516", None, "tia", "1.0.0", **kw)  # type: ignore[arg-type]


def test_project_kind_defaults_to_project_and_device_to_none() -> None:
    p = _project()
    assert p.kind == "project"
    assert p.device is None


def test_upgrade_messages_default_empty() -> None:
    assert Upgrade("V19", "V21", "TIA Portal V21").messages == ()


def test_native_part_sorts_files_by_path() -> None:
    part = NativePart("siemens-simatic-sd", "sd", {"b/x.s7dcl": b"2", "a/y.s7res": b"1"})
    assert list(part.sorted().files) == ["a/y.s7res", "b/x.s7dcl"]


def test_bundle_wraps_a_single_model() -> None:
    m = ExportModel(project=_project())
    bundle = as_bundle(m)
    assert isinstance(bundle, ExportBundle)
    assert bundle.models == [m]
    assert as_bundle(bundle) is bundle


@pytest.mark.parametrize(
    ("versions", "expected"),
    [
        (["1.10.0", "1.9.0", "1.2.0"], ["1.2.0", "1.9.0", "1.10.0"]),
        (["2.0", "1.0.1", "1.0"], ["1.0", "1.0.1", "2.0"]),
        (["1.0.0", "V1.0.1", "1.0.0-beta"], ["1.0.0", "1.0.0-beta", "V1.0.1"]),
    ],
)
def test_version_key_orders_numerically(versions: list[str], expected: list[str]) -> None:
    assert sorted(versions, key=version_key) == expected


def _version(
    v: str, status: str = "released", part: str = "sd", gap: str | None = None
) -> TypeVersion:
    return TypeVersion(
        version=v,
        status=status,  # type: ignore[arg-type]
        author=None,
        date=None,
        comment={},
        content_part=part,  # type: ignore[arg-type]
        content_path=None if part == "none" else f"sd/T/{v}/T.s7dcl",
        gap_reason=gap,
    )


def _library(
    types: tuple[LibraryType, ...], kind: str = "global", company: bool = True
) -> LibraryModel:
    return LibraryModel(name="ACME", version=None, kind=kind, company=company, types=types)  # type: ignore[arg-type]


def test_library_sorted_orders_versions_numerically() -> None:
    lib = _library(
        (LibraryType("Conveyor", "Types", "plc_block", (_version("1.10.0"), _version("1.9.0"))),)
    )
    assert [v.version for v in lib.sorted().types[0].versions] == ["1.9.0", "1.10.0"]


def test_library_version_strings_unique_per_type() -> None:
    lib = _library(
        (LibraryType("Conveyor", "Types", "plc_block", (_version("1.0"), _version("1.0"))),)
    )
    with pytest.raises(LibraryValidationError, match="version strings unique per type"):
        validate_library(lib)


def test_released_version_needs_content_or_gap_reason() -> None:
    bad = _library(
        (LibraryType("Conveyor", "Types", "plc_block", (_version("1.0", part="none"),)),)
    )
    with pytest.raises(LibraryValidationError, match="must have content or a gap reason"):
        validate_library(bad)
    ok = _library(
        (
            LibraryType(
                "Conveyor", "Types", "plc_block", (_version("1.0", part="none", gap="protected"),)
            ),
        )
    )
    validate_library(ok)
    in_work = _library(
        (LibraryType("Conveyor", "Types", "plc_block", (_version("1.1", "in_work", "none"),)),)
    )
    validate_library(in_work)


def test_company_only_on_global_libraries() -> None:
    with pytest.raises(LibraryValidationError, match='only on kind="global"'):
        validate_library(_library((), kind="project", company=True))


def test_model_sorted_sorts_links_and_native_parts() -> None:
    m = ExportModel(
        project=_project(),
        native_parts=[NativePart("siemens-simatic-sd", "sd", {"z.s7dcl": b"", "a.s7dcl": b""})],
        library_links=[
            LibraryLink("FB_b", "unit", "B", "Types", "1.0", "released", None),
            LibraryLink("FB_a", "unit", "A", "Types", "1.0", "released", None),
        ],
    )
    s = m.sorted()
    assert [link.object for link in s.library_links] == ["FB_a", "FB_b"]
    assert list(s.native_parts[0].files) == ["a.s7dcl", "z.s7dcl"]
