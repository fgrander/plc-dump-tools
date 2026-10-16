# Common format additions for TIA (format v1, backward compatible)

All additions are optional; existing exports (testfixture, STEP 7 classic) stay valid without
change. Schemas in `python/src/plcexport/schemas/` are extended; `plcexport validate` checks them.

## 1. Manifest

```jsonc
{
  "format_version": 1,
  "kind": "project",                      // new, optional: "project" (default) | "library"
  "device": "PLC_Press3",                 // new, optional: device inside a bundle; "_project"
  "parts": [                              // new, optional; default [{"kind":"common","path":"."}]
    {"kind": "common", "path": "."},
    {"kind": "siemens-simatic-sd", "path": "sd", "files": 214, "checksum": "sha256:…"}
  ],
  "platform": {"id": "siemens-tia", "version": "V21 Upd1"},
  "upgrade": {"from": "V18", "to": "V21", "tool": "TIA Portal V21 Upd1",
              "messages": ["…"]},         // "messages" new, optional
  "source": {"path": "...", "kind": "archive", "checksum": "sha256:…"},
  "extractor": {"id": "tia", "version": "1.0.0", "route": "local",
                "worker": "TIAHOST01", "vendor_software": "TIA Portal V21 Upd1"},
  "...": "unchanged fields"
}
```

Rules:
- `source.path` is the source's path relative to the scanned root, with `/` ; `plcexport one` writes the
  file or folder name. A manifest never holds a path
  of the machine that ran the export. The path is no longer run-specific: when it
  changes, the manifest is committed again.
- `parts[].path` is relative and inside the export folder; the `common` part is always `"."`.
- The `checksum` of a native part is computed over its sorted file paths and contents, so a
  change in any SD file changes the manifest (deterministic).
- `index.md` lists every unit, including SD units, with their real path (`sd/...s7dcl`); the
  `Cat` column marks the part (`unit (SD)`).

## 2. Folder layout of a TIA PLC export

```text
<plant>/<line>/<PLC>/
├── README.md  index.md  manifest.json  coverage.json  structure.json
├── symbols.json  io.json  hardware.json  xref.json
├── library.json                 # project library
├── library_links.json           # written by `relink`
├── units/<KIND>/<name>.md       # common-format units (S7-300/400, SD-refused units, TAG_TABLE)
├── datatypes/<name>.md
├── safety/safety.json
├── hmi/hmi.json  hmi/screens/<screen>.md
├── sd/<folder>/<unit>.s7dcl|.s7res     # native part, as TIA wrote it; text IDs renumbered
└── platform/siemens-tia/platform.json  platform/siemens-tia/library_ids.json
```

The project-level export (`device: "_project"`) holds HMI devices connected to several PLCs and
the hardware of devices without a PLC; it has no `units/`.

## 3. Library export

Path `libraries/<library name>/` in an export repository. Manifest `kind: "library"`.

```text
libraries/<name>/
├── README.md  index.md  manifest.json  coverage.json
├── library.json
├── units/<KIND>/<Type>@<version>.md     # common-format content of a type version
├── sd/<type>/<version>/<unit>.s7dcl|.s7res
└── platform/siemens-tia/library_ids.json
```

### `library.json`

```jsonc
{
  "name": "ACME_Standard", "version": "3.2", "kind": "global", "company": true,
  "duplicate_of": null,
  "types": [
    {"name": "Conveyor", "folder": "Types/Material", "kind": "plc_block",
     "versions": [
       {"version": "1.2.0", "status": "released", "author": "…", "date": "2025-03-14",
        "comment": {"en-US": "Speed ramp added"}, "content_part": "sd",
        "content_path": "sd/Conveyor/1.2.0/FB_Conveyor.s7dcl", "gap_reason": null},
       {"version": "1.4.0", "status": "released", "...": "..."},
       {"version": "1.5.0", "status": "in_work", "...": "..."}
     ]}
  ],
  "master_copies": [{"name": "Station template", "folder": "Templates",
                     "objects": [{"name": "PLC_1", "type": "plc"}], "content_path": null}]
}
```

Versions are sorted numerically (`1.10.0` after `1.9.0`). The coverage categories are used
as follows for a library: `program_units` = type versions with content, `hmi` = HMI types,
`structure` = folders and master copies, the others `unavailable` with `not_in_project`.

## 4. `library_links.json` (project exports)

```jsonc
{
  "compared_with": [{"library": "ACME_Standard", "path": "libraries/ACME_Standard",
                     "commit": "3f2c…"}],
  "links": [
    {"object": "FB_Conveyor", "object_kind": "unit", "type_name": "Conveyor",
     "type_folder": "Types/Material", "version": "1.2.0", "status": "released",
     "original_library": "ACME_Standard", "origin": "company_library",
     "library": "ACME_Standard", "comparison": "outdated", "newest_released": "1.4.0"}
  ]
}
```

Sorted by `object`. The extractor writes the file with the link facts only (`origin`
`unknown_library` or `project_only`, `comparison: "not_compared"`, `compared_with: []`), so a
project export is complete and deterministic before comparison. A later relink step (not part of this repository) fills
`origin`, `library`, `comparison`, `newest_released` and `compared_with`, and changes nothing
else in the export. Type GUIDs for matching stay in `platform/siemens-tia/library_ids.json`.

## 5. Path mapping for bundles

A batch exporter can map projects to export paths with rules like these, with the placeholder
`{device}` for one export per PLC (not part of this repository):

```yaml
- match: "Werk_{plant}/{line}/**"
  plc: "{device}"                 # one export per PLC device of the project
- match: "Bibliotheken/**"
  library: true                   # library sources go to libraries/<library name>/
```

A device that no rule maps is reported (`unmapped`) and not published. It is
still exported under `--out`; that export is the record that keeps the next run from extracting
it again.
