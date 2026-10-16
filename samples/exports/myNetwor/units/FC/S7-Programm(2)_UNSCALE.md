---
name: S7-Programm(2)/UNSCALE
kind: FC
number: 106
language: none
original_language: STL
protected: true
parse_quality: full
folder: S7-Programm(2)
attributes:
  address: FC 106
  author: SEA
  family: CONVERT
  version: '2.0'
title:
  de: UNSCALING VALUES
comment:
  de: '

    '
path_prefix: '"S7-Programm(2)/UNSCALE"'
variable_scope: fc_interface
interface:
- {name: BIPOLAR, type: BOOL, section: IN, start: 'False', comment: {de: ' 1=bipolar; 0=unipolar'}}
- {name: HI_LIM, type: REAL, section: IN, start: '0.000000e+000', comment: {de: ' upper limit in engineering units'}}
- {name: IN, type: REAL, section: IN, start: '0.000000e+000', comment: {de: ' input value to be unscaled'}}
- {name: LO_LIM, type: REAL, section: IN, start: '0.000000e+000', comment: {de: ' lower limit in engineering units'}}
- {name: OUT, type: INT, section: OUT, start: '0', comment: {de: ' result of the unscale conversion'}}
- {name: RET_VAL, type: WORD, section: OUT, start: W#16#0}
- {name: K1, type: REAL, section: TEMP, start: '0.000000e+000', comment: {de: ' low limit for output value'}}
- {name: K2, type: REAL, section: TEMP, start: '0.000000e+000', comment: {de: ' high limit for output value'}}
- {name: SPAN, type: REAL, section: TEMP, start: '0.000000e+000', comment: {de: ' HI_LIM - LO_LIM'}}
- {name: TEMP1, type: REAL, section: TEMP, start: '0.000000e+000', comment: {de: ' temporary result'}}
---

# S7-Programm(2)/UNSCALE — UNSCALING VALUES

> de:
>

## Interface
| Section | Name | Type | Start | Comment |
|---|---|---|---|---|
| IN | BIPOLAR | BOOL | False | de: 1=bipolar; 0=unipolar |
| IN | HI_LIM | REAL | 0.000000e+000 | de: upper limit in engineering units |
| IN | IN | REAL | 0.000000e+000 | de: input value to be unscaled |
| IN | LO_LIM | REAL | 0.000000e+000 | de: lower limit in engineering units |
| OUT | OUT | INT | 0 | de: result of the unscale conversion |
| OUT | RET_VAL | WORD | W#16#0 |  |
| TEMP | K1 | REAL | 0.000000e+000 | de: low limit for output value |
| TEMP | K2 | REAL | 0.000000e+000 | de: high limit for output value |
| TEMP | SPAN | REAL | 0.000000e+000 | de: HI_LIM - LO_LIM |
| TEMP | TEMP1 | REAL | 0.000000e+000 | de: temporary result |

> protected – logic not exported
