---
name: S7-Programm(2)/SCALE
kind: FC
number: 105
language: none
original_language: STL
protected: true
parse_quality: full
folder: S7-Programm(2)
attributes:
  address: FC 105
  author: SEA
  family: CONVERT
  version: '2.1'
title:
  de: SCALING VALUES
comment:
  de: '

    '
path_prefix: '"S7-Programm(2)/SCALE"'
variable_scope: fc_interface
interface:
- {name: BIPOLAR, type: BOOL, section: IN, start: 'False', comment: {de: ' 1=bipolar; 0=unipolar'}}
- {name: HI_LIM, type: REAL, section: IN, start: '0.000000e+000', comment: {de: ' upper limit in engineering units'}}
- {name: IN, type: INT, section: IN, start: '0', comment: {de: ' input value to be scaled'}}
- {name: LO_LIM, type: REAL, section: IN, start: '0.000000e+000', comment: {de: ' lower limit in engineering units'}}
- {name: OUT, type: REAL, section: OUT, start: '0.000000e+000', comment: {de: ' result of the scale conversion'}}
- {name: RET_VAL, type: WORD, section: OUT, start: W#16#0}
- {name: IN_REAL, type: REAL, section: TEMP, start: '0.000000e+000', comment: {de: ' input value as a REAL number'}}
- {name: K1, type: REAL, section: TEMP, start: '0.000000e+000', comment: {de: ' low limit for input value'}}
- {name: K2, type: REAL, section: TEMP, start: '0.000000e+000', comment: {de: ' high limit for input value'}}
- {name: SPAN, type: REAL, section: TEMP, start: '0.000000e+000', comment: {de: ' HI_LIM - LO_LIM'}}
- {name: TEMP1, type: REAL, section: TEMP, start: '0.000000e+000', comment: {de: ' temporary result'}}
---

# S7-Programm(2)/SCALE — SCALING VALUES

> de:
>

## Interface
| Section | Name | Type | Start | Comment |
|---|---|---|---|---|
| IN | BIPOLAR | BOOL | False | de: 1=bipolar; 0=unipolar |
| IN | HI_LIM | REAL | 0.000000e+000 | de: upper limit in engineering units |
| IN | IN | INT | 0 | de: input value to be scaled |
| IN | LO_LIM | REAL | 0.000000e+000 | de: lower limit in engineering units |
| OUT | OUT | REAL | 0.000000e+000 | de: result of the scale conversion |
| OUT | RET_VAL | WORD | W#16#0 |  |
| TEMP | IN_REAL | REAL | 0.000000e+000 | de: input value as a REAL number |
| TEMP | K1 | REAL | 0.000000e+000 | de: low limit for input value |
| TEMP | K2 | REAL | 0.000000e+000 | de: high limit for input value |
| TEMP | SPAN | REAL | 0.000000e+000 | de: HI_LIM - LO_LIM |
| TEMP | TEMP1 | REAL | 0.000000e+000 | de: temporary result |

> protected – logic not exported
