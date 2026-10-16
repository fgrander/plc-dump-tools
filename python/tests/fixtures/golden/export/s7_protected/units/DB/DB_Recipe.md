---
name: DB_Recipe
kind: DB
number: 20
language: none
protected: false
parse_quality: full
attributes:
  address: DB 20
path_prefix: '"DB_Recipe"'
variable_scope: db_member
interface:
- {offset: '0.0', name: Counter, type: INT, start: '0'}
- {offset: '2.0', name: Limits, type: STRUCT, members: [{offset: '2.0', name: Max, type: REAL, start: '2.600000e+002'}, {offset: '6.0', name: Min, type: REAL, start: '2.000000e+001'}]}
- {offset: '10.0', name: Setpoint, type: REAL, start: '2.300000e+002', comment: {de: Sollwert}}
---

# DB_Recipe

## Interface
| Offset | Section | Name | Type | Start | Comment |
|---|---|---|---|---|---|
| 0.0 |  | Counter | INT | 0 |  |
| 2.0 |  | Limits | STRUCT |  |  |
| 2.0 |  | Limits.Max | REAL | 2.600000e+002 |  |
| 6.0 |  | Limits.Min | REAL | 2.000000e+001 |  |
| 10.0 |  | Setpoint | REAL | 2.300000e+002 | de: Sollwert |
