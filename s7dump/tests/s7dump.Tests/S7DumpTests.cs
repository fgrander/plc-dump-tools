using System.IO.Compression;
using System.Text.Json;
using S7Dump;
using Xunit;

namespace S7Dump.Tests;

public class ProjectLocatorTests
{
    [Fact]
    public void FindsTheProjectFileInAFolder()
    {
        var dir = Directory.CreateTempSubdirectory("s7dump-test").FullName;
        File.WriteAllText(Path.Combine(dir, "B.s7p"), "x");
        File.WriteAllText(Path.Combine(dir, "A.s7p"), "x");
        Assert.Equal(Path.Combine(dir, "A.s7p"), ProjectLocator.Find(dir));
    }

    [Fact]
    public void FindsAFolderWhateverTheCaseOfItsName()
    {
        // STEP 7 names block folders 0000000a; the library asks for 0000000A (Linux exporter)
        var dir = Directory.CreateTempSubdirectory("s7dump-test").FullName;
        var real = Directory.CreateDirectory(Path.Combine(dir, "ombstx", "offline", "0000000a")).FullName;
        var asked = Path.Combine(dir, "OMBSTX", "offline", "0000000A");
        Assert.Equal(real, Dumper.ExistingDirectory(asked), ignoreCase: OperatingSystem.IsWindows());
        Assert.Equal(real, Dumper.ExistingDirectory(real + Path.DirectorySeparatorChar));
        Assert.Null(Dumper.ExistingDirectory(Path.Combine(dir, "ombstx", "offline", "0000000b")));
        Assert.Null(Dumper.ExistingDirectory(null));

        // the same for a source file: S7ASRCOM/00000001/00000003.SCL in the table, lower case on disk
        var file = Path.Combine(real, "00000003.scl");
        File.WriteAllText(file, "x := a + b;");
        var found = Dumper.ExistingFile(Path.Combine(dir, "OMBSTX", "offline", "0000000A", "00000003.SCL"));
        Assert.Equal(file, found, ignoreCase: OperatingSystem.IsWindows());
        Assert.Null(Dumper.ExistingFile(Path.Combine(real, "missing.scl")));
        Assert.Null(Dumper.ExistingFile(null));
    }

    [Fact]
    public void AcceptsLibrariesAndRejectsOtherFiles()
    {
        var dir = Directory.CreateTempSubdirectory("s7dump-test").FullName;
        var lib = Path.Combine(dir, "Lib.s7l");
        File.WriteAllText(lib, "x");
        Assert.Equal(lib, ProjectLocator.Find(lib));
        var other = Path.Combine(dir, "Project.ap10");
        File.WriteAllText(other, "x");
        Assert.Throws<InvalidOperationException>(() => ProjectLocator.Find(other));
    }

    [Fact]
    public void FolderWithoutProjectIsRejected()
    {
        var dir = Directory.CreateTempSubdirectory("s7dump-test").FullName;
        Assert.Throws<InvalidOperationException>(() => ProjectLocator.Find(dir));
    }
}

/// <summary>Real STEP 7 V5.x projects from samples/s7classic (zips with a .s7p/.s7l entry).</summary>
public class SampleProjectTests
{
    private static string? SamplesDir()
    {
        var env = Environment.GetEnvironmentVariable("S7DUMP_SAMPLES_DIR");
        if (!string.IsNullOrEmpty(env)) return env;
        for (var d = new DirectoryInfo(AppContext.BaseDirectory); d is not null; d = d.Parent)
        {
            var candidate = Path.Combine(d.FullName, "samples", "s7classic");
            if (Directory.Exists(candidate)) return candidate;
        }
        return null;
    }

    public static IEnumerable<object[]> Projects()
    {
        var found = new List<object[]>();
        var dir = SamplesDir();
        if (dir is not null)
        {
            foreach (var zip in Directory.EnumerateFiles(dir, "*.zip", SearchOption.AllDirectories).Order())
            {
                using var archive = ZipFile.OpenRead(zip);
                if (archive.Entries.Any(e => e.FullName.EndsWith(".s7p", StringComparison.OrdinalIgnoreCase)
                                          || e.FullName.EndsWith(".s7l", StringComparison.OrdinalIgnoreCase)))
                    found.Add([zip]);
            }
        }
        // xUnit fails a theory without data: one empty case stands for "no STEP 7 samples"
        return found.Count > 0 ? found : [[""]];
    }

    [Fact]
    public void SamplesFolderIsOptional()
    {
        // Documents the gate: with no STEP 7 samples, DumpsEverySample has no cases.
        Assert.True(SamplesDir() is null || Directory.Exists(SamplesDir()));
    }

    [Theory]
    [MemberData(nameof(Projects))]
    public void DumpsEverySample(string zip)
    {
        if (zip.Length == 0) return; // no STEP 7 V5.x samples in samples/s7classic
        var hashBefore = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(zip)));
        var work = Directory.CreateTempSubdirectory("s7dump-sample").FullName;
        ZipFile.ExtractToDirectory(zip, work);
        var projectFile = Directory.EnumerateFiles(work, "*.*", SearchOption.AllDirectories)
            .First(f => f.EndsWith(".s7p", StringComparison.OrdinalIgnoreCase)
                     || f.EndsWith(".s7l", StringComparison.OrdinalIgnoreCase));
        using var dumper = new Dumper(projectFile, english: true, sources: true);
        using var doc = JsonDocument.Parse(dumper.Dump());
        Assert.Equal(1, doc.RootElement.GetProperty("dump_version").GetInt32());
        Assert.True(doc.RootElement.GetProperty("programs").GetArrayLength() >= 0);
        var hashAfter = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(zip)));
        Assert.Equal(hashBefore, hashAfter);
    }
}

/// <summary>Ethernet nodes of the network table, also those no hardware object owns.</summary>
public class EthernetNodeTests
{
    // a field: its ID twice, a length-prefixed label, 10 bytes, the length-prefixed value
    private static byte[] Field(ushort id, string label, string value)
    {
        byte[] head = [(byte)(id & 0xFF), (byte)(id >> 8), 0, 0, (byte)(id & 0xFF), (byte)(id >> 8), 0, 0];
        return [.. head, (byte)label.Length, .. System.Text.Encoding.Latin1.GetBytes(label),
            0, 1, 0, 1, 0, 1, 0, 0, 0, 0, (byte)value.Length, .. System.Text.Encoding.Latin1.GetBytes(value)];
    }

    private static byte[] Node(int number, string ip, string name) =>
        [0x03, 0x52, 0x14, 0x00, .. BitConverter.GetBytes(number), .. new byte[40],
            .. Field(0x0FE0, "", ip), .. Field(0x1001, "Baugruppenname", name)];

    [Fact]
    public void ReadsAddressAndNameOfEveryNode()
    {
        var nodes = EthernetReader.ReadNodes(
            [.. Node(4, "AC1837B4", "CP 443-1 Advanced"), .. Node(7, "AC1837A3", "Ethernet Schnittstelle(1)")]);
        Assert.Equal(("172.24.55.180", "CP 443-1 Advanced"), (nodes[4]["ip"], nodes[4]["name"]));
        Assert.Equal(("172.24.55.163", "Ethernet Schnittstelle(1)"), (nodes[7]["ip"], nodes[7]["name"]));
    }

    private static System.Text.Json.Nodes.JsonObject LibraryEntry(string node, string? station, string address) => new()
    {
        ["kind"] = "ethernet", ["subnet"] = null, ["node"] = node, ["station"] = station,
        ["device"] = null, ["address"] = address, ["device_name"] = null,
    };

    private static EthernetReader.Interface Cp(string ip) => new(
        4, "SIMATIC 400(1)", 0, 3, "CP 443-1 Advanced", "CP 443-1 Advanced", ip, "255.255.255.192",
        null, null, null, null, null);

    [Fact]
    public void LibraryEntryWithoutStationIsReplacedByItsNode()
    {
        var networks = new List<System.Text.Json.Nodes.JsonObject>
        {
            LibraryEntry("CP 443-1 Advanced", null, "172.24.55.180"),
        };
        EthernetReader.ReplaceIn(networks, [Cp("172.24.55.180")]);
        var entry = Assert.Single(networks);
        Assert.Equal(("SIMATIC 400(1)", "172.24.55.180/26"), ((string?)entry["station"], (string?)entry["address"]));
    }

    [Fact]
    public void LibraryEntryWithoutStationAndAnotherAddressIsKept()
    {
        var networks = new List<System.Text.Json.Nodes.JsonObject>
        {
            LibraryEntry("CP 443-1 Advanced", null, "10.0.0.1"),
        };
        EthernetReader.ReplaceIn(networks, [Cp("172.24.55.180")]);
        Assert.Equal(["10.0.0.1", "172.24.55.180/26"], networks.Select(n => (string?)n["address"]).Order());
    }

    [Fact]
    public void NodeWithoutModuleIsListedUnderItsName()
    {
        var networks = new List<System.Text.Json.Nodes.JsonObject>();
        EthernetReader.ReplaceIn(networks, [new EthernetReader.Interface(
            7, null, null, null, null, "Ethernet Schnittstelle(1)", "172.24.55.163", "255.255.255.192",
            null, null, null, null, null)]);
        var entry = Assert.Single(networks);
        Assert.Equal(("Ethernet Schnittstelle(1)", null, "172.24.55.163/26"),
            ((string?)entry["node"], (string?)entry["station"], (string?)entry["address"]));
    }
}

/// <summary>Order numbers of DP slave and IO device modules from the station table file.</summary>
public class HardwareTableTests
{
    // a table file: runs of length-prefixed strings, one run per row, each table followed by its
    // header row (as seen in the Siemens, Pepperl+Fuchs and Mettler Toledo samples)
    private static byte[] TableFile(params string[][] rows)
    {
        var b = new List<byte>();
        foreach (var row in rows)
        {
            foreach (var cell in row)
            {
                var text = cell.Length == 0 ? " " : cell;  // empty cells are blanks in the file
                b.Add((byte)text.Length);
                b.AddRange(System.Text.Encoding.Latin1.GetBytes(text));
            }
            b.AddRange(new byte[] { 0, 0 });
        }
        return b.ToArray();
    }

    private static readonly List<HardwareReader.TableRow> Rows = HardwareReader.ReadTableRows(TableFile(
        ["1", "PS 307 5A", "1", "PS 307 5A", "6ES7 307-1EA00-0AA0", "", "", "", "", ""],
        ["Steckplatz", "Baugruppe", "Bestellnummer", "Firmware", "MPI-Adresse", "E-Adresse", "A-Adresse", "Kommentar"],
        ["1", "PM-E DC24V", "1", "PM-E DC24V", "6ES7 138-4CA01-0AA0", "", "", "2044*"],
        ["3", "PM-E DC24V", "3", "PM-E DC24V", "6ES7 138-4CB11-0AB0", "", "", "2043*"],
        ["4", "4/8 F-DI DC24V", "4", "4/8 F-DI DC24V", "6ES7 138-4FA03-0AB0", "1...6", "1...4", ""],
        ["Steckplatz", "Baugruppe", "Bestellnummer", "E-Adresse", "A-Adresse", "Diagnoseadresse", "Kommentar"],
        ["1", "16AO", "1", "16AO", "I/O 28 Wrd", "", "256...287", ""],
        ["Slot", "DP ID", "Order Number / Designation", "I Address", "Q Address", "Comment"],
        ["1", "identcontrol", "1", "172.24.55.165", "identcontrol", "#200877", "V3.1", "8186*", "aktiviert"],
        ["0", "identcontrol", "0", "identcontrol", "#200877", "", "", "8186*"],
        ["1", "In/Out 64 Bytes", "1", "In/Out 64 Bytes", "", "512...575", "512...575", ""],
        ["Steckplatz", "Baugruppe", "Bestellnummer", "E-Adresse", "A-Adresse", "Diagnoseadresse", "Kommentar"]));

    [Fact]
    public void ReadsEveryTableAndMarksDpIdDesignations()
    {
        Assert.Equal(7, Rows.Count);  // the device overview row is not a module row
        Assert.Equal(["16AO"], Rows.Where(r => r.Designation).Select(r => r.Name));
    }

    [Fact]
    public void ShortenedCatalogKeyConfirmsTheOrderNumber()
    {
        Assert.Equal("6ES7 138-4FA03-0AB0", HardwareReader.DeviceOrderNo("4/8 F-DI DC24V", "_S7H_6ES7_138_4FA03_0AB~", null, Rows));
        Assert.Equal("6ES7 138-4CB11-0AB0", HardwareReader.DeviceOrderNo("PM-E DC24V", "_S7H_HSP_6ES7_138_4CB11~", null, Rows));
        Assert.Null(HardwareReader.DeviceOrderNo("4/8 F-DI DC24V", "_S7H_6ES7_138_4FB02_0AB~", null, Rows));  // contradicts the key
    }

    [Fact]
    public void AmbiguousNamesAreNotGuessed() =>
        Assert.Null(HardwareReader.DeviceOrderNo("PM-E DC24V", null, null, Rows));

    [Fact]
    public void DpIdDesignationIsNoOrderNumber() =>
        Assert.Null(HardwareReader.DeviceOrderNo("16AO", "_S7H_DP_NOCHILD_CT", "I/O 28 Wrd", Rows));

    [Fact]
    public void DeviceHeadTakesTheAccessPointRow()
    {
        Assert.Equal("#200877", HardwareReader.DeviceOrderNo("IDENTControl", "_S7H_IO_NORM_ETER_CT", null, Rows));
        Assert.Null(HardwareReader.DeviceOrderNo("In/Out 64 Bytes", "_S7H_IO_NORM_MODULE_CT", null, Rows));
    }
}

/// <summary>Order number and firmware of PROFINET device heads from the IO system's device list.</summary>
public class DeviceListTests
{
    private static byte[] TableFile(params string[][] rows)
    {
        var b = new List<byte>();
        foreach (var row in rows)
        {
            foreach (var cell in row)
            {
                var text = cell.Length == 0 ? " " : cell;
                b.Add((byte)text.Length);
                b.AddRange(System.Text.Encoding.Latin1.GetBytes(text));
            }
            b.AddRange(new byte[] { 0, 0 });
        }
        return b.ToArray();
    }

    // device list rows as in the Pepperl+Fuchs (renamed device), Kollmorgen AKD (no IP) samples
    private static readonly List<HardwareReader.DeviceRow> Devices = HardwareReader.ReadDeviceRows(TableFile(
        ["2", "CPU 414-3 PN/DP", "2", "CPU 414-3 PN/DP", "6ES7 414-3EM05-0AB0", "V5.3", "2", "", "", ""],
        ["1", "identcontrol05", "1", "172.24.55.186", "identcontrol05", "#200877", "V3.1", "8186*", "aktiviert", "", ""],
        ["0", "identcontrol05", "0", "identcontrol05", "#200877", "", "", "8186*"],
        ["2", "akd-pn", "2", "", "akd-pn", "AKD-Pxxxxx-xxPN-xxxx", "V00.02", "2042*", "aktiviert", "", ""],
        ["3", "drive-a", "3", "10.0.0.5", "drive-a", "X-1", "V1", "2041*", "aktiviert", "", ""],
        ["4", "drive-b", "4", "10.0.0.5", "drive-b", "X-2", "V1", "2040*", "aktiviert", "", ""],
        ["Gerätenummer", "IP-Adresse", "Gerätename", "Bestellnummer", "Firmware", "Diagnoseadresse", "Initialzustand", "shared", "Kommentar"]));

    [Fact]
    public void ReadsOnlyDeviceListRows() =>
        Assert.Equal(["identcontrol05", "akd-pn", "drive-a", "drive-b"], Devices.Select(d => d.Name));

    [Fact]
    public void RenamedDeviceIsFoundByItsIpAddress()
    {
        var row = HardwareReader.DeviceListRow("IDENTControl", "172.24.55.186", 1, Devices);
        Assert.Equal(("#200877", "V3.1"), (row?.OrderNo, row?.Firmware));
    }

    [Fact]
    public void RowWithoutIpAddressIsFoundByName()
    {
        var row = HardwareReader.DeviceListRow("AKD-PN", null, 0, Devices);
        Assert.Equal(("AKD-Pxxxxx-xxPN-xxxx", "V00.02"), (row?.OrderNo, row?.Firmware));
    }

    [Fact]
    public void SharedIpAddressIsNotMatched()
    {
        Assert.Null(HardwareReader.DeviceListRow("Drive", "10.0.0.5", 1, Devices));  // two rows
        Assert.Null(HardwareReader.DeviceListRow("Other", "172.24.55.186", 2, Devices));  // two devices
    }
}
