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
{platform_section}
