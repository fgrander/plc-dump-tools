# `tiadump installed` and `used_products`

Additions to [`tiadump.md`](tiadump.md).

## `tiadump installed --tia V21 --out installed.json`

Starts a TIA Portal process without user interface for the given major (default: newest), reads
its installed software and exits. Opens no project. Exit codes as `tiadump` (4 = Openness access
denied, 64 = usage).

```json
{
  "tool": {"name": "tiadump", "version": "…", "openness": "V21"},
  "tia": {"version": "V21", "update": "Upd1"},
  "installed": [
    {"name": "STEP 7 Professional", "version": "V21"},
    {"name": "STEP 7 Safety Advanced", "version": "V21"},
    {"name": "HSP 0345 SINAMICS G220", "version": "V21"}
  ]
}
```

`installed` is sorted by name; names exactly as Openness reports them.

## `dump.json`: `used_products`

Projects (not libraries): `used_products: [{name, version}]` from `Project.UsedProducts`, sorted
by name. Optional in the dump schema so that recorded dumps without it stay valid.

## Read-only

`installed` only reads `InstalledSoftware`; `ForbiddenApiTests` stay as they are.
