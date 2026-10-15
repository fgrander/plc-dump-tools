// State shared by the dumpers of one run (docs/tiadump.md).
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace TiaDump.Dump
{
    public sealed class DumpContext
    {
        public string Out { get; }
        public List<Dictionary<string, object?>> Errors { get; } = new List<Dictionary<string, object?>>();
        public List<string> CompiledUnits { get; } = new List<string>();
        public Dictionary<string, Dictionary<string, object?>> Counts { get; } =
            new Dictionary<string, Dictionary<string, object?>>();
        /// <summary>Product names the project uses but the host lacks.</summary>
        public List<string> MissingProducts { get; }
        public bool LicenseMissing { get; set; }

        public DumpContext(string outDir, IEnumerable<string> missingProducts)
        {
            Out = Path.GetFullPath(outDir);
            Directory.CreateDirectory(Out);
            MissingProducts = missingProducts.ToList();
        }

        public void Error(string where, string kind, string message) =>
            Errors.Add(new Dictionary<string, object?> { ["where"] = where, ["kind"] = kind, ["message"] = message });

        public void Count(string scope, string key, int value)
        {
            if (!Counts.TryGetValue(scope, out var c)) Counts[scope] = c = new Dictionary<string, object?>();
            c[key] = value;
        }

        /// <summary>Absolute path below --out for a relative POSIX path; creates the folder.</summary>
        public string PathOf(string rel)
        {
            var full = Path.Combine(Out, rel.Replace('/', Path.DirectorySeparatorChar));
            Directory.CreateDirectory(Path.GetDirectoryName(full)!);
            return full;
        }

        /// <summary>Absolute folder below --out for a relative POSIX folder; creates it.</summary>
        public DirectoryInfo DirOf(string rel)
        {
            var full = Path.Combine(Out, rel.Replace('/', Path.DirectorySeparatorChar));
            Directory.CreateDirectory(full);
            // not the DirectoryInfo that CreateDirectory returns: under .NET Framework its ToString()
            // is not the absolute path, and TIA rejects it ("'directoryInfo' cannot be a relative path")
            return new DirectoryInfo(full);
        }

        public string Rel(string fullPath) =>
            fullPath.Substring(Out.Length).TrimStart(Path.DirectorySeparatorChar).Replace(Path.DirectorySeparatorChar, '/');

        /// <summary>The first missing product of a software family (e.g. "WinCC Unified"), or null.
        /// Accessing such software can stop TIA Portal, so callers skip it.</summary>
        public string? MissingFor(params string[] productPrefixes) =>
            MissingProducts.FirstOrDefault(p => productPrefixes.Any(x => p.StartsWith(x, StringComparison.OrdinalIgnoreCase)));
    }
}
