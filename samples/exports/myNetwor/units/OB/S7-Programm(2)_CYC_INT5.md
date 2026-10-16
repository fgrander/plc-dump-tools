---
name: S7-Programm(2)/CYC_INT5
kind: OB
number: 35
language: stl
original_language: LAD
protected: false
parse_quality: full
folder: S7-Programm(2)
attributes:
  address: OB 35
  version: '0.1'
title:
  de: '"Cyclic Interrupt"'
networks:
- {'no': 1, line_start: 24, line_end: 36}
- {'no': 2, line_start: 38, line_end: 52}
- {'no': 3, line_start: 54, line_end: 114}
- {'no': 4, line_start: 116, line_end: 145}
---

# S7-Programm(2)/CYC_INT5 — "Cyclic Interrupt"

## NW 1

```stl
      O     #SYS_TRUE
      ON    #SYS_TRUE
      =     L34.0
      A     L 34.0
      BLD   102
      =     #SYS_TRUE
      A     L 34.0
      NOT
      =     #SYS_FALSE
```

## NW 2

```stl
      A     #SYS_FALSE
      =     L34.0
      BLD   103
      CALL  "SCALE" (
            IN      := PW256,
            HI_LIM  := 1.000000e+002,
            LO_LIM  := 0.000000e+000,
            BIPOLAR := L 34.0,
            RET_VAL := #RET,
            OUT     := #PV_VALUE)
      NOP   0
```

## NW 3

```stl
      A(
      A     #SYS_FALSE
      =     L34.0
      BLD   103
      A(
      CALL  "CONT_C", DB100 (
            COM_RST  := ,
            MAN_ON   := ,
            PVPER_ON := ,
            P_SEL    := ,
            I_SEL    := ,
            INT_HOLD := ,
            I_ITL_ON := ,
            D_SEL    := ,
            CYCLE    := ,
            SP_INT   := L#1112014848,
            PV_IN    := #PV_VALUE,
            PV_PER   := ,
            MAN      := ,
            GAIN     := L#1056964608,
            TI       := T#10s,
            TD       := T#1s,
            TM_LAG   := ,
            DEADB_W  := ,
            LMN_HLM  := ,
            LMN_LLM  := ,
            PV_FAC   := ,
            PV_OFF   := ,
            LMN_FAC  := ,
            LMN_OFF  := ,
            I_ITLVAL := ,
            DISV     := ,
            LMN      := #tLMN,
            LMN_PER  := ,
            QLMN_HLM := ,
            QLMN_LLM := ,
            LMN_P    := ,
            LMN_I    := ,
            LMN_D    := ,
            PV       := ,
            ER       := )
      A     BR
      )
      JNB   _001
      CALL  "UNSCALE" (
            IN      := #tLMN,
            HI_LIM  := 1.000000e+003,
            LO_LIM  := 0.000000e+000,
            BIPOLAR := L 34.0,
            RET_VAL := #RET,
            OUT     := #t_WORD)
_001: A     BR
      )
      JNB   _002
      L     #t_WORD
      T     PQW256
_002: NOP   0
```

## NW 4

```stl
      CALL  "CONT_S", DB101 (
            COM_RST  := ,
            LMNR_HS  := ,
            LMNR_LS  := ,
            LMNS_ON  := ,
            LMNUP    := ,
            LMNDN    := ,
            PVPER_ON := ,
            CYCLE    := ,
            SP_INT   := L#1092616192,
            PV_IN    := #PV_VALUE,
            PV_PER   := ,
            GAIN     := L#1036831949,
            TI       := T#1m,
            DEADB_W  := ,
            PV_FAC   := ,
            PV_OFF   := ,
            PULSE_TM := ,
            BREAK_TM := ,
            MTR_TM   := ,
            DISV     := ,
            QLMNUP   := ,
            QLMNDN   := ,
            PV       := ,
            ER       := )
      NOP   0
```
