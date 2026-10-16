## Platform: Siemens STEP 7 classic (V5.x)

Exported without STEP 7 by reading the project files (DotNetSiemensPLCToolBoxLibrary, extractor
`s7classic-direct`), or through STEP 7 itself on an export worker (`s7classic-worker`); the
manifest names the route.

**Blocks.** OB, FB, FC, DB (instance DBs are kind `IDB`, `instance_of` names the FB), UDTs in
`datatypes/`, VATs and SFB/SFC references as `OTHER`. A block is named by its symbol (`FB_Heating`);
its absolute name is the attribute `address` (`FB 10`). `family`, `version` and `author` are block
attributes. In projects with several S7 programs, names are prefixed with the program
(`S7 Program(2)/Main`), and so are symbols (`"S7 Program(2)/I_Start"`).

**Logic is STL** (`language: stl`). LAD and FBD blocks are shown as the STL that STEP 7 itself
shows for them; `original_language` (`LAD`, `FBD`, `STL`, `SCL`, …) says how the block was
written. Example:

```stl
      A     "I_Start"          // AND: start button
      O     "M_Run"            // OR: self-holding
      AN    "I_Stop"           // AND NOT: stop button
      =     "Q_Pump"           // assign the output
```

**Mnemonics.** Exports use the international mnemonics. German equivalents, in case a question
uses them:

| International | German | Meaning |
|---|---|---|
| `I 0.0`, `IB`, `IW`, `ID` | `E 0.0`, `EB`, `EW`, `ED` | input bit/byte/word/double word |
| `Q 4.0`, `QB`, `QW`, `QD` | `A 4.0`, `AB`, `AW`, `AD` | output |
| `PIW 256`, `PQW 512` | `PEW 256`, `PAW 512` | peripheral input/output |
| `M 10.0`, `MW 20` | `M 10.0`, `MW 20` | bit memory |
| `T 5`, `C 3` | `T 5`, `Z 3` | timer, counter |
| `A`, `AN`, `O`, `=` | `U`, `UN`, `O`, `=` | AND, AND NOT, OR, assign |
| `JC`, `JCN`, `JU` | `SPB`, `SPBN`, `SPA` | conditional / unconditional jump |

Data blocks: `DB10.DBX 2.0` (bit), `DB10.DBW 4` (word) or symbolically `"DB_Recipe".Counter`;
after `OPN DB 20`, short forms like `DBW 4` refer to the opened DB. `[AR1,P#0.0]` and
`[MD 10]` are indirect addresses: `xref.json` lists them with access `indirect`.

**Calls.** `CALL "FB_Heating" , "DB_Heating"` calls an FB with its instance DB; the following
lines `Param:=operand` pass the parameters (inputs are reads, outputs writes in `xref.json`).

**Sources.** SCL and STL source files are units of kind `OTHER` named `<source>.scl`/`.stl`
with the text verbatim; blocks compiled from them carry `generated_from`.

**Connections.** `connections.json` holds the connections configured in NetPro, read from
the project's connection tables and from the compiled connection data of the last "save and
compile". Local IDs are shown as NetPro shows them (hex). S7 connections are read in full;
other connection types are listed with `kind: other`, their stored type number and
`details: not_read`. I-Devices and intelligent DP slaves are not detected.

**Not exported here.** Hardware is partial: stations, CPUs, CPs and network addresses, but not
signal modules or their address ranges. HMI (WinCC flexible) is not part of a STEP 7 export.
PCS 7 CFC charts and SFC sequences are listed in `coverage.json` as `not_exported_cfc_sfc`.
Comments are in the language stored in the project; other maintained languages are listed as
a gap.
