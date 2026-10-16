---
name: FB_Valve.scl
kind: OTHER
language: scl
original_language: SCL
protected: false
parse_quality: full
attributes:
  source_kind: scl
  type: source
---

# FB_Valve.scl

## Source

```scl
FUNCTION_BLOCK FB 11
TITLE = 'Ventil'
VAR_INPUT
  Open : BOOL;
END_VAR
VAR_OUTPUT
  Position : REAL;
END_VAR
BEGIN
  IF Open THEN
    Position := 100.0;
  END_IF;
END_FUNCTION_BLOCK
```
