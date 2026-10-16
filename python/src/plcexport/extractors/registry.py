"""Extractor registry; platform features add their extractor here."""

from __future__ import annotations

import fnmatch
from collections.abc import Iterable
from pathlib import Path

from plcexport.extractors.base import PlatformExtractor


class ExtractorRegistry:
    def __init__(self, extractors: Iterable[PlatformExtractor]) -> None:
        self.extractors: dict[str, PlatformExtractor] = {}
        for e in extractors:
            if e.id in self.extractors:
                raise ValueError(f"duplicate extractor id {e.id!r}")
            self.extractors[e.id] = e

    def get(self, extractor_id: str) -> PlatformExtractor:
        try:
            return self.extractors[extractor_id]
        except KeyError:
            raise KeyError(f"unknown extractor {extractor_id!r}") from None

    def match_names(
        self, names: Iterable[str], probe_dir: Path | None = None
    ) -> list[PlatformExtractor]:
        """Extractors whose detection markers match one of ``names`` (files of one folder).

        The optional content probe runs only when the folder exists on disk (``probe_dir``).
        Local routes come first; then rules whose markers all matched, then the rule
        with more matching markers.
        """
        # Case does not count: old STEP 7 versions write ``PROJECT.S7P``, and a file system
        # that ignores case would find it under either spelling.
        names = [n.lower() for n in names]
        hits: list[tuple[int, PlatformExtractor]] = []
        for e in self.extractors.values():
            rule = e.detection
            matched = sum(
                1 for m in rule.markers if any(fnmatch.fnmatchcase(n, m.lower()) for n in names)
            )
            if not matched:
                continue
            probe = rule.content_probe
            if probe_dir is not None and probe is not None and not probe(probe_dir):
                continue
            hits.append((matched, e))
        hits.sort(
            key=lambda h: (
                h[1].route != "local",
                h[0] < len(h[1].detection.markers),  # rules matched completely first
                -h[0],
                h[1].id,
            )
        )
        return [e for _, e in hits]

    def match_file(self, name: str) -> list[PlatformExtractor]:
        """extractors for which the file ``name`` is a project of its own (local first)."""
        hits = [
            e
            for e in self.extractors.values()
            if any(fnmatch.fnmatchcase(name, m) for m in e.detection.file_markers)
        ]
        return sorted(hits, key=lambda e: (e.route != "local", e.id))

    def matching(self, project_dir: Path) -> list[PlatformExtractor]:
        """Extractors whose detection rule claims ``project_dir``."""
        if not project_dir.is_dir():
            return []
        return self.match_names((p.name for p in project_dir.iterdir()), project_dir)


def default_extractors() -> ExtractorRegistry:
    from plcexport.extractors.s7classic.direct import (
        S7ClassicDirectExtractor,
        S7ClassicMultiproject,
    )
    from plcexport.extractors.tia.extractor import TiaExtractor

    return ExtractorRegistry([S7ClassicDirectExtractor(), S7ClassicMultiproject(), TiaExtractor()])
