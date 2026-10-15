// `tiadump project` on a real sample (TIA host only: dotnet test with filter
// "Category=tia"). Uses the published tiadump.exe, works on a copy and checks that the sample
// Is unchanged afterwards.
using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using Xunit;

namespace TiaDump.Tests
{
    [Collection("tia")]  // one TIA Portal instance at a time (about 3 GB each)
    public class ProjectDumpTests
    {
        private static string Hash(string file)
        {
            using var sha = SHA256.Create();
            using var s = File.OpenRead(file);
            return Convert.ToBase64String(sha.ComputeHash(s));
        }

        [Fact]
        [Trait("Category", "tia")]
        public void DumpsAV21SampleAndLeavesTheSourceUnchanged()
        {
            var sample = Path.Combine(ForbiddenApiTests.SampleRoot(), "24-openness-code-snippets", "Step7.zap21");
            var exe = Path.Combine(ForbiddenApiTests.ToolRoot(), "publish", "tiadump.exe");
            if (!File.Exists(sample) || !File.Exists(exe)) return;  // no sample or no build on this machine

            var root = Path.Combine(Path.GetPathRoot(Path.GetTempPath())!, "tiat", Guid.NewGuid().ToString("N").Substring(0, 8));
            var work = Path.Combine(root, "w");
            var output = Path.Combine(root, "o");
            Directory.CreateDirectory(work);
            var copy = Path.Combine(work, "Step7.zap21");
            File.Copy(sample, copy);
            var before = Hash(sample);
            try
            {
                var psi = new ProcessStartInfo(exe, $"project \"{copy}\" --work \"{work}\" --out \"{output}\"")
                {
                    UseShellExecute = false, RedirectStandardError = true,
                };
                psi.EnvironmentVariables["TEMP"] = Path.Combine(root, "tmp");
                psi.EnvironmentVariables["TMP"] = Path.Combine(root, "tmp");
                Directory.CreateDirectory(Path.Combine(root, "tmp"));
                using var p = Process.Start(psi)!;
                var err = p.StandardError.ReadToEnd();
                Assert.True(p.WaitForExit(30 * 60 * 1000), "tiadump did not finish within 30 min");
                Assert.True(p.ExitCode == 0, $"exit {p.ExitCode}: {err}");

                var dump = File.ReadAllText(Path.Combine(output, "dump.json"));
                foreach (var key in new[] { "\"dump_version\": 1", "\"devices\"", "\"hardware\"", "\"counts\"", "\"errors\"", "\"cleanup\"" })
                    Assert.Contains(key, dump);
                Assert.Contains("\"part\": \"sd\"", dump);                       // SIMATIC SD route works
                Assert.True(Directory.EnumerateFiles(Path.Combine(output, "sd"), "*.s7dcl", SearchOption.AllDirectories).Any());
                Assert.Equal(before, Hash(sample));                               // the sample is untouched
            }
            finally
            {
                try { Directory.Delete(root, true); } catch (IOException) { } catch (UnauthorizedAccessException) { }
            }
        }
    }
}
