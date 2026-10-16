"""Export one project folder: copy -> extract -> validate -> write.

The source is only read: it is copied into a temporary work area first, the extractor sees only
the copy, and the source checksum is compared before and after.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import structlog

from plcexport.checksum import source_checksum
from plcexport.extractors.base import ExtractOptions, ExtractRefused, PlatformExtractor
from plcexport.extractors.registry import ExtractorRegistry, default_extractors
from plcexport.format.validate import ExportInvalid, validate_model
from plcexport.format.writer import ManifestInfo, OutputPathTooLong, render, write_atomic
from plcexport.model import ExportModel, as_bundle

log = structlog.get_logger(__name__)

Status = Literal["exported", "partial", "unsupported", "locked", "no_capable_worker", "failed"]


@dataclass
class ExportResult:
    status: Status
    out: Path
    extractor: str | None = None
    reason: str | None = None
    violations: list[str] = field(default_factory=list)
    devices: list[str] = field(default_factory=list)  # one folder per PLC device


def _status(m: ExportModel) -> Status:
    return "partial" if m.is_damaged() else "exported"


def _pick(
    registry: ExtractorRegistry, project_dir: Path, extractor_id: str | None
) -> PlatformExtractor | None:
    if extractor_id:
        return registry.get(extractor_id)
    hits = (
        registry.match_file(project_dir.name)  # single-file sources (.zap21)
        if project_dir.is_file()
        else registry.matching(project_dir)
    )
    local = [e for e in hits if e.route == "local"]
    return local[0] if local else None


def export_project(
    project_dir: Path,
    out: Path,
    extractor_id: str | None = None,
    registry: ExtractorRegistry | None = None,
    options: ExtractOptions | None = None,
    group_threshold: int = 500,
    now: datetime | None = None,
) -> ExportResult:
    registry = registry or default_extractors()
    options = options or ExtractOptions(extra={"source_path": str(project_dir)})
    extractor = _pick(registry, project_dir, extractor_id)
    if extractor is None:
        return ExportResult("unsupported", out, reason="no local extractor detects this project")
    bound = log.bind(project=str(project_dir), extractor=extractor.id)

    before = source_checksum(project_dir)
    with tempfile.TemporaryDirectory(prefix="plcexport-") as td:
        copy = Path(td) / "src" / project_dir.name
        if project_dir.is_file():  # single-file sources such as TIA archives
            copy.parent.mkdir(parents=True)
            shutil.copy2(project_dir, copy)
        else:
            shutil.copytree(project_dir, copy)
        work = Path(td) / "work"
        work.mkdir()
        probe = extractor.probe(copy)
        if not probe.readable:
            bound.warning("export.probe_failed", reason=probe.reason)
            return ExportResult("failed", out, extractor.id, reason=probe.reason or "unreadable")
        try:
            models = as_bundle(extractor.extract(copy, work, options)).models
        except ExtractRefused as exc:  # newer than the host, locked, …
            bound.warning("export.refused", status=exc.status, reason=exc.reason)
            return ExportResult(exc.status, out, extractor.id, reason=exc.reason)
        except Exception as exc:  # an extractor must not take the exporter down
            bound.exception("export.extract_failed")
            return ExportResult("failed", out, extractor.id, reason=f"extractor error: {exc}")

    single = len(models) == 1
    violations = [
        v if single else f"{m.project.device}: {v}" for m in models for v in validate_model(m)
    ]
    if violations:
        bound.warning("export.invalid_model", violations=violations[:20])
        return ExportResult(
            "failed",
            out,
            extractor.id,
            reason=str(ExportInvalid(violations)),
            violations=violations,
        )
    info = ManifestInfo(
        source_path=project_dir.name,  # never an absolute local path
        checksum=before,
        exported_at=now or datetime.now(UTC),
        route=extractor.route,
    )
    rendered = [
        (m, out if single else out / (m.project.device or f"device_{i}"),
         render(m, info, options.unit_split_bytes, group_threshold))
        for i, m in enumerate(models)
    ]  # fmt: skip
    if source_checksum(project_dir) != before:
        return ExportResult("failed", out, extractor.id, reason="source changed during export")
    try:
        for _, target, files in rendered:
            write_atomic(files, target)
    except ExportInvalid as exc:
        bound.warning("export.invalid_files", violations=exc.violations[:20])
        return ExportResult("failed", out, extractor.id, reason=str(exc), violations=exc.violations)
    except OutputPathTooLong as exc:
        bound.warning("export.output_path_too_long", reason=str(exc))
        return ExportResult("failed", out, extractor.id, reason=str(exc))
    status: Status = "partial" if any(_status(m) == "partial" for m in models) else "exported"
    bound.info("export.done", status=status, out=str(out), devices=len(models))
    devices = [] if single else [m.project.device or "" for m in models]
    return ExportResult(status, out, extractor.id, devices=devices)
