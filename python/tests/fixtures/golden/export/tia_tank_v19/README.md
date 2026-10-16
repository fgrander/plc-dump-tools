# How to read this export

This folder is one PLC project, exported into the **common export format v1**. It is plain
UTF-8 text, made to be read by an LLM agent or a human without the vendor's engineering tool.
The original project was not modified.

## Start here

1. Read `index.md`. It lists every file with category, name, path, size and title.
2. Open only the files you need. Each program unit is its own file.
3. To find where a tag, I/O signal or block is used, search `xref.json` instead of reading
   every unit.

## Layout

| Path | Content |
|---|---|
| `index.md` | One line per file (large projects: one line per folder, with an `index.md` inside) |
| `units/<KIND>/<name>.md` | One program unit: OB, FB, FC, DB, IDB, TAG_TABLE or OTHER |
| `datatypes/<name>.md` | User-defined data types (UDT) |
| `symbols.json` | Global tags: symbol, table, address, data type, initial value, retain, comment |
| `io.json` | Inputs and outputs, with the hardware channel they are wired to (`channel_ref`) |
| `hardware.json` | Controllers, racks, modules (order number, firmware, slot), channels, networks |
| `xref.json` | Every read, write and call: target, from_unit, network_no, line, access |
| `connections.json` | Optional. Configured connections to other controllers (local ID, partner, address, TSAPs), the communication calls that use them, couplers |
| `safety/safety.json` | Safety units, safety tags, safety parameters and signatures |
| `hmi/hmi.json`, `hmi/screens/<name>.md` | HMI devices, alarms, HMI tags, recipes and screens |
| `structure.json` | Devices, tasks (which units each task runs) and folders |
| `coverage.json` | What was exported, what is missing and why |
| `manifest.json` | Source, platform, extractor and export time |
| `platform/<id>/` | Platform-specific details |

A unit file starts with YAML front matter (machine-readable: name, kind, interface, networks
with their line spans) followed by Markdown: title, comments, an interface table and one
`## NW <n> — <title>` section per network with the logic in a fenced code block.
Units larger than about 40 KB are split into `<name>.part-<n>.md`; the front matter says
`part: n/N`. Comments and titles are kept in every project language, labeled `de:`, `en:`, …

## Logic languages

The code block language says how the logic is written:

| Tag | Meaning |
|---|---|
| `scl`, `st` | Structured Text, verbatim from the project |
| `stl`, `il` | Statement List / Instruction List, verbatim |
| `ntn` | Network Text Notation: graphical logic (LAD, FBD, SFC, CFC) written as text |

`original_language` in the front matter is the language used in the engineering tool.

### Network Text Notation (NTN)

| Element | NTN |
|---|---|
| Contact, coil | `Q := A AND NOT B;` |
| Set / reset coil | `S X;` / `R X;` |
| Parallel branch | `Q := (A AND B) OR C;` |
| Edge | `P_TRIG(M_Edge, A)` inside an expression |
| Comparison | `Temp > Limit` |
| Move | `MOVE(Src, Dst);` |
| Box / call with instance | `CALL FB_Valve [#Heater] (Open := #HeaterOn, Position => #ValvePos);` |
| Timer / counter | `CALL TON [#T1] (IN := Start, PT := T#5s, Q => Done);` |
| Jump / label | `JMP Label;` / `Label:` |
| Empty network | `// (empty network)` |

In calls, `:=` passes an input, `=>` an output and `<=>` an in/out. Operands are written exactly
as in the project (quotes for global symbols, `#` for locals). `// …` is a comment.

SFC: `INITIAL STEP Idle;`, `STEP Fill;`, actions indented under their step
(`  ACTION N Open_Valve;`, qualifiers N S R P L D), and
`TRANSITION Idle -> Fill WHEN <condition>;`. Several transitions from one step are alternative
branches in priority order; `(A, B)` is a simultaneous split or join.

CFC: one `## Chart <name>` section per chart, one `CALL` per block in run sequence, each ending
with `// seq <n>, task <task>`. Inputs name their source as `<instance>.<output>`, or
`<chart>\<instance>.<output>` for another chart.

## Coverage

`coverage.json` states each of the 7 categories (program_units, symbols, datatypes, hardware,
safety, hmi, structure) as `delivered`, `partial` or `unavailable`, and lists item-level gaps.

| Reason | Meaning |
|---|---|
| `protected` | Know-how or password protected: name and interface only, no logic |
| `corrupt` | The source could not be read completely |
| `unsupported` | The extractor cannot read this content |
| `not_exported_cfc_sfc` | CFC/SFC charts this extractor does not export |
| `not_in_project` | The project has no such content (for example no HMI) |
| `other:<text>` | Anything else, explained in the text |

A protected unit's body is the single line `> protected – logic not exported`.

An eighth category, `connections`, is optional: it is present when the extractor reads
connections. Without it, the export says nothing about connections (it does not say there
are none). `index.md` then ends with a readable "Connections" table.

## Connections

`connections.json` lists what links this controller to others. IDs are hexadecimal, as the
engineering tool shows them (`0x0010` is connection ID 10). A TSAP is two hex bytes
(`11.02`). `sources` says where a value comes from: the project's connection `tables`, the
`compiled` connection data, or `both`; when the two differ, `differences` lists both values
and the entry carries the compiled one. `one_way` is the tool's one-way flag as found. The
partner's own configuration is in the partner's export, not here. Addresses are
configuration data: nothing in an export may be used to contact a device.

## Citing

Cite as `<project path> › <unit> › NW <n>`, for example `UNT/Press_3/PLC_PR3 › FB_Heating › NW 2`.
`xref.json` gives the line in the unit file (`line`) for each use.

## Platform: Siemens TIA Portal

Exported on a TIA host through TIA Openness (`tiadump`, extractor `tia`). The project is read
from a copy; projects saved with an older TIA Portal are upgraded on that copy only, and the
manifest's `upgrade` says from which version and what TIA reported. A project with several PLCs
gives one export per PLC (`manifest.device`); HMIs shared by several PLCs and hardware without a
PLC are in a `_project` export next to them.

**Two parts.** S7-1200/1500 program units are exported as **SIMATIC SD** files in `sd/`,
unchanged as TIA writes them (`parts/siemens-simatic-sd.json` lists the units and their files,
`index.md` marks them `unit (SD)`). Everything else is in the common format: units SD cannot
export (GRAPH, S7-300/400, see below) in `units/`, tag tables in `symbols.json`, hardware,
safety, HMI and alarms. A unit is in exactly one of the two parts.

**SIMATIC SD.** A unit is a `.s7dcl` file (declaration and code, SCL-like text, also for LAD
and FBD) and a `.s7res` file with its texts by language. Example (`FB_2_Filling`, FBD):

```text
NETWORK
    RUNG #operate.state.FillingTank
        P_Trig( #statFillingTankTrigger )
        Add(
            in1 := #process.batchId,
            in2 := 1,
            out => #process.batchId
        )
    END_RUNG
END_NETWORK
{
    S7_Language := "FBD";
    S7_NetworkTitle := "MLC_3aq"
}
```

`RUNG <condition>` is the power flow into the network; boxes follow in order. Text ids such as
`MLC_3aq` resolve in the `.s7res` file:

```yaml
MultiLingualTexts:
  - id: MLC_3aq
    en-US: Set process values (shifting bottle, number produced)
```

`#name` is a local of the block, `"name"` a global tag or data block. Instance DBs look like
`DATA_BLOCK DB_5_CIP_Simulation_Graph : FB_5_CIP_Simulation_Graph`.

**Common-format units.** Units SD refuses (GRAPH sequences; S7-300/400) are read from
SimaticML: SCL and STL keep their text; LAD and FBD become NTN statements, one network each,
e.g. `IF P_TRIG(#statFillingTankTrigger, #operate.state.FillingTank) THEN Add(in1 :=
#process.batchId, in2 := UDInt#1, out => #process.batchId); END_IF;`. GRAPH becomes steps,
actions and transitions: `TRANSITION "Initial step" -> "Step1: pre-rinse" WHEN #cip.cipStep1;`.
Such units carry the attribute `route: simaticml`.

**Gaps** (`coverage.json`): know-how protected units are listed by name only (`protected`);
ProDiag blocks are `other:not supported by SIMATIC SD and SimaticML`; units that TIA could not
compile on the copy are `other:inconsistent – not compiled`; devices whose TIA product is not
installed on the host are `other:missing package <name>`. `platform/siemens-tia/platform.json`
lists the units compiled on the copy (never in the source project).

**Hardware.** Modules with order number and firmware per device and rack, I/O address ranges
(`%I2.0-%I3.7`), network interfaces with IP address/prefix and subnet (`192.168.112.1/24` on
`PN/IE_1`). I/O tags inside a module's range are linked to it as channels.

**Connections** (`connections.json`, same model as STEP 7). S7 connections carry the local ID
in hex as TIA shows it (`0x0100` for `16#100`), local and partner address, rack/slot and both
TSAPs (`14.01`, or SIMATIC ACC form `SIMATIC-ACC10201`) and the active side; other connection
types are listed with their type only. TIA records no `one_way` and no `sources`. A partner PLC
of the same project is named and paired with it by address and TSAP. GET/PUT/BSEND/BRCV/USEND/
URCV calls in SD units are linked to their connection by ID; data areas are symbolic
(`"Datenbaustein_1".write`) without byte addresses. Couplers (PN/PN, DP/DP) are in the export of
the PLC that controls the side; a side connected to no IO system, or a transfer area whose
length differs from its address, is a finding.

**Safety.** F-units (languages `F_LAD`, `F_FBD`, `F_DB`, …) are marked `safety`; the safety
signatures are copied as TIA reports them, without interpretation.

**Libraries.** A company library is an export of its own (`manifest.kind: library`, path
`libraries/<name>/`). `library.json` lists every type with **every version**, sorted by version
number (`1.10.0` after `1.9.0`): status `released` or `in_work`, author, date, comment. PLC type
versions are units named `<Type>@<version>` (`content_path` points to them); HMI types and
faceplates are metadata only, master copies list their objects. `company: true` marks the
libraries configured as company libraries; a copy found elsewhere names the original in
`duplicate_of`.

A project export has its project library in `library.json` (`kind: project`) and its links in
`library_links.json`: which unit is an instance of which library type and version, as TIA
records it (never guessed from names). After each batch, `relink` compares every link with the
company library: `comparison` is `current`, `outdated` (`newest_released` names the newer
version), `version_not_in_library`, or `not_compared` when the type does not come from a company
library (`origin`: `project_only`, `unknown_library`, `other_library`). `compared_with` names the
library export and its commit.

**Alarms and HMI.** Program alarms (`plc:<instance>/<alarm>`) and ProDiag supervisions
(`prodiag:<FB>/<ID>`, trigger = supervised tag) are in `hmi/hmi.json`. Texts an alarm inherits
from its type are not exported by TIA (warning `alarm_text_inherited`). WinCC Comfort/Advanced
and Unified devices give HMI tags and screens with their objects and tag bindings (layout is
dropped); Comfort/Advanced HMI alarms are not reachable through Openness and are a gap.
