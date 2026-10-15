// Probe reads version, kind and ProjectInfo.txt without TIA Portal.
using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Text;
using TiaDump.Dump;
using Xunit;

namespace TiaDump.Tests
{
    public class ProbeTests
    {
        private static string Temp(string name, string content = "")
        {
            var dir = Path.Combine(Path.GetTempPath(), "tiadump-probe-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(dir);
            var path = Path.Combine(dir, name);
            File.WriteAllText(path, content, Encoding.UTF8);
            return path;
        }

        [Theory]
        [InlineData("Line3.ap18", "project", false, "V18")]
        [InlineData("Line3.zap19", "project", true, "V19")]
        [InlineData("Std.al21", "library", false, "V21")]
        [InlineData("Std.zal20", "library", true, "V20")]
        [InlineData("ThreeTank.zap20.zap20", "project", true, "V20")]
        [InlineData("Line3.als21", "local_session", false, "V21")]
        public void KindAndMajorVersionFromSuffix(string name, string kind, bool archive, string version)
        {
            var r = Probe.Inspect(Temp(name));
            Assert.Equal(kind, r["kind"]);
            Assert.Equal(archive, r["archive"]);
            Assert.Equal(version, r["saved_version"]);
        }

        [Fact]
        public void UpdateLevelFromProjectHeaderWhenPresent()
        {
            var path = Temp("Line3.ap20", "<Project><Version>TIA Portal V20 Update 4</Version></Project>");
            Assert.Equal("Upd4", Probe.Inspect(path)["saved_update"]);
        }

        [Fact]
        public void UpdateLevelOfAnotherVersionIsIgnored()
        {
            var path = Temp("Line3.ap20", "<Project>created with V19 Update 2</Project>");
            Assert.Null(Probe.Inspect(path)["saved_update"]);
        }

        // ProjectInfo.txt as TIA V21 writes it (Step7.zap21 sample), with Update 4
        private const string ProjectInfoV21 =
            "TiaPortal:\r\n  MinimumRequired:\r\n  - Version: V21.0\r\n  - TechnicalVersion: 21.00.00.00\r\n" +
            "  LastUsed:\r\n  - Version: V21\r\n  - TechnicalVersion: 21.00.04.00\r\n\r\n" +
            "UsedProducts:\r\n- Name: STEP 7 Professional\r\n  Version: V21\r\n  TechnicalVersion: 21.00.00.00\r\n" +
            "- Name: STEP 7 Safety\r\n  Version: V21\r\n  TechnicalVersion: 21.00.00.00\r\n\r\n" +
            "UsedSupportPackages:\r\n- Name: S7-1500 Motion Control\r\n  Version: V17\r\n  TechnicalVersion: 17.00.00.00\r\n";

        private static List<object?> List(object? value) => (List<object?>)value!;

        private static Dictionary<string, object?> Row(object? value) => (Dictionary<string, object?>)value!;

        [Fact]
        public void ArchiveProjectInfoGivesUpdateProductsAndSupportPackages()
        {
            var path = Temp("Line3.zap21");
            File.Delete(path);
            using (var zip = ZipFile.Open(path, ZipArchiveMode.Create))
            {
                var entry = zip.CreateEntry("ProjectInfo.txt");
                using (var w = new StreamWriter(entry.Open(), new UTF8Encoding(false))) w.Write(ProjectInfoV21);
                zip.CreateEntry("Line3.ap21");
            }
            var r = Probe.Inspect(path);
            Assert.Equal("Upd4", r["saved_update"]);
            var products = List(r["used_products"]);
            Assert.Equal(2, products.Count);
            Assert.Equal("STEP 7 Professional", Row(products[0])["name"]);
            Assert.Equal("V21", Row(products[0])["version"]);
            Assert.Equal("S7-1500 Motion Control", Row(List(r["used_support_packages"])[0])["name"]);
        }

        [Fact]
        public void ProjectInfoNextToAProjectFile()
        {
            var path = Temp("Line3.ap21");
            File.WriteAllText(Path.Combine(Path.GetDirectoryName(path)!, "ProjectInfo.txt"), ProjectInfoV21);
            Assert.Equal("Upd4", Probe.Inspect(path)["saved_update"]);
        }

        [Fact]
        public void WithoutProjectInfoTheListsAreEmpty()
        {
            var r = Probe.Inspect(Temp("Line3.zap19"));
            Assert.Null(r["saved_update"]);
            Assert.Empty(List(r["used_products"]));
            Assert.Empty(List(r["used_support_packages"]));
        }

        [Fact]
        public void TechnicalVersionWithoutUpdateGivesNoUpdate()
        {
            var info = Probe.ParseProjectInfo("TiaPortal:\n  LastUsed:\n  - Version: V21\n  - TechnicalVersion: 21.00.00.00\n");
            Assert.Equal("21.00.00.00", info.LastUsedTechnicalVersion);
            Assert.Null(info.Update);
        }

        [Fact]
        public void NotATiaFileIsAUsageError()
        {
            var e = Assert.Throws<ExitException>(() => Probe.Inspect(Temp("readme.txt")));
            Assert.Equal(ExitCodes.Usage, e.Code);
        }
    }
}
