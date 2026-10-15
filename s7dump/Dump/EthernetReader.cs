using System.Globalization;
using System.Text;
using System.Text.Json.Nodes;

namespace S7Dump;

/// <summary>
/// Ethernet settings of every CPU and CP, read from the project files without a list of hardware
/// type IDs. DotNetSiemensPLCToolBoxLibrary only links an interface to a
/// module whose type it knows, so many CPUs and CPs lose their IP address.
///
/// <list type="number">
/// <item><c>S7Netze/S7NONFGX.tab</c>: one record per Ethernet node (marker <c>03 52 14 00</c>, node
/// number as Int32 after it). Inside a record each field is a two-byte ID written twice
/// (<c>E0 0F 00 00 E0 0F 00 00</c> = IP); the value's length byte is at +19 and the text at +20
/// (IP and mask as 8 hex digits, MAC as 12). Same layout the library reads.</item>
/// <item><c>hOmSave7/*/HRELATI1.DBF</c>: relation 64 links an interface object to its node.</item>
/// <item><c>hOmSave7/*/HOBJECT1.DBF</c>: every hardware object with its parent
/// (<c>UNITTYP</c>, <c>UNITID</c>), name, module and submodule number. Walking up the parents of
/// the interface gives the module (first object with a module number and no submodule number),
/// its rack and the station. A module of a PROFINET IO device (drive, ET 200, ...) has a device
/// number (<c>SUBSTATN</c> &gt; 0) and sits below its IO system instead of a rack.</item>
/// </list>
/// A node no hardware object links to (a PG/PC station of the network configuration) has no
/// station and no module; its <c>interface</c> is its name in the network table.
/// Everything is read-only; unreadable parts are reported, never fatal.
/// </summary>
public static class EthernetReader
{
    private static readonly byte[] RecordMarker = [0x03, 0x52, 0x14, 0x00];
    private const int RecordWindow = 1705;
    private const int RelationInterfaceToNode = 64;
    private static readonly byte[] NameField = [0x01, 0x10, 0x00, 0x00, 0x01, 0x10, 0x00, 0x00];

    private static readonly Dictionary<string, ushort> Fields = new()
    {
        ["ip"] = 0x0FE0, ["mask"] = 0x0FE5, ["router"] = 0x0FE3, ["mac"] = 0x0FA2,
        ["use_router"] = 0x0FE8, ["use_ip"] = 0x0FEA, ["use_iso"] = 0x0FED,
    };

    public sealed record Interface(
        int Node, string? Station, int? Rack, int? Slot, string? Module, string? InterfaceName,
        string? Ip, string? Mask, string? Router, string? Mac, bool? UseRouter, bool? UseIp, bool? UseIso,
        string? IoSystem = null, int? Device = null)
    {
        /// <summary>IP with prefix length (<c>192.168.1.25/24</c>) when the mask is contiguous.</summary>
        public string? Cidr()
        {
            if (Ip is null) return null;
            if (Mask is null || !System.Net.IPAddress.TryParse(Mask, out var m)) return Ip;
            var bits = m.GetAddressBytes().Aggregate(0u, (acc, b) => (acc << 8) | b);
            var prefix = 0;
            while (prefix < 32 && (bits & (0x80000000u >> prefix)) != 0) prefix++;
            return bits == (prefix == 0 ? 0u : uint.MaxValue << (32 - prefix)) ? $"{Ip}/{prefix}" : Ip;
        }

        public JsonObject ToJson() => new()
        {
            ["node"] = Node, ["station"] = Station, ["rack"] = Rack, ["slot"] = Slot,
            ["module"] = Module, ["interface"] = InterfaceName, ["io_system"] = IoSystem,
            ["device"] = Device, ["ip"] = Ip, ["mask"] = Mask,
            ["router"] = Router, ["mac"] = Mac, ["use_router"] = UseRouter, ["use_ip"] = UseIp,
            ["use_iso"] = UseIso,
        };
    }

    public static List<Interface> Read(string projectDir, Action<string, string> error)
    {
        var result = new List<Interface>();
        var tab = FindFile(Path.Combine(projectDir, "S7Netze"), "S7NONFGX.tab");
        if (tab is null) return result;  // no network configuration at all
        Dictionary<int, Dictionary<string, object?>> nodes;
        try
        {
            nodes = ReadNodes(File.ReadAllBytes(tab));
        }
        catch (Exception e)
        {
            error("S7Netze/S7NONFGX.tab", $"{e.GetType().Name}: {e.Message}");
            return result;
        }
        if (nodes.Count == 0) return result;

        var objects = new Dictionary<(long Type, long Id), Dictionary<string, string>>();
        var links = new List<((long Type, long Id) Interface, int Node)>();
        var hw = Path.Combine(projectDir, "hOmSave7");
        foreach (var dir in Directory.Exists(hw) ? Directory.EnumerateDirectories(hw) : [])
        {
            try
            {
                if (FindFile(dir, "HOBJECT1.DBF") is { } objectFile)
                {
                    foreach (var row in Dbf.Read(objectFile))
                    {
                        if (Num(row, "OBJTYP") is { } t && Num(row, "ID") is { } id) objects[(t, id)] = row;
                    }
                }
                if (FindFile(dir, "HRELATI1.DBF") is { } relationFile)
                {
                    foreach (var row in Dbf.Read(relationFile))
                    {
                        if (Num(row, "RELID") == RelationInterfaceToNode
                            && Num(row, "SOBJTYP") is { } t && Num(row, "SOBJID") is { } id
                            && Num(row, "TOBJID") is { } node && nodes.ContainsKey((int)node))
                        {
                            links.Add(((t, id), (int)node));
                        }
                    }
                }
            }
            catch (Exception e)
            {
                error($"hOmSave7/{Path.GetFileName(dir)}", $"{e.GetType().Name}: {e.Message}");
            }
        }

        var linked = new HashSet<int>();
        foreach (var (iface, node) in links.Distinct())
        {
            linked.Add(node);
            result.Add(Build(node, nodes[node], iface, objects));
        }
        foreach (var (node, values) in nodes.Where(n => !linked.Contains(n.Key)))
        {
            result.Add(Build(node, values, null, objects));  // node without a module link
        }
        return result
            .OrderBy(i => i.Station, StringComparer.Ordinal)
            .ThenBy(i => i.Device ?? 0).ThenBy(i => i.Rack).ThenBy(i => i.Slot).ThenBy(i => i.Node)
            .ToList();
    }

    /// <summary>Puts the nodes of the network table into the dump's <c>networks</c>. A node with a
    /// module replaces the library's Ethernet entry of that module: the one of the same station,
    /// or the one the library reports without a station for the same IP address (seen: CP 443-1
    /// Advanced, listed twice before). A node no module owns (PG/PC station) is added under its
    /// name in the network table.</summary>
    public static void ReplaceIn(List<JsonObject> networks, IEnumerable<Interface> ethernet)
    {
        foreach (var i in ethernet.Where(i => i.Ip is not null))
        {
            if (i.Module is not null && i.Device is null)
            {
                networks.RemoveAll(n => (string?)n["kind"] == "ethernet" && (string?)n["node"] == i.Module
                    && ((string?)n["station"] == i.Station
                        || (n["station"] is null && ((string?)n["address"])?.Split('/')[0] == i.Ip)));
            }
            networks.Add(new JsonObject
            {
                ["kind"] = "ethernet", ["subnet"] = null,
                ["node"] = i.Module ?? i.InterfaceName ?? $"node {i.Node}",
                ["station"] = i.Module is null ? null : i.Station,
                ["device"] = i.Module is null ? null : i.Device,
                ["address"] = i.Cidr(), ["device_name"] = null,
            });
        }
    }

    private static Interface Build(
        int node, Dictionary<string, object?> v, (long Type, long Id)? iface,
        Dictionary<(long Type, long Id), Dictionary<string, string>> objects)
    {
        string? module = null, interfaceName = null, station = null, ioSystem = null;
        int? slot = null, rack = null, device = null;
        var chain = new List<Dictionary<string, string>>();
        var seen = new HashSet<(long, long)>();
        var key = iface;
        while (key is { } k && seen.Add(k) && objects.TryGetValue(k, out var row))
        {
            chain.Add(row);
            key = Num(row, "UNITTYP") is { } pt && Num(row, "UNITID") is { } pid && pid > 0 ? (pt, pid) : null;
        }
        if (chain.Count > 0)
        {
            interfaceName = Text(chain[0], "NAME");
            var moduleIndex = chain.FindIndex(r => Num(r, "MODULN") > 0 && (Num(r, "SUBMODN") ?? 0) <= 0);
            if (moduleIndex >= 0)
            {
                module = Text(chain[moduleIndex], "NAME");
                slot = (int?)Num(chain[moduleIndex], "MODULN");
                if (Num(chain[moduleIndex], "SUBSTATN") is { } d && d > 0)
                {
                    // PROFINET IO device: slot is a slot of the device; the IO system is the first
                    // ancestor with an IO system number and no device number
                    device = (int)d;
                    ioSystem = chain.Skip(moduleIndex + 1)
                        .Where(r => Num(r, "DPSUBSN") > 0 && (Num(r, "SUBSTATN") ?? 0) <= 0)
                        .Select(r => HardwareReader.IoSystemName(Text(r, "NAME")))
                        .FirstOrDefault();
                }
                else if (moduleIndex + 1 < chain.Count && Num(chain[moduleIndex + 1], "MODULN") is { } r && r >= 0)
                {
                    rack = (int)r;
                }
            }
            station = Text(chain[^1], "NAME");
        }
        else
        {
            // no hardware object owns the node (the interface of a PG/PC station in the network
            // configuration): it keeps the name the network table has for it
            interfaceName = v.GetValueOrDefault("name") as string;
        }
        return new Interface(
            node, station, device is null ? rack ?? (slot is null ? null : 0) : null, slot, module, interfaceName,
            v.GetValueOrDefault("ip") as string, v.GetValueOrDefault("mask") as string,
            v.GetValueOrDefault("router") as string, v.GetValueOrDefault("mac") as string,
            v.GetValueOrDefault("use_router") as bool?, v.GetValueOrDefault("use_ip") as bool?,
            v.GetValueOrDefault("use_iso") as bool?, ioSystem, device);
    }

    public static Dictionary<int, Dictionary<string, object?>> ReadNodes(byte[] buf)
    {
        var nodes = new Dictionary<int, Dictionary<string, object?>>();
        for (var pos = IndexOf(buf, RecordMarker, 0, buf.Length); pos >= 0;
             pos = IndexOf(buf, RecordMarker, pos + 1, buf.Length))
        {
            if (pos + 8 > buf.Length) break;
            var number = BitConverter.ToInt32(buf, pos + 4);
            var end = Math.Min(buf.Length, pos + RecordWindow);
            var values = new Dictionary<string, object?>();
            foreach (var (name, id) in Fields)
            {
                var lo = (byte)(id & 0xFF);
                var hi = (byte)(id >> 8);
                byte[] pattern = [lo, hi, 0, 0, lo, hi, 0, 0];
                var p = IndexOf(buf, pattern, pos, end);
                if (p < 0 || p + 20 > buf.Length) continue;
                if (name.StartsWith("use_", StringComparison.Ordinal))
                {
                    values[name] = buf[p + 19] != 0;
                    continue;
                }
                var length = buf[p + 19];
                if (p + 20 + length > buf.Length) continue;
                var text = Encoding.ASCII.GetString(buf, p + 20, length);
                values[name] = name == "mac" ? Mac(text) : Ip(text);
            }
            if (NodeName(buf, pos, end) is { } nodeName) values["name"] = nodeName;
            if (values.ContainsKey("ip") || values.ContainsKey("mac")) nodes[number] = values;
        }
        return nodes;
    }

    /// <summary>The node's module name (field <c>0x1001</c>): unlike the address fields it has a
    /// length-prefixed label ("Baugruppenname") between the ID and the value.</summary>
    private static string? NodeName(byte[] buf, int start, int end)
    {
        var p = IndexOf(buf, NameField, start, end);
        if (p < 0 || p + 8 >= buf.Length) return null;
        var length = p + 9 + buf[p + 8] + 10;  // label, then the same 10 bytes as before an address
        if (length >= buf.Length || length + 1 + buf[length] > buf.Length) return null;
        var text = Encoding.Latin1.GetString(buf, length + 1, buf[length]).Trim();
        return text.Length > 0 ? text : null;
    }

    private static string? Ip(string hex)
    {
        if (hex.Length != 8 || !uint.TryParse(hex, NumberStyles.HexNumber, CultureInfo.InvariantCulture, out _))
        {
            return null;
        }
        return string.Join('.', Enumerable.Range(0, 4).Select(i => Convert.ToByte(hex.Substring(i * 2, 2), 16)));
    }

    private static string? Mac(string hex) =>
        hex.Length == 12 && hex.All(Uri.IsHexDigit)
            ? string.Join('-', Enumerable.Range(0, 6).Select(i => hex.Substring(i * 2, 2).ToUpperInvariant()))
            : null;

    private static int IndexOf(byte[] buf, byte[] pattern, int start, int end)
    {
        for (var i = Math.Max(0, start); i + pattern.Length <= end; i++)
        {
            var match = true;
            for (var j = 0; j < pattern.Length && match; j++) match = buf[i + j] == pattern[j];
            if (match) return i;
        }
        return -1;
    }

    private static string? FindFile(string dir, string name) =>
        Directory.Exists(dir)
            ? Directory.EnumerateFiles(dir).FirstOrDefault(f => Path.GetFileName(f).Equals(name, StringComparison.OrdinalIgnoreCase))
            : null;

    private static long? Num(Dictionary<string, string> row, string field) =>
        row.TryGetValue(field, out var s) && long.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var n)
            ? n
            : null;

    private static string? Text(Dictionary<string, string> row, string field) =>
        row.TryGetValue(field, out var s) && s.Length > 0 ? s : null;
}

/// <summary>Minimal read-only dBase III reader for STEP 7's project tables (memo fields as their
/// block number in the .DBT).
/// Text is decoded as Windows-1252, as STEP 7 V5.x writes it.</summary>
public static class Dbf
{
    private static readonly Encoding Latin = Encoding.Latin1;

    public static List<Dictionary<string, string>> Read(string path)
    {
        var raw = File.ReadAllBytes(path);
        var count = BitConverter.ToInt32(raw, 4);
        int headerLength = BitConverter.ToUInt16(raw, 8), recordLength = BitConverter.ToUInt16(raw, 10);
        var fields = new List<(string Name, char Type, int Offset, int Length)>();
        int offset = 1, pos = 32;
        while (pos + 32 <= raw.Length && raw[pos] != 0x0D)
        {
            var name = Encoding.ASCII.GetString(raw, pos, 11).TrimEnd('\0', ' ');
            fields.Add((name, (char)raw[pos + 11], offset, raw[pos + 16]));
            offset += raw[pos + 16];
            pos += 32;
        }
        var rows = new List<Dictionary<string, string>>();
        for (var i = 0; i < count; i++)
        {
            var start = headerLength + i * recordLength;
            if (start + recordLength > raw.Length) break;
            if (raw[start] == (byte)'*') continue;  // deleted
            var row = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (var f in fields)
            {
                if (f.Type is 'B' or 'G') continue;  // memo fields ('M') keep their block number
                var text = Latin.GetString(raw, start + f.Offset, f.Length);
                var nul = text.IndexOf('\0');
                row[f.Name] = (nul >= 0 ? text[..nul] : text).Trim();
            }
            rows.Add(row);
        }
        return rows;
    }
}
