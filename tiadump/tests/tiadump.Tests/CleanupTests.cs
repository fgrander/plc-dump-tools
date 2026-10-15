// After a `tiadump project` run the known TIA locations
// Hold no new entries of the job, and dump.json reports nothing left outside --work.
// TIA host only: dotnet test with filter "Category=tia".
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using Xunit;

namespace TiaDump.Tests
{
    [Collection("tia")]  // one TIA Portal instance at a time (about 3 GB each)
    public class CleanupTests
    {
        // the locations of Openness/Cleanup.cs, for the user's own profile and for the
        // job's TEMP folder
        private static IEnumerable<string> Locations(string jobTemp)
        {
            var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            var roaming = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            yield return Path.Combine(Path.GetTempPath(), "Siemens");
            yield return Path.Combine(jobTemp, "Siemens");
            foreach (var root in new[] { local, roaming })
            {
                var automation = Path.Combine(root, "Siemens", "Automation");
                if (!Directory.Exists(automation)) continue;
                foreach (var portal in Directory.EnumerateDirectories(automation, "Portal V*"))
                    yield return Path.Combine(portal, "Temp");
            }
        }

        private static HashSet<string> Snapshot(IEnumerable<string> dirs)
        {
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var dir in dirs)
                if (Directory.Exists(dir))
                    foreach (var e in Directory.EnumerateFileSystemEntries(dir, "*", SearchOption.TopDirectoryOnly)) seen.Add(e);
            return seen;
        }

        [Fact]
        [Trait("Category", "tia")]
        public void AJobLeavesNoFilesInTheKnownTiaLocations()
        {
            var sample = Path.Combine(ForbiddenApiTests.SampleRoot(), "24-openness-code-snippets", "Step7.zap21");
            var exe = Path.Combine(ForbiddenApiTests.ToolRoot(), "publish", "tiadump.exe");
            if (!File.Exists(sample) || !File.Exists(exe)) return;  // no sample or no build on this machine

            var root = Path.Combine(Path.GetPathRoot(Path.GetTempPath())!, "tiat", Guid.NewGuid().ToString("N").Substring(0, 8));
            var work = Path.Combine(root, "w");
            var output = Path.Combine(root, "o");
            var jobTemp = Path.Combine(root, "tmp");
            Directory.CreateDirectory(work);
            Directory.CreateDirectory(jobTemp);
            var copy = Path.Combine(work, "Step7.zap21");
            File.Copy(sample, copy);
            var locations = Locations(jobTemp).ToList();
            var before = Snapshot(locations);
            try
            {
                var psi = new ProcessStartInfo(exe, $"project \"{copy}\" --work \"{work}\" --out \"{output}\"")
                {
                    UseShellExecute = false, RedirectStandardError = true,
                };
                psi.EnvironmentVariables["TEMP"] = jobTemp;
                psi.EnvironmentVariables["TMP"] = jobTemp;
                using var p = Process.Start(psi)!;
                var err = p.StandardError.ReadToEnd();
                Assert.True(p.WaitForExit(30 * 60 * 1000), "tiadump did not finish within 30 min");
                Assert.True(p.ExitCode == 0, $"exit {p.ExitCode}: {err}");

                var left = Snapshot(locations).Except(before, StringComparer.OrdinalIgnoreCase).ToList();
                Assert.True(left.Count == 0, "left behind: " + string.Join(", ", left));
                var dump = File.ReadAllText(Path.Combine(output, "dump.json"));
                Assert.Contains("\"outside_work\": []", dump);
                // the retrieved and upgraded project copy is gone; TIA child processes may still
                // hold --work itself for a moment, the caller removes it
                Assert.False(Directory.Exists(Path.Combine(work, "retrieved")), "retrieved project copy still in --work");
            }
            finally
            {
                try { Directory.Delete(root, true); } catch (IOException) { } catch (UnauthorizedAccessException) { }
            }
        }
    }
}
