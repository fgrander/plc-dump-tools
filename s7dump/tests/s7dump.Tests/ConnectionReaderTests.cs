using System.Text;
using S7Dump;
using Xunit;

namespace S7Dump.Tests;

/// <summary>Configured connections from synthetic project files: tables, link files
/// and compiled records, as seen in the myNetw sample projects.</summary>
public class ConnectionReaderTests
{
    private static readonly byte[] Tail =
    [
        0x1c, 0x01, 0x08, 0x02, 0x00, 0x01, 0x00, 0x00, 0x00, 0x12, 0x03, 0x03, 0x02, 0x00,
        0x04, 0x04, 0x12, 0x02, 0x06, 0x06, 0x0a, 0x05, 0x05, 0x05, 0x04, 0x07, 0x03, 0x00,
    ];

    [Fact]
    public void ParsesTheTailOfACompiledRecord()
    {
        var record = ConnectionReader.ParseCompiledTail([.. new byte[78], .. Tail], "sdb/1/a.PG");
        Assert.NotNull(record);
        Assert.Equal((true, 0x12, "12.02", "10.5.5.5", "03.00"),
            (record.Active, record.LocalId, record.LocalTsap, record.PartnerIp, record.PartnerTsap));
    }

    [Fact]
    public void FileWithoutTheTailIsNoConnectionRecord()
    {
        Assert.Null(ConnectionReader.ParseCompiledTail(new byte[106]));
        Assert.Null(ConnectionReader.ParseCompiledTail([.. Tail, 0x00]));  // the tail is not at the end
        Assert.Null(ConnectionReader.ParseCompiledTail(Tail[..20]));
    }

    [Fact]
    public void TsapHasTwoDigitsPerByte() => Assert.Equal("03.00", ConnectionReader.Tsap(3, 0));

    [Fact]
    public void AddressFromEightHexDigits()
    {
        Assert.Equal("10.102.10.20", ConnectionReader.Ip("0A660A14"));
        Assert.Null(ConnectionReader.Ip("0A66"));
    }

    private static ConnectionReader.Compiled Record(int id, string tsap, string ip) =>
        new("f", true, id, tsap, ip, "10.02");

    [Fact]
    public void CompiledRecordIsMatchedByIdPlaceAndPartnerAddress()
    {
        var owner = new ConnectionReader.Owner("St", 0, 2, "CPU");
        ConnectionReader.Compiled[] records =
            [Record(1, "10.02", "10.0.0.1"), Record(1, "10.02", "10.0.0.2"), Record(1, "10.03", "10.0.0.1")];
        Assert.Equal("10.0.0.2", ConnectionReader.Match(records, 1, owner, "10.0.0.2")?.PartnerIp);
        Assert.Null(ConnectionReader.Match(records, 1, owner, "10.0.0.9"));  // two candidates, none exact
        Assert.Null(ConnectionReader.Match(records, 2, owner, "10.0.0.1"));
        // changed after the last compile: the only record of this ID and place is still the record
        Assert.Equal("10.0.0.1", ConnectionReader.Match([records[2]], 1, owner with { Slot = 3 }, "10.0.0.9")?.PartnerIp);
    }

    // ---------------------------------------------------------------- a synthetic project
    private static byte[] DbfFile(string[] fields, int[] lengths, params (bool Deleted, string[] Values)[] rows)
    {
        var record = 1 + lengths.Sum();
        var header = 32 + 32 * fields.Length + 1;
        var b = new byte[header + rows.Length * record];
        b[0] = 0x03;
        BitConverter.GetBytes(rows.Length).CopyTo(b, 4);
        BitConverter.GetBytes((ushort)header).CopyTo(b, 8);
        BitConverter.GetBytes((ushort)record).CopyTo(b, 10);
        for (var i = 0; i < fields.Length; i++)
        {
            Encoding.ASCII.GetBytes(fields[i]).CopyTo(b, 32 + 32 * i);
            b[32 + 32 * i + 11] = (byte)'C';
            b[32 + 32 * i + 16] = (byte)lengths[i];
        }
        b[header - 1] = 0x0D;
        for (var r = 0; r < rows.Length; r++)
        {
            var at = header + r * record;
            b[at++] = (byte)(rows[r].Deleted ? '*' : ' ');
            for (var i = 0; i < fields.Length; i++)
            {
                Encoding.Latin1.GetBytes(rows[r].Values[i].PadRight(lengths[i])).CopyTo(b, at);
                at += lengths[i];
            }
        }
        return b;
    }

    // a KNIL link file: one 512-byte block per entry, references of 8 bytes from offset 16
    private static byte[] LinkFile(params (uint Type, uint Id)[][] blocks)
    {
        var b = new byte[512 * (blocks.Length + 1)];
        Encoding.ASCII.GetBytes("KNIL").CopyTo(b, 0);
        for (var i = 0; i < blocks.Length; i++)
        {
            var at = 512 * (i + 1) + 16;
            foreach (var (type, id) in blocks[i])
            {
                BitConverter.GetBytes(type).CopyTo(b, at);
                BitConverter.GetBytes(id).CopyTo(b, at + 4);
                at += 8;
            }
        }
        return b;
    }

    private static string Project()
    {
        var dir = Directory.CreateTempSubdirectory("s7dump-conn").FullName;
        var conn = Directory.CreateDirectory(Path.Combine(dir, "CONN")).FullName;
        var list = Directory.CreateDirectory(Path.Combine(conn, "CO_2")).FullName;
        var hw = Directory.CreateDirectory(Path.Combine(dir, "hOmSave7", "S7HK31AX")).FullName;
        var sdb = Directory.CreateDirectory(Path.Combine(dir, "sdb", "00000001")).FullName;

        File.WriteAllBytes(Path.Combine(conn, "VERBTAB.DBF"), DbfFile(
            ["ID", "LINKID"], [11, 11],
            (true, ["1", "512"]),      // a deleted list
            (false, ["2", "1024"])));
        File.WriteAllBytes(Path.Combine(conn, "LINKVL.dbf"), LinkFile(
            [(0x00145301, 1)],
            [(0x00145301, 2), (0x00145401, 1), (0x36, 2), (1314974, 1), (2366073, 2), (0x35, 1)]));
        string[] verb = ["ID", "TYPE", "NAME", "AUFBAU", "LFDNR", "UNSPEZ", "EINSEITIG", "CREATOR", "LOCALID", "LINKID"];
        int[] verbLengths = [11, 11, 24, 3, 5, 3, 3, 40, 11, 11];
        File.WriteAllBytes(Path.Combine(list, "HOMOVERB.DBF"), DbfFile(verb, verbLengths,
            (false, ["2", "1332225", "S7-Verbindung 2", "0", "17", "1", "1", "someone", "16", "512"]),
            (true, ["9", "1332225", "deleted", "1", "20", "1", "1", "someone", "9", "1536"]),
            (false, ["1", "1332225", "S7-Verbindung 1", "1", "16", "0", "1", "someone", "1", "1024"])));
        File.WriteAllBytes(Path.Combine(list, "HOMTABV4.DBF"), DbfFile(
            ["ID", "UN_MODNAME", "UN_LFDNO", "UN_RACKNO", "UN_SLOTNO", "UN_TNADR"], [11, 25, 5, 5, 5, 32],
            (false, ["2", "HomePLC3", "16", "0", "3", "0A660A14"]),
            (false, ["1", "", "3", "0", "0", ""])));
        File.WriteAllBytes(Path.Combine(list, "HOMOLINK.dbf"), LinkFile(
            [(0x00145203, 4), (0x6c, 4), (0x00145301, 2)],
            [(0x00145203, 8), (0x6c, 4), (0x00145203, 4), (0x6c, 4)]));
        File.WriteAllBytes(Path.Combine(hw, "HOBJECT1.DBF"), DbfFile(
            ["ID", "OBJTYP", "UNITID", "UNITTYP", "NAME", "MODULN", "SUBMODN"], [11, 11, 11, 11, 30, 5, 5],
            (false, ["1", "1314969", "53", "1122305", "SIMATIC 300-Station", "-1", "-1"]),
            (false, ["1", "1314974", "1", "1314969", "UR", "0", "0"]),
            (false, ["2", "2366073", "1", "1314974", "CPU 317F-2 PN/DP", "2", "0"])));
        // compiled: ID 0x10 passive 11.02 -> 10.102.10.20 / 10.03; ID 1 active 10.02 -> 10.60.10.2 / 03.02
        File.WriteAllBytes(Path.Combine(sdb, "0000002f.PG"),
        [
            .. new byte[78], 0x1c, 0x01, 0x08, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10, 0x03, 0x03, 0x02, 0x00,
            0x04, 0x04, 0x11, 0x02, 0x06, 0x06, 0x0a, 0x66, 0x0a, 0x14, 0x04, 0x07, 0x10, 0x03,
        ]);
        File.WriteAllBytes(Path.Combine(sdb, "00000030.PG"),
        [
            .. new byte[78], 0x1c, 0x01, 0x08, 0x02, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x03, 0x03, 0x02, 0x00,
            0x04, 0x04, 0x10, 0x02, 0x06, 0x06, 0x0a, 0x3c, 0x0a, 0x02, 0x04, 0x07, 0x03, 0x02,
        ]);
        File.WriteAllBytes(Path.Combine(sdb, "00000031.PG"), new byte[200]);  // not a connection record
        return dir;
    }

    private static EthernetReader.Interface Node(int node, string station, int slot, string module, string ip) =>
        new(node, station, 0, slot, module, module, ip, "255.255.255.0", null, null, null, null, null);

    [Fact]
    public void ReadsConnectionsWithOwnerPartnerAndTsaps()
    {
        var errors = new List<string>();
        var connections = ConnectionReader.Read(
            Project(),
            [Node(4, "SIMATIC 300-Station", 2, "CPU 317F-2 PN/DP", "10.100.10.20"),
             Node(8, "SIMATIC 400(1)", 2, "CPU 414-3 PN/DP", "10.60.10.2")],
            (where, message) => errors.Add($"{where}: {message}"));
        Assert.Empty(errors);
        Assert.Equal([1, 16], connections.Select(c => c.LocalId));  // deleted row and list skipped

        var inProject = connections[0];
        Assert.Equal((2, "S7-Verbindung 1", true, true, false), (inProject.List, inProject.Name, inProject.Active, inProject.OneWay, inProject.Unspecified));
        Assert.Equal((4, 8), (inProject.LocalNode, inProject.PartnerNode));
        Assert.Null(inProject.PartnerName);
        Assert.Null(inProject.PartnerIp);
        Assert.Equal(("10.02", "10.60.10.2", "03.02"), (inProject.Compiled?.LocalTsap, inProject.Compiled?.PartnerIp, inProject.Compiled?.PartnerTsap));

        var unspecified = connections[1];
        Assert.Equal(new ConnectionReader.Owner("SIMATIC 300-Station", 0, 2, "CPU 317F-2 PN/DP"), unspecified.Owner);
        Assert.Equal((false, 17, "HomePLC3", 0, 3, 16, "10.102.10.20"),
            (unspecified.Active, unspecified.LocalResource, unspecified.PartnerName, unspecified.PartnerRack,
             unspecified.PartnerSlot, unspecified.PartnerResource, unspecified.PartnerIp));
        Assert.Equal((4, null), (unspecified.LocalNode, unspecified.PartnerNode));
        Assert.Equal(("sdb/00000001/0000002f.PG", false, "11.02", "10.03"),
            (unspecified.Compiled?.File, unspecified.Compiled?.Active, unspecified.Compiled?.LocalTsap, unspecified.Compiled?.PartnerTsap));
        Assert.DoesNotContain("someone", unspecified.ToJson().ToJsonString());  // CREATOR is never read
    }

    [Fact]
    public void ProjectWithoutConnectionTablesHasNoConnections() =>
        Assert.Empty(ConnectionReader.Read(Directory.CreateTempSubdirectory("s7dump-none").FullName, [], (_, _) => { }));

    [Fact]
    public void RecognizesCallsOfCommunicationBlocks()
    {
        // networks with such a call get their statements without call reconstruction
        var callees = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "FB12", "SFB14", "\"BSEND\"" };
        Assert.True(Dumper.IsCommCall("      UC    \"BSEND\"", callees));
        Assert.True(Dumper.IsCommCall("      UC    FB    12", callees));
        Assert.True(Dumper.IsCommCall("      CALL  SFB   14", callees));
        Assert.False(Dumper.IsCommCall("      UC    \"Ethernet_Comm\"", callees));
        Assert.False(Dumper.IsCommCall("      UC    FB    120", callees));
        Assert.False(Dumper.IsCommCall("      L     W#16#1005", callees));
    }

    [Fact]
    public void ReaderSourceUsesNoNetworkApi()
    {
        // addresses are data; the reader must not be able to contact a device
        var dir = AppContext.BaseDirectory;
        while (dir is not null && !File.Exists(Path.Combine(dir, "Dump", "ConnectionReader.cs"))) dir = Path.GetDirectoryName(dir);
        Assert.NotNull(dir);
        var source = File.ReadAllText(Path.Combine(dir, "Dump", "ConnectionReader.cs"));
        foreach (var forbidden in (string[])["System.Net", "Socket", "TcpClient", "PLCConnection", "HttpClient"])
        {
            Assert.DoesNotContain(forbidden, source);
        }
    }
}
