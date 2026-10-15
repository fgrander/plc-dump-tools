// The installed.json document (docs/tiadump-installed.md), without TIA Portal.
using System.Collections.Generic;
using TiaDump.Dump;
using Xunit;

namespace TiaDump.Tests
{
    public class InstalledTests
    {
        private static List<object?> List(object? value) => (List<object?>)value!;

        private static Dictionary<string, object?> Row(object? value) => (Dictionary<string, object?>)value!;

        [Fact]
        public void SoftwareIsSortedByNameWithTheUpdateOfThePortal()
        {
            var doc = Installed.Document("V21", new[]
            {
                ("STEP 7 Safety", "V21"),
                ("Totally Integrated Automation Portal", "V21 Update 2"),
                ("HSP 0345 SINAMICS G220", "V21"),
                ("STEP 7 Professional", "V21"),
            });
            var tia = (Dictionary<string, object?>)doc["tia"]!;
            Assert.Equal("V21", tia["version"]);
            Assert.Equal("Upd2", tia["update"]);
            var names = new List<string?>();
            foreach (var r in List(doc["installed"])) names.Add((string?)Row(r)["name"]);
            Assert.Equal(new[] { "HSP 0345 SINAMICS G220", "STEP 7 Professional", "STEP 7 Safety", "Totally Integrated Automation Portal" }, names);
            Assert.Equal("V21", ((Dictionary<string, object?>)doc["tool"]!)["openness"]);
        }

        [Theory]
        [InlineData("V21", null)]
        [InlineData("V21 Update 2", "Upd2")]
        [InlineData("V20 Upd4", "Upd4")]
        [InlineData("V20 Update 0", null)]
        [InlineData(null, null)]
        public void UpdateLevel(string? version, string? update)
        {
            Assert.Equal(update, Installed.UpdateOf(version));
        }
    }
}
