// Remove everything a job left behind.
// --work is deleted completely. Files TIA Portal writes elsewhere for the job are found by
// Comparing snapshots of the known TIA locations before and after the job (Cleanup.Locations names the
// locations); anything that cannot be deleted is reported in dump.json `cleanup.outside_work`.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace TiaDump.Openness
{
    public sealed class Cleanup
    {
        private readonly string _work;
        private readonly Dictionary<string, HashSet<string>> _before = new Dictionary<string, HashSet<string>>();

        /// <summary>Folders TIA Portal may write to for one project.</summary>
        public static IEnumerable<string> KnownLocations()
        {
            var temp = Path.GetTempPath();
            var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            var roaming = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            yield return Path.Combine(temp, "Siemens");
            yield return Path.Combine(local, "Siemens", "Automation", "Portal V" + (AssemblyResolver.PortalVersion ?? "").TrimStart('V'), "Temp");
            yield return Path.Combine(roaming, "Siemens", "Automation", "Portal V" + (AssemblyResolver.PortalVersion ?? "").TrimStart('V'), "Temp");
        }

        public Cleanup(string work)
        {
            _work = work;
            foreach (var dir in KnownLocations()) _before[dir] = Snapshot(dir);
        }

        public static HashSet<string> Snapshot(string dir)
        {
            if (!Directory.Exists(dir)) return new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            try
            {
                return new HashSet<string>(
                    Directory.EnumerateFileSystemEntries(dir, "*", SearchOption.TopDirectoryOnly),
                    StringComparer.OrdinalIgnoreCase);
            }
            catch (IOException) { return new HashSet<string>(StringComparer.OrdinalIgnoreCase); }
            catch (UnauthorizedAccessException) { return new HashSet<string>(StringComparer.OrdinalIgnoreCase); }
        }

        /// <summary>Delete the job's files; returns what could not be deleted.</summary>
        public List<string> Run()
        {
            var left = new List<string>();
            foreach (var pair in _before)
            {
                foreach (var entry in Snapshot(pair.Key).Except(pair.Value, StringComparer.OrdinalIgnoreCase))
                    if (!TryDelete(entry)) left.Add(entry);
            }
            if (Directory.Exists(_work) && !TryDelete(_work)) left.Add(_work);
            left.Sort(StringComparer.Ordinal);
            return left;
        }

        private static bool TryDelete(string path)
        {
            for (var attempt = 0; attempt < 5; attempt++)
            {
                try
                {
                    if (Directory.Exists(path))
                    {
                        foreach (var f in Directory.EnumerateFiles(path, "*", SearchOption.AllDirectories))
                            File.SetAttributes(f, FileAttributes.Normal);
                        Directory.Delete(path, true);
                    }
                    else if (File.Exists(path))
                    {
                        File.SetAttributes(path, FileAttributes.Normal);
                        File.Delete(path);
                    }
                    return true;
                }
                catch (IOException) { System.Threading.Thread.Sleep(500); }
                catch (UnauthorizedAccessException) { System.Threading.Thread.Sleep(500); }
            }
            return !Directory.Exists(path) && !File.Exists(path);
        }
    }
}
