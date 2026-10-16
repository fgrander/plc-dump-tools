---
name: FB_Heating
kind: FB
number: 10
language: none
original_language: FBD
protected: true
parse_quality: full
attributes:
  address: FB 10
  author: Max Mustermann
  family: HEAT
  version: '1.2'
title:
  de: Heizplattenregelung
comment:
  de: Begrenzt die Plattentemperatur auf TempLimit.
path_prefix: '"FB_Heating"'
variable_scope: fb_interface
interface:
- {name: TempActual, type: REAL, section: IN}
- {name: HeaterOn, type: BOOL, section: OUT}
- {name: TempLimit, type: REAL, section: STATIC, start: '2.500000e+002', comment: {de: Maximale Plattentemperatur}}
- {name: Valve, type: FB11, section: STATIC}
- {name: t, type: REAL, section: TEMP}
---

# FB_Heating — Heizplattenregelung

> de: Begrenzt die Plattentemperatur auf TempLimit.

## Interface
| Section | Name | Type | Start | Comment |
|---|---|---|---|---|
| IN | TempActual | REAL |  |  |
| OUT | HeaterOn | BOOL |  |  |
| STATIC | TempLimit | REAL | 2.500000e+002 | de: Maximale Plattentemperatur |
| STATIC | Valve | FB11 |  |  |
| TEMP | t | REAL |  |  |

> protected – logic not exported
