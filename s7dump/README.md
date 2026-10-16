# s7dump

Reads a Siemens STEP 7 V5.x project (`.s7p`, library `.s7l`) **without STEP 7** and writes one
JSON document (format: [`docs/s7dump-json.md`](../docs/s7dump-json.md), schema:
[`s7classic/dump_schema.json`](../python/src/plcexport/extractors/s7classic/dump_schema.json)). It only reads; it never writes
anything but its `--out` file, and it never connects to a PLC.

```text
s7dump <project.s7p | project.s7l | project folder> --out dump.json [--mnemonic en|de] [--no-sources]
```

Exit codes: `0` JSON written (it may list `errors`), `2` project cannot be opened, `64` usage.

## Build

With the .NET 8 SDK, from the repository root:

```bash
dotnet publish s7dump -c Release -r linux-x64 --self-contained -p:PublishSingleFile=false -o s7dump/publish/linux-x64
# Windows binary: -r win-x64 -o s7dump/publish/win-x64
dotnet test s7dump/tests/s7dump.Tests
```

Or without a local .NET, in Docker:

```bash
docker run --rm -v "$PWD/s7dump:/src" -v s7dump-nuget:/root/.nuget/packages -w /src \
  mcr.microsoft.com/dotnet/sdk:8.0 \
  dotnet publish -c Release -r linux-x64 --self-contained -p:PublishSingleFile=false -o publish/linux-x64
```

The dump also holds the configured connections (`connections`: local ID, partner, both
TSAPs, each value from the connection tables and from the compiled records) and the raw STL of
communication block calls, see [`docs/s7dump-connections.md`](../docs/s7dump-connections.md).
s7dump reads files only; it never opens a network connection.

## Third-party library

s7dump uses [DotNetSiemensPLCToolBoxLibrary](https://github.com/dotnetprojects/DotNetSiemensPLCToolBoxLibrary)
(NuGet `DotNetProjects.DotNetSiemensPLCToolBoxLibrary` 4.4.10, pinned in `packages.lock.json`),
licensed under the **GNU Lesser General Public License v2.1**. It is used unmodified and is
published as a separate, replaceable DLL (`DotNetSiemensPLCToolBoxLibrary.dll`; never as a
single-file bundle). The library's source code is available at the link above.
