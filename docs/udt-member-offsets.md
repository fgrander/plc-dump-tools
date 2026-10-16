# A data type in the export (STEP 7 classic)

Extends [`common-format.md`](common-format.md) (interface members, `offset`).

## File `datatypes/<name>.md`

Front matter, one flow-style line per member, `offset` first:

```yaml
interface:
- {offset: '0.0', name: Enable, type: BOOL, start: 'False'}
- {offset: '1.0', name: Mode, type: BYTE, start: B#16#0}
- {offset: '2.0', name: Speed, type: INT, start: '0'}
- {offset: '4.0', name: Limits, type: STRUCT, members: [
    {offset: '4.0', name: Max, type: REAL}, {offset: '8.0', name: Min, type: REAL}]}
```

Table, `Offset` as the first column, same as for a data block:

```markdown
## Members
| Offset | Section | Name | Type | Start | Comment |
|---|---|---|---|---|---|
| 0.0 |  | Enable | BOOL | False |  |
| 1.0 |  | Mode | BYTE | B#16#0 |  |
| 2.0 |  | Speed | INT | 0 |  |
| 4.0 |  | Limits | STRUCT |  |  |
| 4.0 |  | Limits.Max | REAL |  |  |
| 8.0 |  | Limits.Min | REAL |  |  |
```

## Rules

1. **Meaning**: `offset` of a data type member is `byte.bit` from the start of the data type.
   Nested members count from the start of the outermost type.
2. **Order**: members by ascending offset (byte, then bit).
3. **Consistency**: for a data block member `M` of this type at offset `m`, the export lists
   `M.<x>` in the data block at `m + offset(<x>)` (byte and bit added, bits carried at 8).
4. **No reliable layout**: the type has no `offset` key on any member, the table has no
   `Offset` column, the members are in declaration order, and `coverage.json` carries a warning
   `udt_layout_mismatch` with the type as unit and the reason.
5. **Never estimated**: an offset is either the layout read from the project and checked, or
   absent.
6. **Nothing else changes**: every other file of the export is the same as before, byte for
   byte, except lines that hold a checksum over the changed files.

## Warning

| Code | Unit | Message (examples) |
|---|---|---|
| `udt_layout_mismatch` | the data type | `UDT_Text: Lines is an array of odd-length strings, which the library lays out without their fill bytes; members exported without offsets` · `UDT_Net: reset_request at 25.0 follows port and has to start on an even byte; members exported without offsets` · `UDT_Drive: DB_Line lists Motor.Speed at 14.0, the type says 2.0 after 10.0; members exported without offsets` |

## Compatibility

- Additive in common format v1: `offset` is an existing optional member key; readers that do not
  know it for data types ignore it.
- Exports of data types change once (column and order). `format_version` stays `1`.
