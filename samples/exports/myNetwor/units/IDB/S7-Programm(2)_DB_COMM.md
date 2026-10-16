---
name: S7-Programm(2)/DB_COMM
kind: IDB
number: 5
language: none
protected: false
parse_quality: full
folder: S7-Programm(2)
instance_of: S7-Programm(2)/Ethernet_Comm
attributes:
  address: DB 5
path_prefix: '"S7-Programm(2)/DB_COMM"'
variable_scope: db_member
interface:
- {offset: '0.0', name: ReadPLC2, type: SFB14, section: STATIC}
- {offset: '90.0', name: WritePLC3, type: FB12, section: STATIC}
- {offset: '456.0', name: ReadPLC3, type: FB13, section: STATIC}
---

# S7-Programm(2)/DB_COMM

Instance of `S7-Programm(2)/Ethernet_Comm`.

## Interface
| Offset | Section | Name | Type | Start | Comment |
|---|---|---|---|---|---|
| 0.0 | STATIC | ReadPLC2 | SFB14 |  |  |
| 90.0 | STATIC | WritePLC3 | FB12 |  |  |
| 456.0 | STATIC | ReadPLC3 | FB13 |  |  |
