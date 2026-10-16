---
name: S7-Programm(2)/DB101
kind: IDB
number: 101
language: none
protected: false
parse_quality: full
folder: S7-Programm(2)
instance_of: FB42
attributes:
  address: DB 101
path_prefix: '"S7-Programm(2)/DB101"'
variable_scope: db_member
interface:
- {offset: '0.0', name: COM_RST, type: BOOL, section: IN, start: 'False', comment: {de: complete restart}}
- {offset: '0.1', name: LMNR_HS, type: BOOL, section: IN, start: 'False', comment: {de: high limit signal of repeated manipulated value}}
- {offset: '0.2', name: LMNR_LS, type: BOOL, section: IN, start: 'False', comment: {de: low limit signal of repeated manipulated value}}
- {offset: '0.3', name: LMNS_ON, type: BOOL, section: IN, start: 'False', comment: {de: manipulated signals on}}
- {offset: '0.4', name: LMNUP, type: BOOL, section: IN, start: 'False', comment: {de: manipulated signal up}}
- {offset: '0.5', name: LMNDN, type: BOOL, section: IN, start: 'False', comment: {de: manipulated signal down}}
- {offset: '0.6', name: PVPER_ON, type: BOOL, section: IN, start: 'False', comment: {de: process variable peripherie on}}
- {offset: '2.0', name: CYCLE, type: TIME, section: IN, start: T#1S, comment: {de: sample time}}
- {offset: '6.0', name: SP_INT, type: REAL, section: IN, start: '0.000000e+000', comment: {de: internal setpoint}}
- {offset: '10.0', name: PV_IN, type: REAL, section: IN, start: '0.000000e+000', comment: {de: process variable in}}
- {offset: '14.0', name: PV_PER, type: WORD, section: IN, start: W#16#0, comment: {de: process variable peripherie}}
- {offset: '16.0', name: GAIN, type: REAL, section: IN, start: '2.000000e+006', comment: {de: proportional gain}}
- {offset: '20.0', name: TI, type: TIME, section: IN, start: T#20S, comment: {de: reset time}}
- {offset: '24.0', name: DEADB_W, type: REAL, section: IN, start: '1.000000e+006', comment: {de: dead band width}}
- {offset: '28.0', name: PV_FAC, type: REAL, section: IN, start: '1.000000e+006', comment: {de: process variable factor}}
- {offset: '32.0', name: PV_OFF, type: REAL, section: IN, start: '0.000000e+000', comment: {de: process variable offset}}
- {offset: '36.0', name: PULSE_TM, type: TIME, section: IN, start: T#3S, comment: {de: minimum pulse time}}
- {offset: '40.0', name: BREAK_TM, type: TIME, section: IN, start: T#3S, comment: {de: minimum break time}}
- {offset: '44.0', name: MTR_TM, type: TIME, section: IN, start: T#30S, comment: {de: motor manipulated value}}
- {offset: '48.0', name: DISV, type: REAL, section: IN, start: '0.000000e+000', comment: {de: disturbance variable}}
- {offset: '52.0', name: QLMNUP, type: BOOL, section: OUT, start: 'False', comment: {de: manipulated signal up}}
- {offset: '52.1', name: QLMNDN, type: BOOL, section: OUT, start: 'False', comment: {de: manipulated signal down}}
- {offset: '54.0', name: PV, type: REAL, section: OUT, start: '0.000000e+000', comment: {de: process variable}}
- {offset: '58.0', name: ER, type: REAL, section: OUT, start: '0.000000e+000', comment: {de: error signal}}
- {offset: '62.0', name: LMNRS_ON, type: BOOL, section: STATIC, start: 'False'}
- {offset: '64.0', name: LMNRSVAL, type: REAL, section: STATIC, start: '0.000000e+000'}
- {offset: '68.0', name: LMNR_SIM, type: REAL, section: STATIC, start: '0.000000e+000'}
- {offset: '72.0', name: sFbPVal, type: REAL, section: STATIC, start: '0.000000e+000'}
- {offset: '76.0', name: sThrOn, type: REAL, section: STATIC, start: '0.000000e+000'}
- {offset: '80.0', name: siImpAus, type: INT, section: STATIC, start: '0'}
- {offset: '82.0', name: stImpDauer, type: TIME, section: STATIC, start: T#0MS}
- {offset: '86.0', name: stPausDauer, type: TIME, section: STATIC, start: T#0MS}
---

# S7-Programm(2)/DB101

Instance of `FB42`.

## Interface
| Offset | Section | Name | Type | Start | Comment |
|---|---|---|---|---|---|
| 0.0 | IN | COM_RST | BOOL | False | de: complete restart |
| 0.1 | IN | LMNR_HS | BOOL | False | de: high limit signal of repeated manipulated value |
| 0.2 | IN | LMNR_LS | BOOL | False | de: low limit signal of repeated manipulated value |
| 0.3 | IN | LMNS_ON | BOOL | False | de: manipulated signals on |
| 0.4 | IN | LMNUP | BOOL | False | de: manipulated signal up |
| 0.5 | IN | LMNDN | BOOL | False | de: manipulated signal down |
| 0.6 | IN | PVPER_ON | BOOL | False | de: process variable peripherie on |
| 2.0 | IN | CYCLE | TIME | T#1S | de: sample time |
| 6.0 | IN | SP_INT | REAL | 0.000000e+000 | de: internal setpoint |
| 10.0 | IN | PV_IN | REAL | 0.000000e+000 | de: process variable in |
| 14.0 | IN | PV_PER | WORD | W#16#0 | de: process variable peripherie |
| 16.0 | IN | GAIN | REAL | 2.000000e+006 | de: proportional gain |
| 20.0 | IN | TI | TIME | T#20S | de: reset time |
| 24.0 | IN | DEADB_W | REAL | 1.000000e+006 | de: dead band width |
| 28.0 | IN | PV_FAC | REAL | 1.000000e+006 | de: process variable factor |
| 32.0 | IN | PV_OFF | REAL | 0.000000e+000 | de: process variable offset |
| 36.0 | IN | PULSE_TM | TIME | T#3S | de: minimum pulse time |
| 40.0 | IN | BREAK_TM | TIME | T#3S | de: minimum break time |
| 44.0 | IN | MTR_TM | TIME | T#30S | de: motor manipulated value |
| 48.0 | IN | DISV | REAL | 0.000000e+000 | de: disturbance variable |
| 52.0 | OUT | QLMNUP | BOOL | False | de: manipulated signal up |
| 52.1 | OUT | QLMNDN | BOOL | False | de: manipulated signal down |
| 54.0 | OUT | PV | REAL | 0.000000e+000 | de: process variable |
| 58.0 | OUT | ER | REAL | 0.000000e+000 | de: error signal |
| 62.0 | STATIC | LMNRS_ON | BOOL | False |  |
| 64.0 | STATIC | LMNRSVAL | REAL | 0.000000e+000 |  |
| 68.0 | STATIC | LMNR_SIM | REAL | 0.000000e+000 |  |
| 72.0 | STATIC | sFbPVal | REAL | 0.000000e+000 |  |
| 76.0 | STATIC | sThrOn | REAL | 0.000000e+000 |  |
| 80.0 | STATIC | siImpAus | INT | 0 |  |
| 82.0 | STATIC | stImpDauer | TIME | T#0MS |  |
| 86.0 | STATIC | stPausDauer | TIME | T#0MS |  |
