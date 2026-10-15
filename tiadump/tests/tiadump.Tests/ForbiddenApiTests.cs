// Read-only guard. Fails the build when any
// Tiadump source calls a TIA Openness API that writes, compiles, downloads or goes online.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using Xunit;

namespace TiaDump.Tests
{
    public class ForbiddenApiTests
    {
        public static readonly string[] Forbidden =
        {
            "Save", "SaveAs", "Compile", "Download", "GoOnline", "Upload", "Import", "ImportFromDocuments",
            "SetAttribute", "SetAttributes", "Delete", "Create", "CreateFrom", "Archive", "UpdateLibrary",
            "UpdateProject", "CleanUpLibrary",
        };

        // The only places allowed to call these (all on the copy in --work).
        private static readonly Dictionary<string, string[]> Allowed = new Dictionary<string, string[]>
        {
            ["Retrieve"] = new[] { "Openness/TiaSession.cs" },
            ["RetrieveWithUpgrade"] = new[] { "Openness/TiaSession.cs" },
            ["OpenWithUpgrade"] = new[] { "Openness/TiaSession.cs" },
            // compile only units of the working copy that SD cannot export
            ["Compile"] = new[] { "Openness/CopyCompiler.cs" },
        };

        // ".Name(" and generic ".Name<T>(" member calls (ConnectionComposition.Create<T>,
        // Connection.Delete); plain C# library calls on these types are not Openness calls.
        private static readonly Regex Call = new Regex(@"\.\s*(?<name>[A-Z][A-Za-z]*)\s*(<[^<>()]*>)?\s*\(", RegexOptions.Compiled);
        private static readonly string[] SafeReceivers = { "File.", "Directory.", "Path.", "Json.", "Regex.", "sb.", "Console." };

        public static string ToolRoot()
        {
            var dir = new DirectoryInfo(AppContext.BaseDirectory);
            while (dir != null && !File.Exists(Path.Combine(dir.FullName, "tiadump.csproj"))) dir = dir.Parent;
            return dir?.FullName ?? throw new InvalidOperationException("tiadump.csproj not found above the test output");
        }

        /// <summary>The TIA sample folder: samples/tia-portal in the repository root, or TIADUMP_SAMPLES_DIR.</summary>
        public static string SampleRoot()
        {
            var env = Environment.GetEnvironmentVariable("TIADUMP_SAMPLES_DIR");
            return string.IsNullOrEmpty(env)
                ? Path.GetFullPath(Path.Combine(ToolRoot(), "..", "samples", "tia-portal"))
                : env!;
        }

        public static List<string> Violations(string root)
        {
            var found = new List<string>();
            foreach (var file in Directory.EnumerateFiles(root, "*.cs", SearchOption.AllDirectories))
            {
                var rel = file.Substring(root.Length + 1).Replace('\\', '/');
                if (rel.StartsWith("tests/", StringComparison.Ordinal) || rel.Contains("/obj/") || rel.Contains("/bin/")
                    || rel.StartsWith("obj/", StringComparison.Ordinal) || rel.StartsWith("bin/", StringComparison.Ordinal))
                    continue;
                var lines = File.ReadAllLines(file);
                for (var i = 0; i < lines.Length; i++)
                {
                    var line = lines[i];
                    var code = line.Split(new[] { "//" }, StringSplitOptions.None)[0];
                    foreach (Match m in Call.Matches(code))
                    {
                        var name = m.Groups["name"].Value;
                        if (Allowed.TryGetValue(name, out var files) && files.Contains(rel)) continue;
                        if (!Forbidden.Contains(name) && !Allowed.ContainsKey(name)) continue;
                        var start = Math.Max(0, m.Index - 12);
                        var before = code.Substring(start, m.Index - start + 1);
                        if (SafeReceivers.Any(r => before.EndsWith(r, StringComparison.Ordinal))) continue;
                        found.Add($"{rel}:{i + 1}: {name}");
                    }
                }
            }
            return found;
        }

        [Fact]
        public void ToolSourcesCallNoWriteOrOnlineApi()
        {
            var violations = Violations(ToolRoot());
            Assert.True(violations.Count == 0, "forbidden Openness calls:\n" + string.Join("\n", violations));
        }

        [Fact]
        public void ScannerFindsAPlantedForbiddenCall()
        {
            var root = Path.Combine(Path.GetTempPath(), "tiadump-forbidden-" + Guid.NewGuid().ToString("N"));
            try
            {
                Directory.CreateDirectory(Path.Combine(root, "Dump"));
                File.WriteAllText(Path.Combine(root, "tiadump.csproj"), "<Project />");
                File.WriteAllText(Path.Combine(root, "Dump", "Bad.cs"), "class Bad { void M(dynamic p) { p.Save(); p.Compile(); } }");
                File.WriteAllText(Path.Combine(root, "Dump", "Good.cs"), "class Good { void M() { System.IO.File.Delete(\"x\"); } // p.Save()\n }");
                File.WriteAllText(Path.Combine(root, "Dump", "Retrieve.cs"), "class R { void M(dynamic p) { p.Retrieve(null, null); } }");
                File.WriteAllText(Path.Combine(root, "Dump", "Conn.cs"), "class C { void M(dynamic c) { c.Connections.Create<S7Connection>(a, b, d); c.Delete(); } }");
                var v = Violations(root);
                Assert.Contains("Dump/Bad.cs:1: Save", v);
                Assert.Contains("Dump/Bad.cs:1: Compile", v);
                Assert.Contains("Dump/Retrieve.cs:1: Retrieve", v);  // only TiaSession may retrieve
                Assert.Contains("Dump/Conn.cs:1: Create", v);  // generic create of a connection
                Assert.Contains("Dump/Conn.cs:1: Delete", v);
                Assert.DoesNotContain(v, x => x.StartsWith("Dump/Good.cs", StringComparison.Ordinal));
            }
            finally
            {
                Directory.Delete(root, true);
            }
        }
    }
}
