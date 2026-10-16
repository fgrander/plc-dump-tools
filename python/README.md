# plcexport

Turns the output of [`s7dump`](../s7dump/) and [`tiadump`](../tiadump/) into the **common export
format**: one folder per PLC with `manifest.json`, `coverage.json`, `symbols.json`, `io.json`,
`hardware.json`, `xref.json`, `structure.json`, optional `connections.json`, one Markdown file
per program unit with YAML front matter, and for TIA Portal the native SIMATIC SD files
(`.s7dcl`/`.s7res`). Graphical logic is written as Network Text Notation; SimaticML exports
from TIA Portal are converted the same way.

The format is described in [`docs/common-format.md`](../docs/common-format.md) and the documents
next to it; its JSON Schemas are in [`src/plcexport/schemas/`](src/plcexport/schemas/).

## Use

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
cd python
uv sync
uv run plcexport one <project folder or .zapNN/.zalNN> --out <export folder>
uv run plcexport validate <export folder>
```

`plcexport one` copies the source to a temporary folder, runs the matching extractor on the copy,
validates the result and writes the export folder. The source is only read; its checksum is
compared before and after.

| Extractor | Sources | Runs |
|---|---|---|
| `s7classic-direct` | STEP 7 V5.x project folders (`.s7p`), libraries (`.s7l`), multiprojects | `s7dump` (Linux or Windows) |
| `tia` | TIA Portal projects and libraries (`.apNN`, `.zapNN`, `.alNN`, `.zalNN`) | `tiadump`, only on a Windows host with TIA Portal and Openness |

A TIA project gives one export folder per PLC below `--out`, plus `_project` for the hardware
and HMI devices that belong to no single PLC.

## Settings

Environment variables (or a `.env` file in the working folder):

| Variable | Default | Meaning |
|---|---|---|
| `PLCEXPORT_S7DUMP_PATH` | `s7dump/publish/<win-x64\|linux-x64>/s7dump[.exe]` in this repository | the `s7dump` binary |
| `PLCEXPORT_S7_MNEMONIC` | `en` | STL mnemonic, `en` or `de` |
| `PLCEXPORT_S7_TEXT_LANGUAGE` | `de` | language of comments when the project does not say |
| `PLCEXPORT_S7DUMP_TIMEOUT_S` | `600` | |
| `PLCEXPORT_TIADUMP_PATH` | `tiadump/publish/tiadump.exe` in this repository | the `tiadump` binary |
| `PLCEXPORT_TIADUMP_PATHS` | `{}` | one build per TIA major, e.g. `{"V20": "C:/tiadump-v20/tiadump.exe"}` |
| `PLCEXPORT_TIA_VERSION` | `auto` | TIA Portal to use: `auto` (newest installed), `none`, or e.g. `V21` |
| `PLCEXPORT_TIA_TIMEOUT_S` | `1800` | |
| `PLCEXPORT_TIA_WORK_ROOT` | `C:/tiaw` | short work folder; TIA refuses project paths over 143 characters |
| `PLCEXPORT_TIA_LIBRARIES_FILE` | none | YAML file `company_libraries: [{name, path}]`: the libraries that count as company libraries |

## Tests

```bash
uv run pytest
```

The tests run on recorded `s7dump`/`tiadump` output in `tests/fixtures/` and compare against the
golden exports in `tests/fixtures/golden/export/` (`PLCEXPORT_UPDATE_GOLDEN=1` rewrites them).
Tests that need real projects or TIA Portal are skipped without them (see the repository README).
