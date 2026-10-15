using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization.Metadata;
using System.Text.RegularExpressions;
using DotNetSiemensPLCToolBoxLibrary.DataTypes;
using DotNetSiemensPLCToolBoxLibrary.DataTypes.AWL.Step7V5;
using DotNetSiemensPLCToolBoxLibrary.DataTypes.Blocks;
using DotNetSiemensPLCToolBoxLibrary.DataTypes.Blocks.Step7V5;
using DotNetSiemensPLCToolBoxLibrary.DataTypes.Network;
using DotNetSiemensPLCToolBoxLibrary.DataTypes.Projectfolders;
using DotNetSiemensPLCToolBoxLibrary.DataTypes.Projectfolders.Step7V5;
using DotNetSiemensPLCToolBoxLibrary.Projectfiles;

namespace S7Dump;

/// <summary>Builds the s7dump JSON document (docs/s7dump-json.md) from a STEP 7 V5.x project.</summary>
public sealed class Dumper : IDisposable
{
    private static readonly string[] BlockTypes = ["OB", "FB", "FC", "SFB", "SFC", "DB", "UDT", "VAT"];
    private static readonly Regex SourceDefines = new(
        // "FB_X" | FB 10 | bare name (OSCAT: FUNCTION_BLOCK ARRAY_MIN)
        @"^\s*(ORGANIZATION_BLOCK|FUNCTION_BLOCK|FUNCTION|DATA_BLOCK|TYPE)\s+(""[^""]+""|[A-Za-z]+\s*\d+(?!\w)|[A-Za-z_]\w*)",
        RegexOptions.Multiline | RegexOptions.IgnoreCase);

    private readonly Step7ProjectV5 _project;
    private readonly string _projectFile;
    private readonly bool _english;
    private readonly bool _sources;
    private readonly JsonArray _errors = new();

    public Dumper(string projectFile, bool english, bool sources, Encoding? encoding = null)
    {
        _projectFile = projectFile;
        _english = english;
        _sources = sources;
        _project = encoding is null
            ? new Step7ProjectV5(projectFile, false)
            : new Step7ProjectV5(projectFile, false, encoding);
    }

    public void Dispose() => _project.Dispose();

    /// <summary>S7DUMP_TRACE=1: the full exception on stderr, for finding where the library fails.</summary>
    private static void Trace(string where, Exception e)
    {
        if (Environment.GetEnvironmentVariable("S7DUMP_TRACE") == "1") Console.Error.WriteLine($"{where}: {e}");
    }

    private void Error(string where, Exception e)
    {
        Trace(where, e);
        _errors.Add(new JsonObject { ["where"] = where, ["message"] = $"{e.GetType().Name}: {e.Message}" });
    }

    private void Error(string where, string message) =>
        _errors.Add(new JsonObject { ["where"] = where, ["message"] = message });

    public string Dump()
    {
        var encoding = _project.ProjectEncoding ?? Encoding.Latin1;
        var doc = new JsonObject
        {
            ["dump_version"] = 1,
            ["tool"] = new JsonObject
            {
                ["name"] = "s7dump",
                ["version"] = typeof(Dumper).Assembly.GetName().Version?.ToString(3) ?? "1.0.0",
                ["library_version"] = typeof(Step7ProjectV5).Assembly.GetName().Version?.ToString() ?? "",
            },
            ["project"] = new JsonObject
            {
                ["name"] = _project.ProjectName,
                ["description"] = _project.ProjectDescription,
                ["kind"] = _projectFile.EndsWith(".s7l", StringComparison.OrdinalIgnoreCase) ? "library" : "project",
                ["step7_version"] = null,
                ["encoding"] = encoding.WebName,
                ["languages"] = new JsonObject { ["stored"] = "und", ["maintained"] = new JsonArray() },
                ["mnemonic"] = new JsonObject
                {
                    ["exported"] = _english ? "en" : "de",
                    ["project"] = _project.ProjectLanguage == MnemonicLanguage.English ? "en" : "de",
                },
                ["pcs7"] = false,
            },
        };
        DumpHardware(doc);
        doc["programs"] = DumpPrograms(encoding);
        doc["pcs7_charts"] = new JsonArray();
        doc["errors"] = _errors;
        var options = new JsonSerializerOptions
        {
            WriteIndented = true,
            Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
            TypeInfoResolver = new DefaultJsonTypeInfoResolver(),
        };
        return doc.ToJsonString(options) + "\n";
    }

    // ------------------------------------------------------------------ hardware (partial, R1)
    private void DumpHardware(JsonObject doc)
    {
        var stations = new SortedDictionary<string, string?>(StringComparer.Ordinal);
        var cpus = new JsonArray();
        var cps = new JsonArray();
        var networks = new List<JsonObject>();
        try
        {
            foreach (var cpu in _project.CPUFolders.OrderBy(c => c.Name, StringComparer.Ordinal))
            {
                var station = StationOf(cpu, stations);
                var program = _project.S7ProgrammFolders.FirstOrDefault(p => ReferenceEquals(p.Parent, cpu));
                cpus.Add(new JsonObject
                {
                    ["name"] = cpu.Name, ["station"] = station, ["rack"] = cpu.Rack, ["slot"] = cpu.Slot,
                    ["order_no"] = cpu.MLFB_OrderNumber, ["type"] = cpu.CpuType.ToString(),
                    ["program"] = program?.Name,
                });
                networks.AddRange(Interfaces(cpu.Name, station, cpu.NetworkInterfaces));
            }
            foreach (var cp in _project.CPFolders.OrderBy(c => c.Name, StringComparer.Ordinal))
            {
                var station = StationOf(cp, stations);
                cps.Add(new JsonObject
                {
                    ["name"] = cp.Name, ["station"] = station, ["rack"] = cp.Rack, ["slot"] = cp.Slot,
                    ["order_no"] = null,
                });
                networks.AddRange(Interfaces(cp.Name, station, cp.NetworkInterfaces));
            }
        }
        catch (Exception e)
        {
            Error("hardware", e);
        }
        // Ethernet settings of every CPU and CP, also of types the library does not know; they
        // replace the library's Ethernet entries (address as CIDR when the mask is known)
        var ethernet = EthernetReader.Read(
            Path.GetDirectoryName(Path.GetFullPath(_projectFile))!, (where, message) => Error(where, message));
        doc["ethernet"] = new JsonArray(ethernet.Select(i => (JsonNode)i.ToJson()).ToArray());
        doc["modules"] = HardwareReader.Read(
            Path.GetDirectoryName(Path.GetFullPath(_projectFile))!, (where, message) => Error(where, message), ethernet);
        EthernetReader.ReplaceIn(networks, ethernet);
        // configured connections (NetPro) with their TSAPs; addresses are data, nothing is contacted
        doc["connections"] = new JsonArray(ConnectionReader
            .Read(Path.GetDirectoryName(Path.GetFullPath(_projectFile))!, ethernet, (where, message) => Error(where, message))
            .Select(c => (JsonNode)c.ToJson()).ToArray());
        doc["stations"] = new JsonArray(stations
            .Select(kv => (JsonNode)new JsonObject { ["name"] = kv.Key, ["type"] = kv.Value }).ToArray());
        doc["cpus"] = cpus;
        doc["cps"] = cps;
        doc["networks"] = new JsonArray(networks
            .OrderBy(n => (string?)n["station"], StringComparer.Ordinal)
            .ThenBy(n => (string?)n["node"], StringComparer.Ordinal)
            .ThenBy(n => (int?)n["device"] ?? 0)
            .ThenBy(n => (string?)n["kind"], StringComparer.Ordinal)
            .Select(n => (JsonNode)n).ToArray());
    }

    private static string? StationOf(ProjectFolder folder, SortedDictionary<string, string?> stations)
    {
        for (var p = folder.Parent; p is not null; p = p.Parent)
        {
            if (p is StationConfigurationFolder s)
            {
                stations[s.Name] = s.StationType.ToString();
                return s.Name;
            }
        }
        return null;
    }

    private static IEnumerable<JsonObject> Interfaces(
        string node, string? station, IEnumerable<NetworkInterface>? interfaces)
    {
        foreach (var ni in interfaces ?? [])
        {
            var obj = new JsonObject
            {
                ["kind"] = ni.NetworkInterfaceType switch
                {
                    NetworkType.Ethernet => "ethernet",
                    NetworkType.Profibus => "profibus",
                    NetworkType.Mpi => "mpi",
                    _ => ni.NetworkInterfaceType.ToString().ToLowerInvariant(),
                },
                ["subnet"] = null,
                ["node"] = node,
                ["station"] = station,
                ["device"] = null,
                ["address"] = ni switch
                {
                    EthernetNetworkInterface e => e.UseIp ? e.IpAddress?.ToString() : e.Mac?.ToString(),
                    MpiProfiBusNetworkInterface m => m.Address.ToString(),
                    _ => null,
                },
                ["device_name"] = null,
            };
            yield return obj;
        }
    }

    // ------------------------------------------------------------------ programs
    private JsonArray DumpPrograms(Encoding encoding)
    {
        var programs = new JsonArray();
        foreach (var prog in _project.S7ProgrammFolders.OrderBy(p => p.Name, StringComparer.Ordinal))
        {
            var blocks = new JsonArray();
            var catalogBlocks = 0;
            if (prog.BlocksOfflineFolder is { } folder)
            {
                var infos = folder.BlockInfos
                    .Where(i => BlockTypes.Contains(i.BlockType.ToString()))
                    .OrderBy(i => Array.IndexOf(BlockTypes, i.BlockType.ToString()))
                    .ThenBy(i => Number(InfoName(i)))
                    .ThenBy(i => InfoName(i), StringComparer.Ordinal)
                    .ToList();
                catalogBlocks = infos.Count;
                var attributes = SubBlockAttributes(prog.Name, folder);
                FindCommCallees(prog, folder);
                foreach (var info in infos) blocks.Add(DumpBlock(prog.Name, folder, info, attributes));
            }
            var symbols = DumpSymbols(prog);
            var sources = _sources ? DumpSources(prog, encoding) : new JsonArray();
            programs.Add(new JsonObject
            {
                ["name"] = prog.Name,
                ["cpu"] = (prog.Parent as CPUFolder)?.Name,
                // program names repeat across stations ("S7-Programm(1)" in every station)
                ["station"] = prog.Parent is ProjectFolder parent
                    ? StationOf(parent, new SortedDictionary<string, string?>(StringComparer.Ordinal))
                    : null,
                ["catalog"] = new JsonObject
                {
                    ["blocks"] = catalogBlocks,
                    ["sources"] = prog.SourceFolder?.BlockInfos.Count ?? 0,
                    ["symbols"] = symbols.Count,
                },
                ["blocks"] = blocks,
                ["sources"] = sources,
                ["symbols"] = symbols,
            });
        }
        return programs;
    }

    /// <summary>"FB10"-style name of a block entry; the library leaves Name empty for some.</summary>
    private static string InfoName(ProjectBlockInfo info) =>
        !string.IsNullOrEmpty(info.Name) ? info.Name : info.ToString() ?? "";

    /// <summary>Bit 6 of the block header attribute byte: <c>S7BlockAtributes.FBlock</c>, "an Safety
    /// Block in an Safety PLC" in the library source.</summary>
    private const int FBlockBit = 0x40;

    /// <summary>SUBBLKTYP codes of the block header records in SUBBLK.DBF.</summary>
    private static readonly Dictionary<string, int> SubBlockTypes = new()
    {
        ["OB"] = 8, ["DB"] = 10, ["FC"] = 12, ["SFC"] = 13, ["FB"] = 14, ["SFB"] = 15,
    };

    private static int? FindAttribute(
        IReadOnlyDictionary<(int Type, int Number), int>? attributes, string type, int number) =>
        attributes is not null && SubBlockTypes.TryGetValue(type, out var code)
            && attributes.TryGetValue((code, number), out var value)
            ? value
            : null;

    /// <summary>The directory as it is spelled on disk, or null. The library builds folder names
    /// from numbers in the project tables (<c>0000000A</c>) while the folder may be
    /// <c>0000000a</c>; that only matters on a case-sensitive file system (the Linux exporter).</summary>
    public static string? ExistingDirectory(string? dir)
    {
        if (string.IsNullOrEmpty(dir)) return null;
        dir = dir.Replace('\\', Path.DirectorySeparatorChar).TrimEnd(Path.DirectorySeparatorChar);
        if (Directory.Exists(dir)) return dir;
        var parent = ExistingDirectory(Path.GetDirectoryName(dir));
        return parent is null ? null : Directory.EnumerateDirectories(parent).FirstOrDefault(d =>
            Path.GetFileName(d).Equals(Path.GetFileName(dir), StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>The file as it is spelled on disk, or null (see <see cref="ExistingDirectory"/>).</summary>
    public static string? ExistingFile(string? file)
    {
        if (string.IsNullOrEmpty(file)) return null;
        file = file.Replace('\\', Path.DirectorySeparatorChar);
        if (File.Exists(file)) return file;
        var dir = ExistingDirectory(Path.GetDirectoryName(file));
        return dir is null ? null : Directory.EnumerateFiles(dir).FirstOrDefault(f =>
            Path.GetFileName(f).Equals(Path.GetFileName(file), StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>ATTRIBUTE per (SUBBLKTYP, BLKNUMBER) from the program's SUBBLK.DBF, read-only. The
    /// file is dBase III: a 32-byte header, 32-byte field descriptors up to 0x0D, fixed-length
    /// records whose first byte is '*' when deleted. Null when the table cannot be read.</summary>
    private Dictionary<(int Type, int Number), int>? SubBlockAttributes(
        string program, BlocksOfflineFolder folder)
    {
        try
        {
            var dir = ExistingDirectory(folder.Folder);
            var path = dir is null ? null : Directory
                .EnumerateFiles(dir)
                .FirstOrDefault(f => Path.GetFileName(f).Equals("SUBBLK.DBF", StringComparison.OrdinalIgnoreCase));
            if (path is null)
            {
                Error($"{program}/SUBBLK.DBF", "block table not found: F-block flags unknown");
                return null;
            }
            var raw = File.ReadAllBytes(path);
            var count = BitConverter.ToInt32(raw, 4);
            int headerLength = BitConverter.ToUInt16(raw, 8), recordLength = BitConverter.ToUInt16(raw, 10);
            var offsets = new Dictionary<string, (int Offset, int Length)>();
            int offset = 1, pos = 32;
            while (pos + 32 <= raw.Length && raw[pos] != 0x0D)
            {
                var name = Encoding.ASCII.GetString(raw, pos, 11).TrimEnd('\0', ' ');
                offsets[name] = (offset, raw[pos + 16]);
                offset += raw[pos + 16];
                pos += 32;
            }
            string Field(int start, string name) =>
                Encoding.ASCII.GetString(raw, start + offsets[name].Offset, offsets[name].Length).Trim();
            var result = new Dictionary<(int, int), int>();
            for (var i = 0; i < count; i++)
            {
                var start = headerLength + i * recordLength;
                if (start + recordLength > raw.Length) break;
                if (raw[start] == (byte)'*') continue;  // deleted record
                if (int.TryParse(Field(start, "SUBBLKTYP"), out var t)
                    && int.TryParse(Field(start, "BLKNUMBER"), out var n)
                    && int.TryParse(Field(start, "ATTRIBUTE"), out var a))
                {
                    result[(t, n)] = a;
                }
            }
            return result;
        }
        catch (Exception e)
        {
            Error($"{program}/SUBBLK.DBF", e);
            return null;
        }
    }

    private static readonly JsonSerializerOptions AttributeJson = new()
    {
        TypeInfoResolver = new DefaultJsonTypeInfoResolver(),
    };

    /// <summary>The block's attributes from the Attributes tab, with all their public properties
    /// as the library reads them (no interpretation).</summary>
    private static JsonArray BlockAttributes(S7Block s7)
    {
        var list = new JsonArray();
        foreach (var attribute in s7.Attributes ?? [])
        {
            if (attribute is null) continue;
            list.Add(JsonSerializer.SerializeToNode(attribute, attribute.GetType(), AttributeJson));
        }
        return list;
    }

    private static int Number(string? name)
    {
        if (string.IsNullOrEmpty(name)) return 0;
        var digits = new string(name.Where(char.IsDigit).ToArray());
        return int.TryParse(digits, out var n) ? n : 0;
    }

    private JsonObject DumpBlock(
        string program, BlocksOfflineFolder folder, ProjectBlockInfo info,
        IReadOnlyDictionary<(int Type, int Number), int>? attributes)
    {
        var type = info.BlockType.ToString();
        var where = $"{program}/{InfoName(info)}";
        var protectedBlock = info is S7ProjectBlockInfo s7info && s7info.KnowHowProtection;
        var obj = new JsonObject
        {
            ["type"] = type,
            ["number"] = Number(InfoName(info)),
            ["symbolic_name"] = null,
            ["family"] = (info as S7ProjectBlockInfo)?.Family,
            ["version"] = null,
            ["author"] = null,
            // filled from the decoded block below: ProjectBlockInfo.BlockLanguage decodes the
            // block itself, outside any error handling, and one block the library cannot
            // decode ended the whole run
            ["language"] = "unknown",
            ["know_how_protected"] = protectedBlock,
            ["title"] = null,
            ["description"] = null,
            ["mc7_size"] = 0,
            ["interface"] = new JsonArray(),
            ["networks"] = new JsonArray(),
            ["instance_of"] = null,
            // safety content as found. header_attribute is the block's ATTRIBUTE column
            // in the project's SUBBLK.DBF (the library does not read it); f_block is its bit 6
            // (S7BlockAtributes.FBlock), null when unknown. checksum is the MC7 code checksum, not an
            // F-signature
            ["f_block"] = null,
            ["header_attribute"] = null,
            ["checksum"] = null,
            ["attributes"] = new JsonArray(),
        };
        var errors = new JsonArray();
        obj["errors"] = errors;
        Block? block;
        try
        {
            var options = new S7ConvertingOptions(_english ? MnemonicLanguage.English : MnemonicLanguage.German)
            {
                UseComments = true,
                UseDBActualValues = type == "DB",  // actual values next to start values (F_PROG_SIG)
            };
            try
            {
                block = folder.GetBlock(info, options);
            }
            catch (Exception e) when (type == "DB" && e is IndexOutOfRangeException or ArgumentException)
            {
                // The stored actual values are shorter than the declaration asks for (seen on
                // instance DBs of library blocks): the library runs past their end. The
                // declaration and the start values are still readable.
                Trace(where, e);
                options.UseDBActualValues = false;
                block = folder.GetBlock(info, options);
                obj["actual_values_read"] = false;
            }
        }
        catch (Exception e)
        {
            errors.Add($"{e.GetType().Name}: {e.Message}");
            Error(where, e);
            return obj;
        }
        if (block is null)
        {
            errors.Add("block could not be read");
            Error(where, "block could not be read");
            return obj;
        }
        obj["language"] = block.BlockLanguage.ToString();
        obj["symbolic_name"] = block.SymbolTableEntry?.Symbol;
        if (block.BlockNumber > 0) obj["number"] = block.BlockNumber;
        if (block is S7Block s7)
        {
            obj["family"] = s7.Family ?? (string?)obj["family"];
            obj["version"] = s7.Version;
            obj["author"] = s7.Author;
            obj["title"] = s7.Title;
            obj["mc7_size"] = s7.CodeSize;
            obj["know_how_protected"] = protectedBlock || s7.KnowHowProtection;
            // the library leaves BlockAttribute at 0 for offline blocks; the block table has it
            var header = FindAttribute(attributes, type, (int)obj["number"]!)
                ?? (Convert.ToInt32(s7.BlockAttribute) is var a and > 0 ? a : (int?)null);
            obj["header_attribute"] = header;
            obj["f_block"] = header is { } h ? (h & FBlockBit) != 0 : null;
            obj["checksum"] = s7.CheckSum;
            obj["attributes"] = BlockAttributes(s7);
        }
        try
        {
            switch (block)
            {
                case S7FunctionBlock fb:
                    obj["description"] = fb.Description;
                    obj["interface"] = Interface(fb.Parameter, sections: true);
                    if (!(bool)obj["know_how_protected"]!)
                    {
                        obj["networks"] = Networks(fb);
                        AttachRawStatements(folder, info, (JsonArray)obj["networks"]!, errors);
                    }
                    break;
                case S7DataBlock db:
                    obj["interface"] = Interface(db.Structure, sections: db.IsInstanceDB);
                    if (db.IsInstanceDB) obj["instance_of"] = $"FB{db.FBNumber}";
                    break;
            }
        }
        catch (Exception e)
        {
            errors.Add($"{e.GetType().Name}: {e.Message}");
            Error(where, e);
        }
        return obj;
    }

    private static readonly Dictionary<string, string> Sections = new(StringComparer.OrdinalIgnoreCase)
    {
        ["IN"] = "IN", ["OUT"] = "OUT", ["IN_OUT"] = "IN_OUT", ["STAT"] = "STAT", ["STATIC"] = "STAT",
        ["TEMP"] = "TEMP", ["RET_VAL"] = "RETURN", ["RETURN"] = "RETURN",
    };

    private static JsonArray Interface(IDataRow? root, bool sections)
    {
        var rows = new JsonArray();
        if (root?.Children is null) return rows;
        foreach (var child in root.Children)
        {
            if (sections && Sections.TryGetValue(child.Name ?? "", out var section))
            {
                if (section == "RETURN" && (child.Children is null || child.Children.Count == 0))
                {
                    rows.Add(Member(child, section));
                    continue;
                }
                foreach (var m in child.Children ?? []) rows.Add(Member(m, section));
            }
            else
            {
                rows.Add(Member(child, null));
            }
        }
        return rows;
    }

    private static JsonObject Member(IDataRow row, string? section)
    {
        string? type = row is DataBlockRow dbr ? dbr.DataTypeAsString : row.DataType.ToString();
        string? start = null;
        string? actual = null;
        string? offset = null;
        int? length = null;
        if (row is S7DataRow s7row)
        {
            try { start = s7row.StartValueAsString; } catch { start = null; }
            try { actual = s7row.ValueAsString; } catch { actual = null; }
            try
            {
                // byte.bit offset in the block, as the library lays the block out
                var address = s7row.BlockAddress;
                var bytes = s7row.ByteLength;
                offset = $"{address.ByteAddress}.{address.BitAddress}";
                length = bytes;
            }
            catch { offset = null; length = null; }
        }
        var members = new JsonArray();
        var isStruct = row.DataType == S7DataRowType.STRUCT || row.DataType == S7DataRowType.UDT;
        if (isStruct)
        {
            foreach (var c in row.Children ?? []) members.Add(Member(c, null));
        }
        return new JsonObject
        {
            ["name"] = row.Name,
            ["section"] = section,
            ["type"] = type,
            ["start"] = string.IsNullOrEmpty(start) ? null : start,
            ["offset"] = offset,
            ["length"] = length,
            // actual value of a DB member, only where it differs from the start value
            ["actual"] = string.IsNullOrEmpty(actual) || actual == start ? null : actual,
            ["comment"] = string.IsNullOrEmpty(row.Comment) ? null : row.Comment,
            ["members"] = members,
        };
    }

    // SFB/FB numbers of the communication blocks for S7 connections (USEND, URCV, BSEND, BRCV,
    // GET, PUT); the standard library's loadable FBs for S7-300 use the same numbers
    private static readonly HashSet<int> CommBlockNumbers = [8, 9, 12, 13, 14, 15];
    private static readonly System.Text.RegularExpressions.Regex RawCall = new(
        @"^\s*(UC|CC|CALL)\s+(.+?)\s*$", System.Text.RegularExpressions.RegexOptions.Compiled);

    // per block folder: how a call of one of its communication blocks is written (FB12, "BSEND")
    private readonly Dictionary<BlocksOfflineFolder, HashSet<string>> _commCallees = [];

    private void FindCommCallees(S7ProgrammFolder prog, BlocksOfflineFolder folder)
    {
        // absolute forms of every communication block; a block listed under its symbol name has
        // no number in its info, so the symbol table says which symbols stand for one of them
        var absolute = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var n in CommBlockNumbers)
        {
            absolute.Add("FB" + n.ToString(System.Globalization.CultureInfo.InvariantCulture));
            absolute.Add("SFB" + n.ToString(System.Globalization.CultureInfo.InvariantCulture));
        }
        var callees = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        try
        {
            foreach (var e in prog.SymbolTable?.SymbolTableEntrys ?? [])
            {
                string?[] operands = [e.Operand, e.OperandIEC];
                if (operands.Any(o => o is not null && absolute.Contains(o.Replace(" ", ""))))
                {
                    callees.Add("\"" + e.Symbol + "\"");
                }
            }
        }
        catch (Exception e)
        {
            Error($"{prog.Name}/symbols", e);
        }
        var present = callees.Count > 0 || folder.BlockInfos.Any(i => absolute.Contains(InfoName(i).Replace(" ", "")));
        if (present) callees.UnionWith(absolute);  // programs without such a block are not converted twice
        _commCallees[folder] = callees;
    }

    /// <summary>The library rebuilds CALL statements and loses the ANY pointers of FB and SFB calls.
    /// For every network that calls a communication block, the statements are
    /// emitted a second time without call reconstruction (<c>raw_stl</c>): the parameter
    /// assignments are plain L/T statements there. Blocks of programs without a communication block
    /// are not converted twice.</summary>
    private void AttachRawStatements(
        BlocksOfflineFolder folder, ProjectBlockInfo info, JsonArray networks, JsonArray errors)
    {
        if (!_commCallees.TryGetValue(folder, out var callees) || callees.Count == 0) return;
        try
        {
            var options = new S7ConvertingOptions(_english ? MnemonicLanguage.English : MnemonicLanguage.German)
            {
                UseComments = false,
                GenerateCallsfromUCs = false,
            };
            if (folder.GetBlock(info, options) is not S7FunctionBlock raw) return;
            var rawNetworks = Networks(raw);
            for (var i = 0; i < networks.Count && i < rawNetworks.Count; i++)
            {
                var lines = (JsonArray)rawNetworks[i]!["stl"]!;
                if (lines.Any(l => IsCommCall((string?)l, callees))) networks[i]!["raw_stl"] = lines.DeepClone();
            }
        }
        catch (Exception e)
        {
            errors.Add($"raw statements: {e.GetType().Name}: {e.Message}");
        }
    }

    /// <summary>True for a block call (<c>UC</c>, <c>CC</c>, <c>CALL</c>) of one of the given callees,
    /// written absolute (<c>UC FB 12</c>) or symbolic (<c>UC "BSEND"</c>).</summary>
    public static bool IsCommCall(string? line, IReadOnlySet<string> callees)
    {
        if (line is null || RawCall.Match(line) is not { Success: true } m) return false;
        var callee = m.Groups[2].Value;
        return callees.Contains(callee.StartsWith('"') ? callee : callee.Replace(" ", ""));
    }

    private static JsonArray Networks(S7FunctionBlock fb)
    {
        var networks = new JsonArray();
        var no = 0;
        foreach (var nw in fb.Networks ?? [])
        {
            no++;
            var lines = new JsonArray();
            foreach (var row in nw.AWLCode ?? [])
            {
                var text = row.ToString() ?? "";
                foreach (var line in text.Replace("\r\n", "\n").Split('\n'))
                {
                    if (line.Length > 0) lines.Add(line.TrimEnd());
                }
            }
            networks.Add(new JsonObject
            {
                ["no"] = no,
                ["title"] = string.IsNullOrEmpty(nw.Name) ? null : nw.Name,
                ["comment"] = string.IsNullOrEmpty(nw.Comment) ? null : nw.Comment,
                ["stl"] = lines,
            });
        }
        return networks;
    }

    private JsonArray DumpSymbols(S7ProgrammFolder prog)
    {
        var symbols = new JsonArray();
        try
        {
            var entries = prog.SymbolTable?.SymbolTableEntrys ?? [];
            foreach (var e in entries.OrderBy(e => e.Symbol, StringComparer.Ordinal))
            {
                var operand = _english && !string.IsNullOrEmpty(e.OperandIEC) ? e.OperandIEC : e.Operand;
                symbols.Add(new JsonObject
                {
                    ["symbol"] = e.Symbol,
                    ["address"] = operand,
                    ["type"] = e.DataType,
                    ["comment"] = string.IsNullOrEmpty(e.Comment) ? null : e.Comment,
                });
            }
        }
        catch (Exception e)
        {
            Error($"{prog.Name}/symbols", e);
        }
        return symbols;
    }

    private JsonArray DumpSources(S7ProgrammFolder prog, Encoding encoding)
    {
        var sources = new JsonArray();
        if (prog.SourceFolder is not { } folder) return sources;
        foreach (var info in folder.BlockInfos.OfType<S7ProjectSourceInfo>()
                     .OrderBy(i => i.Name, StringComparer.Ordinal))
        {
            var errors = new JsonArray();
            string? text = null;
            try
            {
                if (ExistingFile(info.Filename) is { } f)
                {
                    var decoder = (Encoding)encoding.Clone();
                    text = decoder.GetString(File.ReadAllBytes(f));
                }
                else
                {
                    // The library's own reader decodes the bytes in a way that drops '+'
                    // characters (seen on a case-sensitive file system, where the file was
                    // not found under the name from the project table). Its text is kept,
                    // but never as reliable content.
                    text = folder.GetSource(info);
                    errors.Add("source file not found on disk; text read by the library may be altered");
                }
                if (text is not null && text.Contains('�'))
                    errors.Add("undecodable characters replaced by U+FFFD");
            }
            catch (Exception e)
            {
                errors.Add($"{e.GetType().Name}: {e.Message}");
                Error($"{prog.Name}/source {info.Name}", e);
            }
            var ext = Path.GetExtension(info.Filename ?? info.Name ?? "").ToLowerInvariant();
            var defines = new JsonArray();
            if (text is not null)
            {
                foreach (Match m in SourceDefines.Matches(text))
                {
                    var target = Regex.Replace(m.Groups[2].Value.Trim(), @"\s+", " ");
                    if (!defines.Any(d => (string?)d == target)) defines.Add(target);
                }
            }
            sources.Add(new JsonObject
            {
                ["name"] = info.Name,
                ["kind"] = ext == ".scl" ? "scl" : "stl",
                ["text"] = text?.Replace("\r\n", "\n"),
                ["defines"] = defines,
                ["errors"] = errors,
            });
        }
        return sources;
    }
}
