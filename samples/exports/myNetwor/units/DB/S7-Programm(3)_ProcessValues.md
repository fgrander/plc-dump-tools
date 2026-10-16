---
name: S7-Programm(3)/ProcessValues
kind: DB
number: 1
language: none
protected: false
parse_quality: full
folder: S7-Programm(3)
attributes:
  address: DB 1
path_prefix: '"S7-Programm(3)/ProcessValues"'
variable_scope: db_member
interface:
- {offset: '0.0', name: MyCounter, type: INT, start: '0', comment: {de: Counter}}
- {offset: '2.0', name: Counter_PLC300, type: INT, start: '0', comment: {de: Counter}}
- {offset: '4.0', name: Remote_counter, type: INT, start: '0', comment: {de: Counter}}
---

# S7-Programm(3)/ProcessValues

## Interface
| Offset | Section | Name | Type | Start | Comment |
|---|---|---|---|---|---|
| 0.0 |  | MyCounter | INT | 0 | de: Counter |
| 2.0 |  | Counter_PLC300 | INT | 0 | de: Counter |
| 4.0 |  | Remote_counter | INT | 0 | de: Counter |
