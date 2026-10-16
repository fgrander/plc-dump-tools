# Common Export Format, version 1

Every export of every platform follows this format. The STEP 7 classic and the TIA Portal
extractors produce it (TIA additions: [common-format-tia.md](common-format-tia.md)). The format
version is recorded in `manifest.json` as `format_version: 1`. Breaking changes require a new
major version and a migration note.

## 1. General rules

- UTF-8 without BOM, LF line endings, final newline. Only text files.
- JSON: canonical form (sorted keys, 2-space indent, no ASCII escaping).
- No timestamps, absolute paths, GUIDs or tool-internal IDs outside `manifest.json` and
  `platform/`.
- File names: identifiers are kept as they are if they are file-system safe. Otherwise unsafe
  characters become `_`, and a short hash suffix is added only if two names collide. The mapping
  appears in `index.md`.
- Every text that exists in several languages is an object `{ "<bcp47>": "<text>" }`, with
  languages sorted.

## 2. Layout

```text
<project>/
├── README.md
├── index.md
├── manifest.json
├── coverage.json
├── structure.json
├── symbols.json
├── io.json
├── hardware.json
├── xref.json
├── connections.json                  # optional: connections, their calls, couplers
├── units/<KIND>/<name>.md            # KIND ∈ OB FB FC DB IDB TAG_TABLE OTHER
├── units/<KIND>/<name>.part-<n>.md   # instead of <name>.md for units over 40 KB
├── units/<KIND>/index.md             # only when the project has more than 500 units
├── datatypes/<name>.md               # UDTs (kind UDT); datatypes/index.md above 500 units
├── safety/safety.json                # safety tags, parameters, signatures
├── hmi/hmi.json                      # devices, alarms, hmi tags, recipes
├── hmi/screens/<name>.md
└── platform/<platform-id>/platform.json  # free-form, documented in README
```

A category that the platform does not provide still has its file. The file then holds an empty
list, and `coverage.json` says `unavailable` with a reason.

`connections.json` is the exception: it is an additive, optional part of version 1 (see
[connections-json.md](connections-json.md)). It exists
only when an extractor read connections and found content; `coverage.json` then has the
optional eighth category `connections`, and `index.md` ends with a readable `## Connections`
section after the file list. An export without the category was not checked for
connections and is valid.

## 3. `manifest.json`

```json
{
  "format_version": 1,
  "source": {"path": "…", "kind": "folder|archive|multiproject_member", "checksum": "sha256:…"},
  "platform": {"id": "siemens-step7-classic", "version": "V5.6"},
  "project": {"controller": "CPU 315-2 DP", "line_or_machine": "Press 3", "languages": ["de"]},
  "extractor": {"id": "s7classic-direct", "version": "1.0.0", "route": "local|worker",
                "worker": null, "vendor_software": null},
  "upgrade": null,
  "exported_at": "2026-10-07T12:00:00Z",
  "counts": {"units": 0, "variables": 0, "xrefs": 0, "hardware_modules": 0, "hmi_screens": 0},
  "coverage_summary": {"program_units": "delivered", "symbols": "delivered", "…": "…"}
}
```

`source.path` is the source's path relative to the scanned root, never an absolute local path
(see [common-format-tia.md](common-format-tia.md) §1).

`upgrade` is `null`, or `{"from": "<source version>", "to": "<version opened>", "tool": "<vendor
software and version>"}` when the extractor had to upgrade the working copy. `platform.version`
always stays the version detected in the source. After a fallback (extractor contract rule 5)
`extractor` also has `"fallback_from": {"id": "<first extractor>", "reason": "…"}`.

## 4. `coverage.json`

```json
{
  "categories": {
    "program_units": {"state": "delivered|partial|unavailable", "reason": null},
    "symbols": {}, "datatypes": {}, "hardware": {}, "safety": {}, "hmi": {}, "structure": {}
  },
  "gaps": [
    {"category": "program_units", "item": "FB12", "reason": "protected"},
    {"category": "program_units", "item": "CFC chart Mixer1",
     "reason": "not_exported_cfc_sfc"}
  ],
  "warnings": [{"code": "parse_error", "message": "…", "unit": "FB12"}]
}
```

The allowed `reason` values are `protected`, `corrupt`, `unsupported`, `not_exported_cfc_sfc`,
`not_in_project` and `other:<text>`.

## 5. Unit files: `units/<KIND>/<name>.md` and `datatypes/<name>.md`

They have YAML front matter, which is machine-readable, followed by a
Markdown body for agents and humans.

~~~markdown
---
name: FB_Heating
kind: FB
number: 10
language: stl            # language of the body below: scl | stl | st | ntn | il | none
original_language: LAD   # language in the engineering tool
protected: false
safety: false
parse_quality: full      # full | partial | names_only
folder: Program/Heating
attributes: {family: HEAT, version: "1.2", author: "…"}
title: {de: "Heizplattenregelung", en: "Heating plate control"}
comment: {de: "…"}
interface:
  - {name: TempActual, section: IN, type: Real}
  - {name: TempLimit, section: STATIC, type: Real, start: "250.0", retain: true,
     comment: {de: "Maximale Plattentemperatur"}}
path_prefix: '"FB_Heating"'    # symbolic path of a member = <prefix>.<name> (nested: <parent>.<name>)
variable_scope: fb_interface   # scope of the members: fb_interface | fc_interface | db_member | udt_member
networks:                # line spans refer to this file; 'no' is quoted (YAML 1.1 boolean)
  - {'no': 1, line_start: 31, line_end: 40, title: {de: "…"}, comment: {de: "…"}}
part: "1/2"              # only for split units
---

# FB_Heating — Heizplattenregelung

## Interface
| Section | Name | Type | Start | Comment |
|---|---|---|---|---|
| IN | TempActual | Real | | |
| STATIC | TempLimit | Real | 250.0 | de: Maximale Plattentemperatur |

## NW 1 — Heizplattentemperatur begrenzen
> de: Heizplattentemperatur auf TempLimit begrenzen

```stl
      L     #TempActual
      L     #TempLimit
      >R
      =     #HeaterOn
```
~~~

Rules:
- Keys are written in the fixed order shown; keys without a value are omitted (`safety`,
  `folder`, `instance_of`, `attributes`, `title`, `comment`, `path_prefix`, `variable_scope`,
  `interface`, `networks`, `element_texts`, `part`). `language` is `none` when there is no body.
- Interface members are one flow-style line each, grouped by section (IN, OUT, IN_OUT, STATIC,
  TEMP, CONSTANT, RETURN). Optional member keys: `offset` (first, before `name`), `path` (only
  when it is not `<prefix>.<name>`), `section`, `start`, `retain`, `comment`, `dims`, `address`,
  `io_direction`, `accessible`, `visible`, `writable`, `safety: true`, `members` (nested).
- `offset` (optional, additive in v1): the member's position in its data block, or from
  the start of its data type, as
  `byte.bit` (`"0.0"`, `"10.5"`), only where the platform has a fixed layout. When any member of
  a unit has an offset, the interface table gets an `Offset` column as its first column, like
  the address column of the STEP 7 DB editor (clarification 2026-10-09):
  `| Offset | Section | Name | Type | Start | Comment |`; otherwise the table is unchanged.
  Within a section, members with an offset are listed in rising address order (byte, then bit),
  then members the extractor gave a declaration position, in that order (a data type whose
  layout is not reliable keeps its declaration order, see
  [udt-member-offsets.md](udt-member-offsets.md); the position is not a key of the file),
  then all other members, sorted by name. A reader keeps the order of the file.
- Comments on single elements are kept in `element_texts: [{network_no, element_ref, kind,
  lang, text}]`.
- Split units repeat the front matter in every part with that part's `networks` and
  `part: n/N`; the interface table is in part 1.
- `TAG_TABLE` units point to `symbols.json` (column `table`). `IDB` units name their FB in
  `instance_of`. UDTs use `## Members` instead of `## Interface`.
- Networks appear in execution order. Each one is a `## NW <n> — <title in first project
  language>` heading, then comment lines per language, then one fenced code block.
- Textual languages are verbatim. Graphical languages use NTN (§6), or the platform's
  native textual equivalent where it preserves meaning (declared in `language`).
- Protected units keep their front matter and interface. The body is the single line
  `> protected – logic not exported`.

## 6. Network Text Notation (NTN), version 1

The notation for graphical logic. It is deterministic, and statements appear in
execution order.

| Element | NTN |
|---|---|
| Contact, coil | `Q := A AND NOT B;` |
| Set/reset coil | `S X;` / `R X;` |
| Parallel branch | `Q := (A AND B) OR C;` |
| Edge | `P_TRIG(M_Edge, A)` inside expressions |
| Comparison | `Temp > Limit` |
| Move | `MOVE(Src, Dst);` |
| Box / call with instance | `CALL FB_Valve [#Heater] (Open := #HeaterOn, Position => #ValvePos);` |
| Timer / counter | `CALL TON [#T1] (IN := Start, PT := T#5s, Q => Done);` |
| Jump / label | `JMP Label;` / `Label:` |
| Unconnected / empty | `// (empty network)` |

`:=` passes inputs, `=>` passes outputs, and `<=>` is used for in/outs. Operands are written
exactly as in the project, including quotes and `#` for locals. Comments on elements are
appended as `// …`.

### 6.1 SFC (sequential function charts)

Body language `ntn`. One block per chart, with steps and transitions in chart order:

| Element | NTN |
|---|---|
| Step / initial step | `STEP Fill;` / `INITIAL STEP Idle;` |
| Action with qualifier | `  ACTION N Open_Valve;` (qualifiers N, S, R, P, L T#…, D T#…) |
| Inline action body | `  ACTION N { Q_Valve := TRUE; }` |
| Transition | `TRANSITION Idle -> Fill WHEN I_Start AND NOT I_Fault;` |
| Alternative branch | several transitions from one step, listed in priority order |
| Simultaneous split / join | `TRANSITION Fill -> (Heat, Stir) WHEN …;` / `TRANSITION (Heat, Stir) -> Drain WHEN …;` |
| Jump | a transition to any step, e.g. `TRANSITION Drain -> Idle WHEN …;` |

### 6.2 CFC (continuous function charts)

One `## Chart <name>` section per chart. Block instances appear in run sequence, one `CALL` each,
using the §6 call syntax. Inputs name their source as `<instance>.<output>`, a tag, or a constant.
Unconnected inputs are omitted. Each call ends with `// seq <n>, task <task>`. Connections to
other charts use `<chart>\<instance>.<output>`.

## 7. Tables

- Rows omit keys whose value is null or empty. `false` is kept (not retentive ≠ unknown).
- **`symbols.json`**: global tags `[{symbol, table, data_type, scope, address, initial, retain,
  comment{lang}, io_direction, accessible, visible, writable, safety, parent, dims}]`, sorted
  by symbol. `symbol` is written exactly as in the project (e.g. `"I_Start"` with quotes);
  `table` is the tag table unit.
- **`io.json`**: `{inputs: [...], outputs: [...]}`, rows `{symbol, address, data_type,
  comment{lang}, channel_ref}`, sorted by address.
- **`hardware.json`**: `{controllers, racks, modules, channels, networks}`. Modules have
  `{ref, slot, rack, type, order_no, firmware, address_ranges}`, and channels have
  `{ref, module_ref, address, symbol}`.
- **`structure.json`**: `{devices, tasks: [{name, kind, interval, units[]}], folders:
  [{path, units[]}]}`.
- **`xref.json`**: `[{target, target_kind: variable|unit, from_unit, network_no, line, access,
  via_param, channel_ref, hmi_ref}]`, sorted. `access` is one of
  `read | write | read_write | call | unknown_direction | indirect`. `line` is a line of the
  unit file (or part file) that holds the network, at the statement naming the target. HMI tag
  bindings are rows with `from_unit: "hmi:<screen>"`, `hmi_ref: "<screen>/<object>"` and
  `access: unknown_direction`. `channel_ref` is set on rows whose target is wired to a hardware
  channel. Only global targets are listed: no block-local variables (`#name` in
  Siemens notation), no temporary stack addresses (`L 0.1`, `LW 2`), no CPU registers (`AR1`,
  `DINO`, `BR`) and no register-indirect operands (`D[AR1,P#2.0]`, `DB[LW14]`). An array
  element of a global variable is listed under the variable, and a global index variable as a
  read.
- **`safety/safety.json`**: `{units[], tags[], parameters[], signatures:
  [{scope, value, kind}]}`.
- **`hmi/hmi.json`**: `{devices, alarms, hmi_tags, recipes}`. Screens are in
  `hmi/screens/<name>.md`, with front matter `{name, device, objects: [{name, type,
  tag_bindings[]}], texts{lang}}`.

## 8. `index.md`

```markdown
# Index — <project path>  (<platform> <version>, <controller>)
See README.md for how to read this export.

| Cat | Name | Path | Size | Title |
|---|---|---|---|---|
| FB | FB_Heating | units/FB/FB_Heating.md | 3.1k | Heizplattenregelung |
| tags | Symbols (512) | symbols.json | 48k | |
```

Each line stays under about 100 characters. Above 500 units, units are listed in
`units/<KIND>/index.md` (and `datatypes/index.md`) and the top-level index has one line per
folder. Every file except `index.md` itself is listed exactly once. The size of
`manifest.json` is left empty, because it changes with every run. Titles are cut at 40
characters.

## 9. README.md

The README is generated from a template. It explains the layout, the NTN, the language codes,
the meaning of the coverage reasons, and how to cite (`project path › unit › NW n`). Each
platform adds a short section (e.g. STEP 7 address syntax), which is versioned with its
extractor.

## 10. Validation

JSON Schemas live in `python/src/plcexport/schemas/*.schema.json` and also cover unit front
matter; `python/src/plcexport/format/validate.py` adds the structural checks.
`plcexport validate <dir>` exits
non-zero on any violation and lists every violation.
