---
name: FB_Valve
kind: FB
number: 11
language: stl
original_language: SCL
protected: false
parse_quality: full
attributes:
  address: FB 11
  generated_from: FB_Valve.scl
path_prefix: '"FB_Valve"'
variable_scope: fb_interface
interface:
- {name: Open, type: BOOL, section: IN}
- {name: Position, type: REAL, section: OUT}
networks:
- {'no': 1, line_start: 29, line_end: 37}
---

# FB_Valve

## Interface
| Section | Name | Type | Start | Comment |
|---|---|---|---|---|
| IN | Open | BOOL |  |  |
| OUT | Position | REAL |  |  |

## NW 1

```stl
      A     #Open
      JCN   M001
      L     1.000000e+002
      T     #Position
M001: NOP   0
```
