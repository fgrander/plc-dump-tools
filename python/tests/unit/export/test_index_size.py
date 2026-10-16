"""index size and unit splitting."""

from __future__ import annotations

from datetime import UTC, datetime

from plcexport.common import ExtractText
from plcexport.format.canonical import split_front_matter
from plcexport.format.reader import read_files
from plcexport.format.writer import ManifestInfo, render
from plcexport.model import (
    CATEGORIES,
    BodyNetwork,
    CategoryCoverage,
    Coverage,
    ExportModel,
    ExportProject,
    ExportUnit,
    ExportXref,
    UnitBody,
)

INFO = ManifestInfo(
    source_path="synthetic",
    checksum="sha256:" + "0" * 64,
    exported_at=datetime(2026, 10, 7, tzinfo=UTC),
)


def _coverage() -> Coverage:
    cats = {c: CategoryCoverage("unavailable", "not_in_project") for c in CATEGORIES}
    cats["program_units"] = CategoryCoverage("delivered")
    return Coverage(categories=cats)


def _model(n_units: int, networks: int = 1, code_lines: int = 1) -> ExportModel:
    kinds = ["FB", "FC", "OB", "DB"]
    units, bodies, texts = [], {}, []
    for i in range(n_units):
        name = f"Unit_{i:04d}"
        units.append(ExportUnit(name, kinds[i % 4], "LAD", (), number=i))  # type: ignore[arg-type]
        texts.append(ExtractText(name, "title", "de", f"Baustein Nummer {i} der Anlage"))
        bodies[name] = UnitBody(
            "ntn",
            tuple(
                BodyNetwork(
                    no,
                    "\n".join(
                        f'"Q_{no}_{k}" := "I_{no}_{k}" AND NOT "M_{k}";' for k in range(code_lines)
                    ),
                    title={"de": f"Netzwerk {no}"},
                )
                for no in range(1, networks + 1)
            ),
        )
    return ExportModel(
        project=ExportProject("synthetic", "1", "CPU", "Line", "synthetic", "1", ("de",)),
        units=units,
        unit_bodies=bodies,
        texts=texts,
        coverage=_coverage(),
    )


def test_index_of_1000_units_stays_under_50_kb() -> None:
    files = render(_model(1000), INFO)
    index = files["index.md"]
    assert len(index.encode("utf-8")) <= 50 * 1024
    # grouped per kind above the 500-unit threshold
    for kind in ("FB", "FC", "OB", "DB"):
        assert f"units/{kind}/index.md" in files
        assert f"| units/{kind}/index.md |" in index
        assert "| units/FB/Unit_0000.md |" in files["units/FB/index.md"]
    assert "Unit_0001.md" not in index
    assert all(len(line) < 120 for line in index.splitlines())


def test_small_project_lists_units_directly() -> None:
    files = render(_model(10), INFO)
    assert "units/FB/index.md" not in files
    assert "| units/FB/Unit_0000.md |" in files["index.md"]


def test_large_unit_is_split_at_network_boundaries() -> None:
    m = _model(1, networks=60, code_lines=25)  # about 70 KB
    m.xrefs.append(ExportXref("Unit_0000", "variable", '"I_55_3"', "read", 55))
    files = render(m, INFO, split_bytes=40 * 1024)
    parts = sorted(p for p in files if p.startswith("units/FB/Unit_0000.part-"))
    assert len(parts) >= 2
    assert "units/FB/Unit_0000.md" not in files
    seen: list[int] = []
    for i, p in enumerate(parts, 1):
        assert len(files[p].encode("utf-8")) <= 40 * 1024
        fm, _ = split_front_matter(files[p])
        assert fm["part"] == f"{i}/{len(parts)}"
        assert fm["name"] == "Unit_0000"
        seen += [nw["no"] for nw in fm["networks"]]
    assert seen == list(range(1, 61))
    # the reader joins the parts again
    back = read_files(files).model
    assert [n.no for n in back.unit_bodies["Unit_0000"].networks] == list(range(1, 61))
    # an xref line points into the part that holds its network
    (x,) = read_files(files).model.xrefs
    part = read_files(files).network_file["Unit_0000"][55]
    assert '"I_55_3"' in files[part].splitlines()[x.line - 1]  # type: ignore[operator]
