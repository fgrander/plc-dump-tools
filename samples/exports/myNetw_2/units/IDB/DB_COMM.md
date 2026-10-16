---
name: DB_COMM
kind: IDB
number: 5
language: none
protected: false
parse_quality: full
instance_of: Ethernet_Comm
attributes:
  address: DB 5
path_prefix: '"DB_COMM"'
variable_scope: db_member
interface:
- {offset: '0.0', name: WritePLC3, type: FB12, section: STATIC}
- {offset: '366.0', name: ReadPLC3, type: FB13, section: STATIC}
---

# DB_COMM

Instance of `Ethernet_Comm`.

## Interface
| Offset | Section | Name | Type | Start | Comment |
|---|---|---|---|---|---|
| 0.0 | STATIC | WritePLC3 | FB12 |  |  |
| 366.0 | STATIC | ReadPLC3 | FB13 |  |  |
