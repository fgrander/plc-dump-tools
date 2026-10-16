---
name: F_GLOBDB
kind: DB
number: 818
language: none
protected: false
safety: true
parse_quality: full
attributes:
  address: DB 818
path_prefix: '"F_GLOBDB"'
variable_scope: db_member
interface:
- {name: DB_VERSION, type: WORD, start: W#16#402}
- {name: F_PROG_SIG, type: DWORD, start: DW#16#0}
---

# F_GLOBDB

## Interface
| Section | Name | Type | Start | Comment |
|---|---|---|---|---|
|  | DB_VERSION | WORD | W#16#402 |  |
|  | F_PROG_SIG | DWORD | DW#16#0 |  |
