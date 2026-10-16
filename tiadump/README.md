# tiadump

Dumps TIA Portal projects and global libraries through **TIA Portal Openness** into `dump.json`
plus exported files; see [`docs/tiadump.md`](../docs/tiadump.md) for the CLI, exit codes and dump
format, and [`tia/dump_schema.json`](../python/src/plcexport/extractors/tia/dump_schema.json) for the schema.

`tiadump` only ever opens a **copy** inside `--work`. It never saves, downloads, goes online or
imports, and compiles only units of the working copy that cannot be exported otherwise;
`tests/tiadump.Tests/ForbiddenApiTests.cs` fails the build if the code calls such an API. Older
projects and libraries are upgraded on the copy.

## Prerequisites

| What | Why |
|---|---|
| TIA Portal V20 Update 4 or later (developed on V21) with Openness | the API `tiadump` uses |
| A **STEP 7 Professional** license (local or floating) | every block/UDT export needs it; without it TIA only opens projects and exports tag tables. A trial can be activated once with `tiadump … --with-ui` |
| Options the projects need (STEP 7 Safety, WinCC, HSPs) | otherwise TIA cannot open those projects; such projects are reported, not exported |
| The account that runs `tiadump` is a member of the local group **Siemens TIA Openness** | Openness refuses access otherwise. Sign out and in again after joining |
| `tiadump.exe` on the Openness allow list (`install-whitelist.ps1`, admin, after each build) | unattended runs; otherwise TIA shows an access dialog for every new build |
| .NET SDK 8 | builds the `net48` project (the .NET Framework 4.8 runtime is part of Windows) |

Add the account to the group (admin PowerShell), then sign out and in:

```powershell
Add-LocalGroupMember -Group "Siemens TIA Openness" -Member "$env:USERDOMAIN\$env:USERNAME"
whoami /groups | Select-String "Openness"   # must list the group after signing in again
```

## Build and test

From the repository root:

```powershell
dotnet build tiadump -c Release -o tiadump/publish
.\tiadump\install-whitelist.ps1          # admin PowerShell; -WhatIf shows the entry only
dotnet test tiadump/tests/tiadump.Tests --filter "Category!=tia"   # no TIA needed
dotnet test tiadump/tests/tiadump.Tests --filter "Category=tia"    # TIA host only
```

The Openness assemblies are referenced from the installed TIA Portal
(`C:\Program Files\Siemens\Automation\Portal V21\PublicAPI\V21\net48`, override with
`-p:TiaMajor=20` or `-p:TiaPublicApi=<folder>`) and never copied into the output or the
repository; at run time they are resolved from the registry
(`HKLM\SOFTWARE\Siemens\Automation\Openness`). Without a TIA Portal installation the project
does not build.

**One build per TIA major.** A host with several TIA Portal versions can have one build per
major:

```powershell
dotnet build tiadump -c Release -p:TiaMajor=20 -o tiadump/publish/V20
.\tiadump\install-whitelist.ps1 -Exe tiadump\publish\V20\tiadump.exe   # admin
```

Whether the V21 build also runs against V20 Update 4 (so that one build serves both) has not been
tested yet.

`tiadump installed --tia V21 --out installed.json` lists the software of one installation
([`docs/tiadump-installed.md`](../docs/tiadump-installed.md)); it starts TIA Portal without user
interface and opens no project.

## Spikes

`tiadump spike <name> …` (`Spikes/`) are research probes that record what Openness exposes
(alarms, HMI, libraries, connections). They follow the same read-only rules.
