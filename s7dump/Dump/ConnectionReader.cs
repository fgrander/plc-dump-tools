using System.Globalization;
using System.Text.Json.Nodes;

namespace S7Dump;

/// <summary>
/// Configured connections (NetPro) of a STEP 7 V5.x project, read from the project files
/// Nothing here opens a network connection: addresses are data.
///
/// <list type="number">
/// <item><c>CONN/VERBTAB.DBF</c>: one row per connection list (<c>ID</c> = n of <c>CONN/CO_n</c>,
/// <c>LINKID</c> = offset of the list's block in <c>CONN/LINKVL.dbf</c>).</item>
/// <item><c>CONN/CO_n/HOMOVERB.DBF</c>: one row per connection (<c>NAME</c>, <c>LOCALID</c>,
/// <c>AUFBAU</c> = active connection establishment, <c>EINSEITIG</c> = one-way, <c>UNSPEZ</c>,
/// <c>LFDNR</c> = local connection resource, <c>LINKID</c> = offset of the connection's block in
/// <c>CONN/CO_n/HOMOLINK.dbf</c>).</item>
/// <item><c>CONN/CO_n/HOMTABV4.DBF</c>: the partner of an unspecified connection (<c>UN_*</c>).</item>
/// <item>The two link files (magic <c>KNIL</c>, 512-byte blocks) hold object references of
/// 8 bytes: type and ID as UInt32. A list's block names the module that owns the list (a row of
/// <c>hOmSave7/*/HOBJECT1.DBF</c>); a connection's block names its network nodes
/// (type <c>0x00145203</c>, node numbers of <c>S7Netze/S7NONFGX.tab</c>).</item>
/// <item><c>sdb/*/*.PG</c>: the compiled record of a connection ends with local ID, active flag,
/// local TSAP, partner IP and partner TSAP (<see cref="ParseCompiledTail"/>).</item>
/// </list>
/// Deleted rows are skipped, personal columns (<c>CREATOR</c>) are never read, and unreadable
/// parts are reported, never fatal.
/// </summary>
public static class ConnectionReader
{
    private const uint NodeType = 0x00145203;
    private const int BlockSize = 512;
    private const int TailLength = 28;

    public sealed record Owner(string? Station, int? Rack, int? Slot, string? Module);

    public sealed record Compiled(
        string File, bool Active, int LocalId, string LocalTsap, string PartnerIp, string PartnerTsap);

    public sealed record Connection(
        int List, Owner? Owner, int? LocalNode, int? PartnerNode, string Name, long TypeId,
        int LocalId, bool? Active, bool? OneWay, bool Unspecified, int? LocalResource,
        string? PartnerName, int? PartnerRack, int? PartnerSlot, int? PartnerResource,
        string? PartnerIp, Compiled? Compiled)
    {
        public JsonObject ToJson() => new()
        {
            ["list"] = List,
            ["owner"] = Owner is null ? null : new JsonObject
            {
                ["station"] = Owner.Station, ["rack"] = Owner.Rack, ["slot"] = Owner.Slot,
                ["module"] = Owner.Module,
            },
            ["local_node"] = LocalNode,
            ["partner_node"] = PartnerNode,
            ["name"] = Name,
            ["type_id"] = TypeId,
            ["local_id"] = LocalId,
            ["active"] = Active,
            ["one_way"] = OneWay,
            ["unspecified"] = Unspecified,
            ["tables"] = new JsonObject
            {
                ["local_resource"] = LocalResource, ["partner_name"] = PartnerName,
                ["partner_rack"] = PartnerRack, ["partner_slot"] = PartnerSlot,
                ["partner_resource"] = PartnerResource, ["partner_ip"] = PartnerIp,
            },
            ["compiled"] = Compiled is null ? null : new JsonObject
            {
                ["file"] = Compiled.File, ["active"] = Compiled.Active,
                ["local_tsap"] = Compiled.LocalTsap, ["partner_ip"] = Compiled.PartnerIp,
                ["partner_tsap"] = Compiled.PartnerTsap,
            },
        };
    }

    public static List<Connection> Read(
        string projectDir, IReadOnlyList<EthernetReader.Interface> ethernet, Action<string, string> error)
    {
        var result = new List<Connection>();
        var conn = FindDir(projectDir, "CONN");
        var lists = conn is null ? null : FindFile(conn, "VERBTAB.DBF");
        if (conn is null || lists is null) return result;  // no connection configuration at all

        var objects = HardwareObjects(projectDir, error);
        var compiled = CompiledRecords(projectDir, error);
        var listLinks = ReadBytes(FindFile(conn, "LINKVL.dbf"), "CONN/LINKVL.dbf", error);
        List<Dictionary<string, string>> listRows;
        try
        {
            listRows = Dbf.Read(lists);
        }
        catch (Exception e)
        {
            error("CONN/VERBTAB.DBF", $"{e.GetType().Name}: {e.Message}");
            return result;
        }

        foreach (var list in listRows)
        {
            if (Num(list, "ID") is not { } listId) continue;
            var where = $"CONN/CO_{listId}";
            var dir = FindDir(conn, $"CO_{listId}");
            var table = dir is null ? null : FindFile(dir, "HOMOVERB.DBF");
            if (dir is null || table is null) continue;  // a list without connections
            try
            {
                var owner = OwnerOf(listLinks, Num(list, "LINKID"), objects);
                var partners = (FindFile(dir, "HOMTABV4.DBF") is { } partnerFile ? Dbf.Read(partnerFile) : [])
                    .Where(r => Num(r, "ID") is not null)
                    .GroupBy(r => Num(r, "ID")!.Value).ToDictionary(g => g.Key, g => g.First());
                var links = ReadBytes(FindFile(dir, "HOMOLINK.dbf"), $"{where}/HOMOLINK.dbf", error);
                foreach (var row in Dbf.Read(table))
                {
                    if (Num(row, "ID") is not { } id || Num(row, "LOCALID") is not { } localId) continue;
                    result.Add(Build((int)listId, row, (int)localId, partners.GetValueOrDefault(id), owner,
                        NodesOf(links, Num(row, "LINKID")), ethernet, compiled));
                }
            }
            catch (Exception e)
            {
                error(where, $"{e.GetType().Name}: {e.Message}");
            }
        }
        foreach (var c in result.Where(c => c.Owner is null))
        {
            error($"CONN/CO_{c.List}", $"connection {c.Name}: the module that owns the list was not found");
        }
        return result
            .OrderBy(c => c.List).ThenBy(c => c.LocalId).ThenBy(c => c.Name, StringComparer.Ordinal)
            .ToList();
    }

    private static Connection Build(
        int list, Dictionary<string, string> row, int localId, Dictionary<string, string>? partner,
        Owner? owner, List<int> nodes, IReadOnlyList<EthernetReader.Interface> ethernet,
        List<Compiled> compiled)
    {
        var unspecified = Num(row, "UNSPEZ") == 1;
        var localNode = nodes.Cast<int?>().FirstOrDefault(n => IsOwners(n!.Value, owner, ethernet));
        if (owner is null && nodes.Count == 1 && ethernet.FirstOrDefault(e => e.Node == nodes[0]) is { Module: not null } only)
        {
            // fallback: the list's module is the module of its only node
            owner = new Owner(only.Station, only.Rack, only.Slot, only.Module);
            localNode = nodes[0];
        }
        var partnerNode = unspecified ? null : nodes.Cast<int?>().FirstOrDefault(n => n != localNode);
        string? partnerIp = unspecified && partner is not null ? Ip(Text(partner, "UN_TNADR")) : null;
        var expectedIp = partnerIp ?? ethernet.FirstOrDefault(e => e.Node == partnerNode)?.Ip;
        return new Connection(
            list, owner, localNode, partnerNode, Text(row, "NAME") ?? "", Num(row, "TYPE") ?? 0, localId,
            Flag(row, "AUFBAU"), Flag(row, "EINSEITIG"), unspecified, (int?)Num(row, "LFDNR"),
            unspecified && partner is not null ? Text(partner, "UN_MODNAME") : null,
            unspecified && partner is not null ? (int?)Num(partner, "UN_RACKNO") : null,
            unspecified && partner is not null ? (int?)Num(partner, "UN_SLOTNO") : null,
            unspecified && partner is not null ? (int?)Num(partner, "UN_LFDNO") : null,
            partnerIp, Match(compiled, localId, owner, expectedIp));
    }

    /// <summary>The compiled record of a connection: same local ID, the owner's rack and slot in
    /// the local TSAP, and the partner address where one is known. A record that differs only in
    /// the partner address is still the connection's record when it is the only candidate (the
    /// project was changed after the last compile; the difference is reported downstream).</summary>
    public static Compiled? Match(IEnumerable<Compiled> records, int localId, Owner? owner, string? partnerIp)
    {
        var place = owner?.Slot is { } slot ? ((owner.Rack ?? 0) * 32 + slot).ToString("X2", CultureInfo.InvariantCulture) : null;
        var candidates = records
            .Where(r => r.LocalId == localId && (place is null || r.LocalTsap.EndsWith("." + place, StringComparison.Ordinal)))
            .ToList();
        var exact = partnerIp is null ? candidates : candidates.Where(r => r.PartnerIp == partnerIp).ToList();
        if (exact.Count == 1) return exact[0];
        return exact.Count == 0 && candidates.Count == 1 && place is not null ? candidates[0] : null;
    }

    /// <summary>The tail of a compiled connection record, or null when the bytes do not end with
    /// one: <c>1c 01 08 02 00 active 00 00 ID(2)</c>, <c>03 03 xx xx</c>, <c>04 04 TSAP(2)</c>,
    /// <c>06 06 IP(4)</c>, <c>04 07 TSAP(2)</c>.</summary>
    public static Compiled? ParseCompiledTail(byte[] bytes, string file = "")
    {
        if (bytes.Length < TailLength) return null;
        var t = bytes[^TailLength..];
        bool Marker(int at, byte a, byte b) => t[at] == a && t[at + 1] == b;
        if (!(t[0] == 0x1C && t[1] == 0x01 && t[2] == 0x08 && t[3] == 0x02 && t[4] == 0x00 && t[5] <= 1
              && Marker(10, 0x03, 0x03) && Marker(14, 0x04, 0x04) && Marker(18, 0x06, 0x06) && Marker(24, 0x04, 0x07)))
        {
            return null;
        }
        return new Compiled(
            file, t[5] == 1, (t[8] << 8) | t[9], Tsap(t[16], t[17]),
            string.Join('.', t[20], t[21], t[22], t[23]), Tsap(t[26], t[27]));
    }

    /// <summary>TSAP as two hex bytes with two digits each: <c>11.02</c> (NetPro shows the same
    /// value and drops a leading zero of the first byte).</summary>
    public static string Tsap(int first, int second) =>
        first.ToString("X2", CultureInfo.InvariantCulture) + "." + second.ToString("X2", CultureInfo.InvariantCulture);

    /// <summary>Object references (type, ID) of the 512-byte block at <paramref name="offset"/>
    /// of a <c>KNIL</c> link file.</summary>
    public static List<(uint Type, uint Id)> References(byte[]? file, long? offset)
    {
        var refs = new List<(uint, uint)>();
        if (file is null || offset is not { } at || at <= 0 || at + BlockSize > file.Length) return refs;
        for (var p = (int)at + 16; p + 8 <= at + BlockSize; p += 4)
        {
            var type = BitConverter.ToUInt32(file, p);
            if ((type & 0xFF000000) != 0 || (type & 0x00FF0000) == 0) continue;  // not an object type
            refs.Add((type, BitConverter.ToUInt32(file, p + 4)));
        }
        return refs;
    }

    private static List<int> NodesOf(byte[]? links, long? offset) =>
        References(links, offset).Where(r => r.Type == NodeType).Select(r => (int)r.Id).Distinct().ToList();

    private static Owner? OwnerOf(
        byte[]? listLinks, long? offset, Dictionary<(long Type, long Id), Dictionary<string, string>> objects)
    {
        foreach (var (type, id) in References(listLinks, offset))
        {
            if (!objects.TryGetValue((type, id), out var row)) continue;
            if (!(Num(row, "MODULN") > 0) || (Num(row, "SUBMODN") ?? 0) > 0) continue;  // not a module
            int? rack = null;
            string? station = null;
            var seen = new HashSet<(long, long)> { (type, id) };
            var current = row;
            var first = true;
            while (Num(current, "UNITTYP") is { } pt && Num(current, "UNITID") is { } pid && pid > 0
                   && seen.Add((pt, pid)) && objects.TryGetValue((pt, pid), out var parent))
            {
                if (first && Num(parent, "MODULN") is { } r && r >= 0) rack = (int)r;
                first = false;
                station = Text(parent, "NAME");
                current = parent;
            }
            return new Owner(station, rack ?? 0, (int?)Num(row, "MODULN"), Text(row, "NAME"));
        }
        return null;
    }

    private static bool IsOwners(int node, Owner? owner, IReadOnlyList<EthernetReader.Interface> ethernet) =>
        owner is not null && ethernet.Any(e => e.Node == node && e.Device is null
            && e.Station == owner.Station && e.Slot == owner.Slot && e.Module == owner.Module);

    private static Dictionary<(long Type, long Id), Dictionary<string, string>> HardwareObjects(
        string projectDir, Action<string, string> error)
    {
        var objects = new Dictionary<(long, long), Dictionary<string, string>>();
        var hw = FindDir(projectDir, "hOmSave7");
        foreach (var dir in hw is null ? [] : Directory.EnumerateDirectories(hw))
        {
            try
            {
                if (FindFile(dir, "HOBJECT1.DBF") is not { } file) continue;
                foreach (var row in Dbf.Read(file))
                {
                    if (Num(row, "OBJTYP") is { } t && Num(row, "ID") is { } id) objects[(t, id)] = row;
                }
            }
            catch (Exception e)
            {
                error($"hOmSave7/{Path.GetFileName(dir)}", $"{e.GetType().Name}: {e.Message}");
            }
        }
        return objects;
    }

    private static List<Compiled> CompiledRecords(string projectDir, Action<string, string> error)
    {
        var records = new List<Compiled>();
        var sdb = FindDir(projectDir, "sdb");
        foreach (var dir in sdb is null ? Enumerable.Empty<string>() : Directory.EnumerateDirectories(sdb).Order(StringComparer.Ordinal))
        {
            foreach (var file in Directory.EnumerateFiles(dir).Order(StringComparer.Ordinal))
            {
                if (!file.EndsWith(".PG", StringComparison.OrdinalIgnoreCase)) continue;
                var name = $"sdb/{Path.GetFileName(dir)}/{Path.GetFileName(file)}";
                try
                {
                    if (ParseCompiledTail(File.ReadAllBytes(file), name) is { } record) records.Add(record);
                }
                catch (Exception e)
                {
                    error(name, $"{e.GetType().Name}: {e.Message}");
                }
            }
        }
        return records;
    }

    private static byte[]? ReadBytes(string? path, string where, Action<string, string> error)
    {
        if (path is null) return null;
        try
        {
            return File.ReadAllBytes(path);
        }
        catch (Exception e)
        {
            error(where, $"{e.GetType().Name}: {e.Message}");
            return null;
        }
    }

    /// <summary>Dotted address from the 8 hex digits the tables store (<c>0A660A14</c>).</summary>
    public static string? Ip(string? hex)
    {
        if (hex is null || hex.Length != 8 || !uint.TryParse(hex, NumberStyles.HexNumber, CultureInfo.InvariantCulture, out var v))
        {
            return null;
        }
        return string.Join('.', v >> 24, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF);
    }

    private static bool? Flag(Dictionary<string, string> row, string field) =>
        Num(row, field) is { } n ? n != 0 : null;

    private static string? FindDir(string parent, string name) =>
        Directory.Exists(parent)
            ? Directory.EnumerateDirectories(parent).FirstOrDefault(d => Path.GetFileName(d).Equals(name, StringComparison.OrdinalIgnoreCase))
            : null;

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
