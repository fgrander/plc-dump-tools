---
name: F_EStop
kind: FB
number: 100
language: stl
original_language: F-FBD
protected: false
safety: true
parse_quality: full
attributes:
  address: FB 100
title:
  de: Not-Halt Presse
path_prefix: '"F_EStop"'
variable_scope: fb_interface
interface:
- {name: ESTOP, type: BOOL, section: IN, comment: {de: Not-Halt Kanal}}
networks:
- {'no': 1, line_start: 29, line_end: 34, title: {de: Not-Halt}}
---

# F_EStop — Not-Halt Presse

## Interface
| Section | Name | Type | Start | Comment |
|---|---|---|---|---|
| IN | ESTOP | BOOL |  | de: Not-Halt Kanal |

## NW 1 — Not-Halt

```stl
U     #ESTOP
=     "Q_Pump"
```
