# `tiadump` CLI and dump

`tiadump/` — C#, `net48`, x64. Uses the installed TIA Portal's Openness API. Meant to be called
by a program (the caller) that copies the project into a work directory first and reads
`dump.json` afterwards.

## CLI

```text
tiadump probe   <file>                          --out <dump.json>
tiadump project <file> --work <dir>             --out <dir>   [--languages all|<bcp47,...>]
tiadump library <file> --work <dir>             --out <dir>
tiadump --version

common options: [--tia V21]                          # default: newest installed TIA
                [--umac-user-env NAME --umac-password-env NAME]   # UMAC-protected projects
```

- `<file>` is always a **copy** in the job's work directory (`.apNN`, `.zapNN`, `.alNN`,
  `.zalNN`). `tiadump` should never receive the path of an original project.
- `--work` is where archives are retrieved and upgrades happen. `--out` receives `dump.json`
  plus exported files.
- `probe` opens nothing in TIA Portal: it reads the file name and header only. It emits
  `{kind, archive, saved_version, saved_update, used_products, used_support_packages}` with
  `kind` = `project | library | local_session` (`.alsNN`; a multiuser local
  session, never to be passed to `tiadump project`). V21 writes `ProjectInfo.txt` (root of
  a `.zapNN`, or next to the `.apNN`): `saved_update` comes from `TiaPortal.LastUsed.
  TechnicalVersion` (`21.00.04.00` → `Upd4`, no update part → null; the mapping of the third
  part to the update number is an assumption until a V20/V21 update sample confirms it), and
  `used_products`/`used_support_packages` list `{name, version}`. Without the file (V19/V20):
  `saved_update` from the project header when present, else null, and empty lists.

| Exit | Meaning |
|---|---|
| 0 | dump written (may contain `errors[]`) |
| 2 | cannot open (damaged, locked, missing product) |
| 3 | TIA refused the upgrade |
| 4 | Openness access denied (group, allow list, UMAC) |
| 5 | project locked (opened by another TIA instance or user); retry later |
| 64 | usage error |
| other | crash; see stderr |

## Forbidden calls (enforced by `ForbiddenApiTests`)

`Save`, `SaveAs`, `Compile`, `Download`, `GoOnline`, `Upload`, `Import`, `ImportFromDocuments`,
`SetAttribute`, `SetAttributes`, `Delete`, `Create`, `CreateFrom`, `Archive`, `UpdateLibrary`,
`UpdateProject`, `CleanUpLibrary`, `Retrieve` with a target outside `--work`. Allowed writes:
`OpenWithUpgrade` on the work copy, `Export`, `ExportAsDocuments`, `Projects.Retrieve` into
`--work`. Generic calls count too: `ConnectionComposition.Create<T>(…)` and
`Connection.Delete()` are found by the same names.

## `dump.json` (dump_version 1)

Canonical JSON, keys sorted, lists sorted as noted. Unit `part` is `sd`, `common` (SimaticML) or
`none` (nothing exportable; see `errors`). The JSON Schema is
[`schema/tiadump.schema.json`](../schema/tiadump.schema.json) (Draft 2020-12); consumers should
validate every dump against it.

```jsonc
{
  "dump_version": 1,
  "tool": {"name": "tiadump", "version": "1.0.0", "openness": "21.0.0.0"},
  "source": {"file": "Line3.ap18", "kind": "project",          // project | library
             "saved_version": "V18", "saved_update": "Upd2"},   // update null if unknown
  "tia": {"version": "V21", "update": "Upd1",
          "upgrade": {"from": "V18", "to": "V21", "messages": ["..."]}},  // null if none
  "languages": {"project": ["de-DE", "en-US"], "editing": "de-DE", "reference": "en-US"},
  "multiuser": {"kind": "none"},            // none | server_project | local_session
  "missing_packages": [{"name": "SIMATIC Safety", "objects": ["PLC_Press3"]}],
  "counts": {"PLC_Press3": {"units": 214, "tag_tables": 6, "tags": 812},
             "HMI_Press3": {"hmi_tags": 120, "screens": 14, "hmi_alarms": 55},  // hmi_alarms: Unified only
             "_hardware": {"modules": 37},
             "_project_library": {"types": 9, "type_versions": 21, "master_copies": 2}},
                                            // counted from the object model;
                                            // no PLC alarm count: Openness has no collection for it
  "cleanup": {"outside_work": []},          // files TIA wrote outside --work for this job
  "compiled_units": ["PLC_1/FB_5_CIP_Simulation_Graph"],  // compiled in the working copy
  "devices": [                                                  // sorted by name
    {
      "name": "PLC_Press3", "kind": "plc", "family": "S7-1500",
      "order_no": "6ES7 516-3AN02-0AB0", "firmware": "V3.1",
      "units": [                                                 // sorted by folder, name
        {"name": "FB_Conveyor", "kind": "FB", "number": 12, "language": "SCL",
         "folder": "Program blocks/Conveyor", "protected": false, "safety": false,
         "consistent": true, "attributes": {"family": "", "version": "0.1", "author": ""},
         "part": "sd", "files": ["sd/Conveyor/FB_Conveyor.s7dcl", "sd/Conveyor/FB_Conveyor.s7res"],
         "error": null}
      ],
      "tag_tables": [{"name": "IO", "file": "simaticml/tags/IO.xml"}],
      "alarms": {"texts_file": "alarms/plc_alarm_texts.json", "classes": ["Errors", "Warnings"]},
      "safety": {"signatures": [{"kind": "CollectiveOfflineSignature", "value": "0x1A2B3C4D"}]},
      "library_links": [
        {"object": "FB_Conveyor", "object_kind": "unit", "type_name": "Conveyor",
         "type_folder": "Types/Material", "version": "1.2.0", "status": "released",
         "original_library": "ACME_Standard", "type_guid": "…"}
      ],
      "connected_hmis": ["HMI_Press3"]
    },
    {
      "name": "HMI_Press3", "kind": "hmi", "hmi_family": "unified",   // comfort|advanced|unified|other
      "connections": [{"name": "Conn_PLC", "plc": "PLC_Press3"}],
      "tags": [{"name": "Speed", "connection": "Conn_PLC", "plc_tag": "\"DB_Conv\".Speed",
                "data_type": "Real"}],
      "screens": [{"name": "Overview", "objects": [{"name": "SpeedField", "type": "IOField",
                    "tag_bindings": ["Speed"]}], "texts": {"de-DE": ["..."]}}],
      "alarms": [{"id": "1", "kind": "discrete", "class": "Errors",
                  "texts": {"de-DE": "Motor gestört"}, "trigger_tag": "AlarmWord1", "bit": 0}],
      "library_links": []
    }
  ],
  "hardware": {
    "devices": [{"name": "S71500/ET200MP station_1", "items": [
      {"name": "DI 32x24VDC", "path": "Rack_0/Slot_2", "rack": "Rack_0", "slot": 2,
       "order_no": "6ES7 521-1BL00-0AB0", "firmware": "V2.1",
       "addresses": [{"io": "input", "start": 0, "length": 4}],
       "interfaces": []}
    ]}],
    "subnets": [{"name": "PN/IE_1", "kind": "PROFINET", "nodes": [
      {"device_item": "PLC_Press3/PROFINET interface_1", "address": "192.168.0.1/24",
       "device_name": "plc_press3"}]}]
  },
  "project_library": {"kind": "project", "types": [/* as library.types */],
                      "master_copies": [/* as library.master_copies */]},
  "library": null,            // library dumps: {"name", "version", "kind": "global", "types": [
                              //   {"name","folder","kind","guid","versions":[{"version","status",
                              //    "author","date","comment":{lang:text},"guid","content":{
                              //    "part":"sd|common|none","path":"...","error":null}}]}],
                              //  "master_copies":[{"name","folder","objects":[...],"path":null}]}
  "errors": [{"where": "PLC_Press3/FB_Prodiag", "kind": "unsupported", "message": "..."}]
  // kinds: protected, inconsistent, unsupported, missing_package, license, compile_failed,
  //        export_failed, other
}
```

### File tree next to `dump.json`

```text
<out>/
├── dump.json
├── sd/<device>/<folder>/<unit>.s7dcl|.s7res        # ExportAsDocuments output, unchanged
├── simaticml/<device>/blocks/<folder>/<unit>.xml   # Export(…) for common-format units
├── simaticml/<device>/tags/<table>.xml
├── alarms/<device>/…                               # PLC alarm texts and supervisions (xlsx)
├── hmi/<device>/screens/<screen>.xml               # Comfort/Advanced screen exports
└── library/sd/<type>/<version>/…                   # LibraryTypeVersion.ExportAsDocuments
```

Cleanup: before exit, `tiadump` closes TIA, deletes everything below `--work`, and deletes the
files TIA wrote for this job outside `--work` (known locations, e.g. the upgrade log and
retrieve temp folders). Anything it cannot delete is listed in `cleanup.outside_work`;
the caller deletes `--out` when done with it.

Determinism: `tiadump` sorts every list; it never writes timestamps except `source` / `tia`
metadata. GUIDs appear only in `type_guid`/`guid`.
