# Platform extractor

Every platform (STEP 7 classic and TIA Portal here; others such as Rockwell, TwinCAT, B&R or
Schneider could follow) implements this protocol in `python/src/plcexport/extractors/<id>/`.

```python
class PlatformExtractor(Protocol):
    id: str                        # "s7classic-direct", "tia"
    version: str                   # bump on any change of output
    platform: str                  # "siemens-step7-classic"
    detection: DetectionRule       # marker globs (+ optional content probe), archive kinds
    supported_versions: VersionSpec
    route: Literal["local", "worker"]
    requires: VendorRequirement | None   # for route=worker: software + version range
    categories: frozenset[Category]      # which of the 7 categories it can deliver
    fallback: str | None                 # extractor id to use when this one gives up

    def probe(self, project_dir: Path) -> ProbeResult:
        """Cheap check: platform version, CPU family, library or multiproject, readable?"""

    def extract(self, project_dir: Path, work_dir: Path, options: ExtractOptions) -> ExportModel:
        """Read a COPY of the project (read-only) and return the model.

        Must not write outside work_dir. Must not raise on unknown content: degrade
        parse_quality and record gaps in coverage instead. Raise NeedsFallback(reason) when the
        result would be unreliable (plausibility checks failed), and a core with a
        `fallback` extractor routes there (`plcexport one` reports the reasons)."""
```

## Rules

1. **Read-only**: `project_dir` is a copy, but extractors must still treat it as read-only.
2. **No file writing**: the core serializes the returned `ExportModel`.
3. **Determinism**: the same input must produce an equal model. Lists are sorted by stable keys.
4. **Coverage**: every one of the 7 categories must be stated. Unsupported means `unavailable`
   with reason `unsupported`.
5. **Fallback**: `NeedsFallback` is the only accepted way to request the other route. The
   manifest records both extractor ids and the reason.
6. **Worker extractors** (route `worker`) run on another host with the vendor software, with the
   same signature; this repository has no worker host, so `plcexport one` only runs `local`
   extractors.

## Conformance suite (required to merge an extractor)

| # | Test | Pass criterion |
|---|---|---|
| E1 | Golden export of each reference project | Equal to the stored golden export (byte-exact, except `exported_at`) |
| E2 | Validation | `plcexport validate` passes |
| E3 | Determinism | Two runs produce byte-identical files |
| E4 | Robustness | Truncated or corrupt input gives `partial` or `failed` with a reason, never an exception that escapes |
| E5 | Read-only | Source checksum is unchanged after extraction |
| E7 | Route equivalence (if `fallback` is set) | Models of both routes are equal in meaning on the reference projects |
