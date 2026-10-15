# `s7dump`: connections

Extends [`s7dump-json.md`](s7dump-json.md).
`dump_version` stays 1: both fields are optional, and a dump without them is valid (a consumer
should then treat connections as not checked).

## `connections`

```json
"connections": [
  {
    "list": 2,
    "owner": {"station": "SIMATIC 300-Station", "rack": 0, "slot": 2, "module": "CPU 317F-2 PN/DP"},
    "local_node": 4,
    "name": "S7-Verbindung 2",
    "type_id": 1332225,
    "local_id": 16,
    "active": false,
    "one_way": true,
    "unspecified": true,
    "tables": {
      "local_resource": 17,
      "partner_name": "HomePLC3", "partner_rack": 0, "partner_slot": 3,
      "partner_resource": 16, "partner_ip": "10.102.10.20"
    },
    "compiled": {
      "file": "sdb/00000001/0000002f.PG",
      "active": false, "local_tsap": "11.02",
      "partner_ip": "10.102.10.20", "partner_tsap": "10.03"
    },
    "partner_node": null
  }
]
```

Rules:

- One entry per row of `CONN/CO_n/HOMOVERB.DBF` that is not deleted, in every list of
  `CONN/VERBTAB.DBF` that is not deleted. Order: `list`, then `local_id`, then `name`.
- `local_id` is the stored integer. Nothing in the dump is converted to hex.
- `owner` is null when the list's module cannot be resolved; `local_node` and `partner_node`
  are node numbers of the dump's `ethernet` entries, or null.
- `tables.partner_*` are null for a partner inside the project (`unspecified: false`).
- `compiled` is null when no compiled record matches owner and `local_id`; `file` is relative
  to the project folder, with forward slashes.
- Personal columns of the tables (`CREATOR`) are never read.
- A table or record that cannot be read adds an entry to the dump's `errors`
  (`{where, message}`) and never fails the dump.
- A project without `CONN/VERBTAB.DBF` has `"connections": []`.

## `raw_stl` on networks

```json
{"no": 2, "title": null, "comment": null,
 "stl": ["      CALL  \"BSEND\" (", "..."],
 "raw_stl": ["      L     W#16#AAAA", "      T     DIW   92", "..."]}
```

- Present only on networks of unprotected blocks that call SFB or FB 8, 9, 12, 13, 14 or 15,
  written absolute (`UC FB 12`) or with a symbol that the program's symbol table assigns to
  one of them (`UC "BSEND"`). Whether it really is a communication block is for the consumer to decide by the called
  block's interface; a user FB can have one of these numbers.
- The statements of the network as the library converts them with call reconstruction switched
  off, in the requested mnemonic, one statement per entry. `stl` is unchanged.
- If the statements cannot be produced, `raw_stl` is absent and the block's `errors` say why.

## Read-only

`s7dump` opens project files for reading only. It opens no network connection; the addresses it
reads are data.
