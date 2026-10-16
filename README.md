# plc-dump-tools

Two read-only command line tools that turn Siemens PLC projects into JSON, so other programs
(search, documentation, diffing, analysis) can work with them without the engineering software:

| Tool | Reads | Needs | Runs on |
|---|---|---|---|
| [`s7dump`](s7dump/) | STEP 7 V5.x projects and libraries (`.s7p`, `.s7l`) | nothing: no STEP 7 installation | .NET 8, Linux and Windows |
| [`tiadump`](tiadump/) | TIA Portal projects and global libraries (`.apNN`, `.zapNN`, `.alNN`, `.zalNN`) | an installed TIA Portal V20 Upd4+ with Openness | .NET Framework 4.8, Windows x64 |

Both dump blocks, interfaces, symbols/tags, hardware configuration with I/O addresses, networks,
and configured connections (with TSAPs) and communication block calls. `tiadump` also dumps HMI
devices, alarms, safety signatures and library types.

[`plcexport`](python/) (Python) turns those dumps into the **common export format**: per PLC a
folder of JSON tables (symbols, I/O, hardware, cross references, connections), one Markdown file
per program unit, and for TIA Portal the SIMATIC SD files, ready to be committed to a git
repository and read by people and LLM agents ([`docs/common-format.md`](docs/common-format.md)):

```bash
cd python && uv sync
uv run plcexport one <project> --out <export folder>
```

## Read-only

Neither tool writes to a project, connects to a PLC or opens a network connection.

- `s7dump` opens project files for reading only and writes nothing but its `--out` file.
- `tiadump` only opens a **copy** of the project in its `--work` folder. It never saves,
  downloads, goes online or imports. It compiles only units of that working copy that cannot be
  exported otherwise. [`ForbiddenApiTests`](tiadump/tests/tiadump.Tests/ForbiddenApiTests.cs) fails
  the build if the code calls such an API.

## Formats

The common export format: [`common-format.md`](docs/common-format.md), with
[`common-format-tia.md`](docs/common-format-tia.md), [`connections-json.md`](docs/connections-json.md),
[`connections-json-tia.md`](docs/connections-json-tia.md),
[`udt-member-offsets.md`](docs/udt-member-offsets.md) and
[`stl-xref-rules.md`](docs/stl-xref-rules.md); extractors follow
[`extractor-contract.md`](docs/extractor-contract.md).

The dump formats of the two tools:

| Document | Schema |
|---|---|
| [`docs/s7dump-json.md`](docs/s7dump-json.md), [`docs/s7dump-connections.md`](docs/s7dump-connections.md) | [`s7classic/dump_schema.json`](python/src/plcexport/extractors/s7classic/dump_schema.json) |
| [`docs/tiadump.md`](docs/tiadump.md), [`docs/tiadump-connections.md`](docs/tiadump-connections.md), [`docs/tiadump-installed.md`](docs/tiadump-installed.md) | [`tia/dump_schema.json`](python/src/plcexport/extractors/tia/dump_schema.json) |

## Tests with real projects

Tests that need real projects look for them in `samples/s7classic` (STEP 7 V5.x projects
zipped) and `samples/tia-portal` (TIA Portal projects) in the repository root, or in the folders
named by `S7DUMP_SAMPLES_DIR` and `TIADUMP_SAMPLES_DIR`. Without samples those tests are skipped.
`samples/` is ignored by git; the sample projects in it and their `plcexport one` results in
`samples/exports/` are force-added (`git add -f`).

## License

[LGPL-2.1](LICENSE), for all parts. `s7dump` uses
[DotNetSiemensPLCToolBoxLibrary](https://github.com/dotnetprojects/DotNetSiemensPLCToolBoxLibrary)
(LGPL-2.1). `tiadump` references the TIA Portal Openness assemblies of the local TIA Portal
installation; they are not part of this repository and are never copied into the build output.

SIMATIC, STEP 7 and TIA Portal are trademarks of Siemens AG. This project is not affiliated with
or endorsed by Siemens.
