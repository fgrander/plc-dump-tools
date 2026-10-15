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

## Read-only

Neither tool writes to a project, connects to a PLC or opens a network connection.

- `s7dump` opens project files for reading only and writes nothing but its `--out` file.
- `tiadump` only opens a **copy** of the project in its `--work` folder. It never saves,
  downloads, goes online or imports. It compiles only units of that working copy that cannot be
  exported otherwise. [`ForbiddenApiTests`](tiadump/tests/tiadump.Tests/ForbiddenApiTests.cs) fails
  the build if the code calls such an API.

## Output format

| Document | Schema |
|---|---|
| [`docs/s7dump-json.md`](docs/s7dump-json.md), [`docs/s7dump-connections.md`](docs/s7dump-connections.md) | [`schema/s7dump.schema.json`](schema/s7dump.schema.json) |
| [`docs/tiadump.md`](docs/tiadump.md), [`docs/tiadump-connections.md`](docs/tiadump-connections.md), [`docs/tiadump-installed.md`](docs/tiadump-installed.md) | [`schema/tiadump.schema.json`](schema/tiadump.schema.json) |

## Tests with real projects

Tests that need real projects look for them in `samples/s7classic` (STEP 7 V5.x projects
zipped) and `samples/tia-portal` (TIA Portal projects) in the repository root, or in the folders
named by `S7DUMP_SAMPLES_DIR` and `TIADUMP_SAMPLES_DIR`. Without samples those tests are skipped.
`samples/` is ignored by git.

## License

[LGPL-2.1](LICENSE). `s7dump` uses
[DotNetSiemensPLCToolBoxLibrary](https://github.com/dotnetprojects/DotNetSiemensPLCToolBoxLibrary)
(LGPL-2.1). `tiadump` references the TIA Portal Openness assemblies of the local TIA Portal
installation; they are not part of this repository and are never copied into the build output.

SIMATIC, STEP 7 and TIA Portal are trademarks of Siemens AG. This project is not affiliated with
or endorsed by Siemens.
