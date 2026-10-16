---
name: Main
kind: OB
number: 1
language: stl
original_language: LAD
protected: false
parse_quality: full
attributes:
  address: OB 1
  family: MAIN
  version: '0.1'
title:
  de: Hauptprogramm
networks:
- {'no': 1, line_start: 23, line_end: 32, title: {de: Pumpe Start/Stopp}, comment: {de: Selbsthaltung der Hydraulikpumpe}}
- {'no': 2, line_start: 34, line_end: 40, title: {de: Heizung}}
- {'no': 3, line_start: 42, line_end: 49, title: {de: Rezeptzähler}}
---

# Main — Hauptprogramm

## NW 1 — Pumpe Start/Stopp
> de: Selbsthaltung der Hydraulikpumpe

```stl
      A     "I_Start"
      O     "M_Run"
      AN    "I_Stop"
      =     "Q_Pump"
      =     "M_Run"
```

## NW 2 — Heizung

```stl
      CALL  "FB_Heating" , "DB_Heating"
       TempActual:="I_TempPlate"
       HeaterOn  :="Q_Heater_On"
```

## NW 3 — Rezeptzähler

```stl
      L     "DB_Recipe".Counter
      L     1
      +I
      T     "DB_Recipe".Counter
```
