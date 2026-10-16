# STL cross-reference rules

The Python STL analyzer turns every STL line into zero or more xrefs (`xref.json` rows).
Operands are kept verbatim as `target_text`; a normalized key is used for matching only.

| STL | Example | Access |
|---|---|---|
| Bit logic | `A I 0.0`, `AN M 10.1`, `O`, `ON`, `X`, `XN` | read |
| Assign / set / reset | `= Q 4.0`, `S M 1.0`, `R M 1.0` | write |
| Edge | `FP M 2.0` (edge memory) | read_write |
| Load / transfer | `L MW 10` / `T DBW 4` | read / write |
| Timers and counters | `SP T 5`, `SE`, `SD`, `SS`, `SF`, `CU C 3`, `CD`, `S C 3` (set counter), `R T 5`, `L T 5`, `LC C 3`, `A T 5` | write (start/count/set/reset) / read (load, check) |
| Open DB | `OPN DB 10`, `OPN DI 20` | read of the DB as a unit |
| Fully qualified DB access | `L DB10.DBW 2`, `= "DB_Recipe".Ready` | per instruction |
| Calls | `CALL FB 10, DB 30` / `CALL "FC_Scale"` / `UC FC 5` / `CC FC 5` | call (unit); instance DB: call (variable) |
| Multi-instance call | `CALL #Valve` (static of type `FB 11`) | call of the FB type (`FB_Valve`) |
| Array element | `L "DB_Rec".Arr[#i]`, `T #t.XY[1, 0]` | per instruction, on the array variable (`"DB_Rec".Arr`); non-constant indexes: read |
| Call parameters | `TempActual := MD 20` | IN → read, OUT → write, IN_OUT → read_write; callee unknown → unknown_direction |
| Register-indirect | `A I [AR1, P#0.0]`, `L W [AR2, P#2.0]` | indirect |
| Memory-indirect | `L MW [MD 10]`, `OPN DB [MW 4]`, `UC FC [MW 2]` | indirect (the pointer operand itself: read) |
| Jumps and labels | `JC M001`, `M001: NOP 0` | none |
| Accumulator/status only | `NOT`, `SET`, `CLR`, `+I`, `TAK`, `BE`, `BEC` | none |

Rules:
- German mnemonics are accepted as input (`U E 0.0`, `= A 4.0`, `Z 3`), so sources in either
  mnemonic give the same xrefs.
- Normalized key: mnemonic-independent area (`I`, `Q`, `M`, `PI`, `PQ`, `DB<n>.DBX/B/W/D`,
  `L`, `T`, `C`), no spaces, upper case: `I 0.0`, `E0.0` → `I0.0`; `DB10.DBX 2.0` →
  `DB10.DBX2.0`; symbols keep their quotes.
- One xref per operand occurrence; `line` is the STL line in the export file ([common-format.md](common-format.md) §7).
- A line the analyzer cannot classify yields no xref and one coverage warning
  `stl_unclassified` with the block and line (never an exception).
- A jump label that is not a valid STEP 7 label (a letter or `_`, then up to three letters,
  digits or `_`) has no readable name in the project: the library returns arbitrary bytes for
  it, also control characters. It gets a generated name (`M001`, `M002`, … skipping names the
  block uses), the same at its definition and at every jump to it, and the block gets one
  coverage warning `stl_label_unreadable`. Readable labels are never changed.
- Export filter (clarification 2026-10-08): `xref.json` keeps only global variable
  targets — inputs, outputs, peripheral I/O, memory, timers, counters, DB values (`DB10.DBW 2`,
  `DBX 0.0`, `"DB".member`) and global symbols — plus every unit row (calls, opened DBs). Left
  out: locals (`#name`: TEMP, IN, OUT, IN_OUT, STAT, `RET_VAL`), the local data stack
  (`L 0.1`, `LW 2`), the running FB's instance data (`DIX`, `DIW`, `DID`), registers (`DINO`,
  `BR`, `AR1`) and every `indirect` row. A global operand passed to a parameter stays, with
  `via_param`.
