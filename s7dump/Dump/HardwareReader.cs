using System.Globalization;
using System.Text;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace S7Dump;

/// <summary>
/// Every module of the hardware configuration with its I/O addresses, read from the
/// project's HW Config tables without hardware type lists or GSD files:
/// <list type="bullet">
/// <item><c>hOmSave7/*/HOBJECT1.DBF</c>: the object tree. Station &gt; central rack (slot =
/// <c>MODULN</c>) or IO system (DP master system / PROFINET IO system, <c>DPSUBSN</c>) &gt; device
/// (<c>SUBSTATN</c> = PROFIBUS address or device number) &gt; module &gt; submodule
/// (<c>SUBMODN</c>).</item>
/// <item><c>hOmSave7/*/HATTRIB1.DBF</c>: attribute 110970 (display name of GSD modules whose
/// object name is a number) and 4098 (catalog key, e.g. <c>_S7H_6ES7_323_1BH00_0AA~</c>).</item>
/// <item><c>hOmSave7/s7hstatx/HADDRES3.DBF</c> + <c>.DBT</c>: input and output address lists; an
/// entry is 36 bytes: object type and id, rack type and id, project type and id, 1, start + 1,
/// start (UInt16), length in bytes (UInt16).</item>
/// <item><c>hOmSave7/s7hstatx/&lt;station id hex&gt;.s7h</c>: the station's HW Config table
/// (slot, module, order number, firmware, ...) with full order numbers.</item>
/// </list>
/// A module is an object with a slot and no submodule number; a submodule with its own I/O
/// (e.g. the DI16/DO16 of a CPU 313C) is listed as a module too. Read-only; never fatal.
/// </summary>
public static class HardwareReader
{
    private const string AttrDisplayName = "110970";
    private const string AttrCatalog = "4098";
    private static readonly Regex CatalogOrderNo =
        new(@"^_S7H_(\d[A-Z0-9]{3})_([A-Z0-9]{3})_([A-Z0-9]{5})_([A-Z0-9]{4})$", RegexOptions.CultureInvariant);

    private sealed record Range(int Start, int Length);

    private sealed class Obj
    {
        public required (long Type, long Id) Key;
        public required Dictionary<string, string> Row;
        public string Name => Text("NAME") ?? "";
        public long Num(string f) => long.TryParse(Row.GetValueOrDefault(f), NumberStyles.Integer, CultureInfo.InvariantCulture, out var n) ? n : -1;
        public string? Text(string f) => Row.TryGetValue(f, out var s) && s.Length > 0 ? s : null;
        public (long, long)? Parent => Num("UNITID") > 0 ? (Num("UNITTYP"), Num("UNITID")) : null;
        public string? Display;
        public string? Catalog;
        public List<Range> Inputs { get; } = [];
        public List<Range> Outputs { get; } = [];
    }

    public static JsonArray Read(string projectDir, Action<string, string> error,
        IReadOnlyList<EthernetReader.Interface>? ethernet = null)
    {
        ethernet ??= [];
        var result = new JsonArray();
        var hw = Path.Combine(projectDir, "hOmSave7");
        if (!Directory.Exists(hw)) return result;
        var objects = new Dictionary<(long, long), Obj>();
        foreach (var dir in Directory.EnumerateDirectories(hw))
        {
            try
            {
                var byId = new Dictionary<string, Obj>();
                if (Find(dir, "HOBJECT1.DBF") is { } objectFile)
                {
                    foreach (var row in Dbf.Read(objectFile))
                    {
                        if (!long.TryParse(row.GetValueOrDefault("OBJTYP"), out var t)
                            || !long.TryParse(row.GetValueOrDefault("ID"), out var id)) continue;
                        var o = new Obj { Key = (t, id), Row = row };
                        objects[(t, id)] = o;
                        byId[row["ID"]] = o;
                    }
                }
                if (Find(dir, "HATTRIB1.DBF") is { } attributeFile)
                {
                    foreach (var a in Dbf.Read(attributeFile))
                    {
                        if (!byId.TryGetValue(a.GetValueOrDefault("IDA") ?? "", out var o)) continue;
                        var value = a.GetValueOrDefault("STRINGVAL");
                        if (string.IsNullOrEmpty(value)) continue;
                        if (a.GetValueOrDefault("ATTRIID") == AttrDisplayName) o.Display = value;
                        else if (a.GetValueOrDefault("ATTRIID") == AttrCatalog) o.Catalog = value;
                    }
                }
            }
            catch (Exception e)
            {
                error($"hOmSave7/{Path.GetFileName(dir)}", $"{e.GetType().Name}: {e.Message}");
            }
        }
        ReadAddresses(Path.Combine(hw, "s7hstatx"), objects, error);
        var tables = ReadStationTables(Path.Combine(hw, "s7hstatx"), error, out var deviceLists);

        Obj? Up(Obj o) => o.Parent is { } p && objects.TryGetValue(p, out var parent) ? parent : null;
        List<Obj> Chain(Obj o)
        {
            var chain = new List<Obj>();
            var seen = new HashSet<(long, long)>();
            for (Obj? x = o; x is not null && seen.Add(x.Key); x = Up(x)) chain.Add(x);
            return chain;
        }

        foreach (var o in objects.Values)
        {
            var slot = o.Num("MODULN");
            var sub = o.Num("SUBMODN");
            var isModule = slot > 0 && sub <= 0;
            var isIoSubmodule = slot > 0 && sub > 0 && o.Inputs.Concat(o.Outputs).Any(r => r.Length > 0);  // not diagnostics only
            if (!isModule && !isIoSubmodule) continue;
            var chain = Chain(o);
            var station = chain[^1].Name;
            var device = o.Num("SUBSTATN") > 0 ? o.Num("SUBSTATN") : (long?)null;
            string? ioSystem = null, deviceName = null;
            int? rack = null;
            if (device is not null)
            {
                // the device: a DP slave object, or a PROFINET device container (internal name, so
                // the device is named after its first module, the interface module)
                var deviceObj = chain.Skip(1).FirstOrDefault(c => c.Num("SUBSTATN") == device && c.Num("MODULN") <= 0);
                ioSystem = IoSystemName(chain.FirstOrDefault(c => c.Num("DPSUBSN") > 0 && c.Num("SUBSTATN") <= 0)?.Name);
                deviceName = deviceObj?.Name;
                if (deviceObj is not null && deviceObj.Name.StartsWith("_S7H_", StringComparison.Ordinal))
                {
                    deviceName = objects.Values
                        .Where(c => c.Parent == deviceObj.Key && c.Num("MODULN") > 0 && c.Num("SUBMODN") <= 0)
                        .OrderBy(c => c.Num("MODULN")).FirstOrDefault()?.Name;
                }
            }
            else if (chain.Skip(1).Any(c => c.Num("MODULN") == 0 && c.Num("SUBSTATN") == 0 && c.Num("DPSUBSN") == 0))
            {
                rack = 0;  // central rack; expansion racks are not told apart yet
            }
            var name = o.Name.Trim().All(char.IsDigit) && o.Display is not null ? o.Display : o.Name;
            string? orderNo = null, firmware = null;
            if (device is null && tables.TryGetValue(chain[^1].Key.Item2, out var rows)
                && rows.FirstOrDefault(r => r.Slot == SlotText(slot, sub) && r.Name == o.Name) is { } t)
            {
                orderNo = t.OrderNo;
                firmware = t.Firmware;
            }
            if (orderNo is null && o.Catalog is not null && CatalogOrderNo.Match(o.Catalog) is { Success: true } m)
            {
                orderNo = $"{m.Groups[1]} {m.Groups[2]}-{m.Groups[3]}-{m.Groups[4]}";
            }
            if (orderNo is null && device is not null && tables.TryGetValue(chain[^1].Key.Item2, out var stationRows))
            {
                orderNo = DeviceOrderNo(o, stationRows);
            }
            if (device is not null && sub <= 0 && deviceLists.TryGetValue(chain[^1].Key.Item2, out var devices))
            {
                // a device head's row of the IO system's device list, by IP address or name
                var ip = ethernet.FirstOrDefault(i => i.Ip is not null && i.Station == station
                    && i.IoSystem == ioSystem && i.Device == device && i.Slot == slot)?.Ip;
                var ipUsers = ip is null ? 0 : ethernet.Count(i => i.Ip == ip && i.Device is not null);
                if (DeviceListRow(o.Name.Trim(), ip, ipUsers, devices) is { } row)
                {
                    orderNo ??= row.OrderNo;
                    firmware ??= row.Firmware;
                }
            }
            var inputs = new List<Range>(o.Inputs);
            var outputs = new List<Range>(o.Outputs);
            result.Add(new JsonObject
            {
                ["key"] = $"{o.Key.Item1}:{o.Key.Item2}",
                ["station"] = station,
                ["rack"] = rack,
                ["io_system"] = ioSystem,
                ["device"] = device,
                ["device_name"] = deviceName,
                ["slot"] = slot,
                ["subslot"] = sub > 0 ? sub : null,
                ["name"] = name,
                ["catalog"] = o.Catalog,
                ["order_no"] = orderNo,
                ["firmware"] = firmware,
                ["inputs"] = Ranges(inputs),
                ["outputs"] = Ranges(outputs),
            });
        }
        return new JsonArray(result
            .OrderBy(n => (string?)n!["station"], StringComparer.Ordinal)
            .ThenBy(n => (string?)n!["io_system"] ?? "", StringComparer.Ordinal)
            .ThenBy(n => (long?)n!["device"] ?? 0)
            .ThenBy(n => (long?)n!["slot"] ?? 0)
            .ThenBy(n => (long?)n!["subslot"] ?? 0)
            .Select(n => n!.DeepClone()).ToArray());
    }

    /// <summary>Name of a DP master system or PROFINET IO system; older projects store only an
    /// internal catalog name there.</summary>
    public static string? IoSystemName(string? name) => name switch
    {
        null => null,
        _ when name.Contains("DPSUBSYSTEM", StringComparison.Ordinal) => "DP-Mastersystem",
        _ when name.Contains("IO_SUBSYSTEM", StringComparison.Ordinal) => "PROFINET-IO-System",
        _ => name,
    };

    private static JsonArray Ranges(IEnumerable<Range> ranges) =>
        new(ranges.Where(r => r.Length > 0).Distinct().OrderBy(r => r.Start)
            .Select(r => (JsonNode)new JsonObject { ["start"] = r.Start, ["length"] = r.Length }).ToArray());

    private static string SlotText(long slot, long sub) => sub > 0 ? $"{slot}.{sub}" : slot.ToString(CultureInfo.InvariantCulture);

    /// <summary>Input and output address lists; each entry is attached to the object it names.</summary>
    private static void ReadAddresses(string dir, Dictionary<(long, long), Obj> objects, Action<string, string> error)
    {
        try
        {
            if (Find(dir, "HADDRES3.DBF") is not { } table) return;
            var memo = Find(dir, "HADDRES3.DBT") is { } dbt ? File.ReadAllBytes(dbt) : [];
            foreach (var row in Dbf.Read(table))
            {
                var name = row.GetValueOrDefault("LISTNAME") ?? "";
                var input = name.Contains("INADDR", StringComparison.OrdinalIgnoreCase);
                var output = name.Contains("OUTADDR", StringComparison.OrdinalIgnoreCase);
                if (!input && !output) continue;
                if (!int.TryParse(row.GetValueOrDefault("LISTCOUNT"), out var count)
                    || !int.TryParse(row.GetValueOrDefault("LISTLEN"), out var length)
                    || !int.TryParse(row.GetValueOrDefault("MEMOARRAYA"), out var block)
                    || length < 36) continue;
                var start = block * 512 + 8;  // dBase III memo block; 8-byte header (FF FF 08 00, length)
                for (var i = 0; i < count; i++)
                {
                    var e = start + i * length;
                    if (e + 36 > memo.Length) break;
                    var key = ((long)BitConverter.ToUInt32(memo, e), (long)BitConverter.ToUInt32(memo, e + 4));
                    var range = new Range(BitConverter.ToUInt16(memo, e + 32), BitConverter.ToUInt16(memo, e + 34));
                    if (!objects.TryGetValue(key, out var o)) continue;
                    (input ? o.Inputs : o.Outputs).Add(range);
                }
            }
        }
        catch (Exception e)
        {
            error("hOmSave7/s7hstatx/HADDRES3", $"{e.GetType().Name}: {e.Message}");
        }
    }

    /// <summary><paramref name="Designation"/>: the row is in a DP slave table whose order number
    /// column holds the DP ID designation of GSD modules (e.g. <c>I/O 28 Wrd</c>).</summary>
    public sealed record TableRow(string Slot, string Name, string? OrderNo, string? Firmware, bool Designation = false);

    private static readonly Regex CatalogOrderStart =
        new(@"_(\d[A-Z]{2}\d)_([A-Z0-9_]*)~?$", RegexOptions.CultureInvariant);
    private static readonly Regex DpIdColumn =
        new(@"^DP[- ]?(ID|Kennung)$", RegexOptions.CultureInvariant | RegexOptions.IgnoreCase);

    /// <summary>Order number of a module of a DP slave or IO device, from the rows of its
    /// station's tables: the rows with its name, when they agree on one order number (a shortened
    /// catalog key must be its start; DP ID designations count only with that confirmation), else
    /// the access point row (slot 0) of a PROFINET device, whose name is the device name: the
    /// module name in lower case. Never guessed.</summary>
    public static string? DeviceOrderNo(string name, string? catalog, string? display, IReadOnlyList<TableRow> rows)
    {
        var start = catalog is not null && CatalogOrderStart.Match(catalog) is { Success: true } m
            ? m.Groups[1].Value + m.Groups[2].Value.Replace("_", "")
            : null;
        bool Usable(TableRow r) =>
            r.OrderNo is { } order && order != display?.Trim()
            && (start is null ? !r.Designation : Compact(order).StartsWith(start, StringComparison.Ordinal));
        var orders = rows.Where(r => r.Name == name && Usable(r)).Select(r => r.OrderNo!).Distinct().ToList();
        if (orders.Count == 0)
        {
            orders = rows.Where(r => r.Slot == "0" && string.Equals(r.Name, name, StringComparison.OrdinalIgnoreCase) && Usable(r))
                .Select(r => r.OrderNo!).Distinct().ToList();
        }
        return orders.Count == 1 ? orders[0] : null;
    }

    private static string? DeviceOrderNo(Obj o, IReadOnlyList<TableRow> rows) =>
        DeviceOrderNo(o.Name.Trim(), o.Catalog, o.Display, rows);

    /// <summary>A row of an IO system's device list: number, device name, number, IP address,
    /// device name, order number, firmware, ... (the number is not always the device number).</summary>
    public sealed record DeviceRow(string Name, string? Ip, string? OrderNo, string? Firmware);

    private static readonly Regex Ipv4 = new(@"^\d{1,3}(\.\d{1,3}){3}$", RegexOptions.CultureInvariant);

    /// <summary>The device list row of a PROFINET device head: the only row with the
    /// device's IP address, when no other device has it (<paramref name="ipUsers"/>), else the
    /// only row whose device name is the head's module name ignoring case. Never guessed.</summary>
    public static DeviceRow? DeviceListRow(string head, string? ip, int ipUsers, IReadOnlyList<DeviceRow> rows)
    {
        if (ip is not null && ipUsers == 1 && rows.Where(r => r.Ip == ip).ToList() is [var byIp]) return byIp;
        return rows.Where(r => string.Equals(r.Name, head, StringComparison.OrdinalIgnoreCase)).ToList() is [var byName]
            ? byName
            : null;
    }

    /// <summary>The device list rows of a table file (recognized by the device name in the second
    /// and fifth column and an IP address or blank in the fourth).</summary>
    public static List<DeviceRow> ReadDeviceRows(byte[] file)
    {
        var rows = new List<DeviceRow>();
        foreach (var run in Runs(file))
        {
            var cells = run.Select(c => c.Trim()).ToList();
            if (cells.Count < 7 || cells[0] != cells[2] || !cells[0].All(char.IsDigit) || cells[0].Length == 0
                || cells[1].Length == 0 || cells[1] != cells[4] || cells[1] == cells[3]
                || (cells[3].Length > 0 && !Ipv4.IsMatch(cells[3]))) continue;
            rows.Add(new DeviceRow(cells[1], cells[3].Length > 0 ? cells[3] : null,
                cells[5].Length > 0 ? cells[5] : null, cells[6].Length > 0 ? cells[6] : null));
        }
        return rows;
    }

    private static string Compact(string order) => order.Replace(" ", "").Replace("-", "");

    /// <summary>HW Config table files (<c>&lt;station id hex&gt;.s7h</c>): runs of length-prefixed
    /// strings, one run per row: slot, module, slot, module, order number, firmware, MPI address,
    /// I address, Q address, comment. Besides the central rack, the file holds one table per DP
    /// slave and IO device; each table's rows are followed by its header row.</summary>
    private static Dictionary<long, List<TableRow>> ReadStationTables(string dir, Action<string, string> error,
        out Dictionary<long, List<DeviceRow>> deviceLists)
    {
        var tables = new Dictionary<long, List<TableRow>>();
        deviceLists = [];
        if (!Directory.Exists(dir)) return tables;
        foreach (var file in Directory.EnumerateFiles(dir, "*.s7h"))
        {
            if (!long.TryParse(Path.GetFileNameWithoutExtension(file), NumberStyles.HexNumber, CultureInfo.InvariantCulture, out var id)) continue;
            try
            {
                var bytes = File.ReadAllBytes(file);
                tables[id] = ReadTableRows(bytes);
                deviceLists[id] = ReadDeviceRows(bytes);
            }
            catch (Exception e)
            {
                error($"hOmSave7/s7hstatx/{Path.GetFileName(file)}", $"{e.GetType().Name}: {e.Message}");
            }
        }
        return tables;
    }

    /// <summary>The rows of a table file. A header row (its first column a title such as
    /// <c>Slot</c> or <c>Steckplatz</c>) closes the table above it; a <c>DP ID</c> column in it
    /// marks the order numbers of that table as possible designations.</summary>
    public static List<TableRow> ReadTableRows(byte[] file)
    {
        var rows = new List<TableRow>();
        var table = new List<TableRow>();
        foreach (var run in Runs(file))
        {
            if (run[0].Trim() == run[2].Trim() && run[1] == run[3])
            {
                var order = run[4].Trim();
                var firmware = run[5].Trim();
                table.Add(new TableRow(run[0].Trim().Replace(' ', '.'), run[1].Trim(),
                    order.Length > 0 ? order : null, firmware.Length > 0 ? firmware : null));
            }
            else if (run[0].Any(char.IsLower))
            {
                var designation = run.Any(c => DpIdColumn.IsMatch(c.Trim()));
                rows.AddRange(table.Select(r => r with { Designation = designation }));
                table.Clear();
            }
        }
        rows.AddRange(table);
        return rows;
    }

    private static IEnumerable<List<string>> Runs(byte[] b)
    {
        var run = new List<string>();
        for (var i = 0; i < b.Length;)
        {
            int n = b[i];
            if (n > 0 && n < 80 && i + 1 + n <= b.Length && b.Skip(i + 1).Take(n).All(c => c >= 32 && c != 127))
            {
                run.Add(Encoding.Latin1.GetString(b, i + 1, n));
                i += 1 + n;
                continue;
            }
            if (run.Count >= 6) yield return run;
            run = [];
            i++;
        }
        if (run.Count >= 6) yield return run;
    }

    private static string? Find(string dir, string name) =>
        Directory.Exists(dir)
            ? Directory.EnumerateFiles(dir).FirstOrDefault(f => Path.GetFileName(f).Equals(name, StringComparison.OrdinalIgnoreCase))
            : null;
}
