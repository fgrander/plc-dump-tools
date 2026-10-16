---
name: FC_Scale
kind: FC
number: 5
language: stl
original_language: STL
protected: false
parse_quality: full
attributes:
  address: FC 5
title:
  de: Analogwert skalieren
path_prefix: '"FC_Scale"'
variable_scope: fc_interface
interface:
- {name: Raw, type: INT, section: IN}
- {name: RET_VAL, type: REAL, section: RETURN}
networks:
- {'no': 1, line_start: 31, line_end: 38, title: {de: Skalieren}}
- {'no': 2, line_start: 40, line_end: 55, title: {de: 'Zeiten, Zähler, indirekt'}}
---

# FC_Scale — Analogwert skalieren

## Interface
| Section | Name | Type | Start | Comment |
|---|---|---|---|---|
| IN | Raw | INT |  |  |
| RETURN | RET_VAL | REAL |  |  |

## NW 1 — Skalieren

```stl
      L     #Raw
      ITD
      DTR
      T     #RET_VAL
```

## NW 2 — Zeiten, Zähler, indirekt

```stl
      A     M     10.0
      L     S5T#5S
      SE    T      5
      A     T      5
      =     Q      4.2
      A     I      0.3
      CU    C      3
      L     MW    20
      T     DB20.DBW    4
      L     IW [AR1,P#0.0]
      OPN   DB    20
      L     DBW [MD    10]
```
