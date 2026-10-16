---
name: DB_Heating
kind: IDB
number: 30
language: none
protected: false
parse_quality: full
instance_of: FB_Heating
attributes:
  address: DB 30
path_prefix: '"DB_Heating"'
variable_scope: db_member
interface:
- {offset: '0.0', name: TempActual, type: REAL, section: IN}
- {offset: '4.0', name: HeaterOn, type: BOOL, section: OUT}
- {offset: '6.0', name: TempLimit, type: REAL, section: STATIC, start: '2.500000e+002'}
- {offset: '10.0', name: Valve, type: FB11, section: STATIC}
---

# DB_Heating

Instance of `FB_Heating`.

## Interface
| Offset | Section | Name | Type | Start | Comment |
|---|---|---|---|---|---|
| 0.0 | IN | TempActual | REAL |  |  |
| 4.0 | OUT | HeaterOn | BOOL |  |  |
| 6.0 | STATIC | TempLimit | REAL | 2.500000e+002 |  |
| 10.0 | STATIC | Valve | FB11 |  |  |
