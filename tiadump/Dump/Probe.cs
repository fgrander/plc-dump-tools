// `tiadump probe` - version and kind from the file name, without starting TIA
// Portal. V21 writes ProjectInfo.txt (archive root, or next to the
// .apNN/.alNN): the update level and the products and support packages the project uses, so
// missing products can be predicted. Older files have none: update from the project
// file header when it carries one, else null, and empty lists.
using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

namespace TiaDump.Dump
{
    public static class Probe
    {
        // .alsNN is a multiuser local session: reported, never exported.
        private static readonly Regex Suffix = new Regex(@"\.(z?ap|z?al|als)(\d\d)$", RegexOptions.IgnoreCase);
        private static readonly Regex Update = new Regex(@"V(\d\d)(?:\.\d+)?\s*(?:SP\s*\d+\s*)?(?:Upd(?:ate)?\s*(\d+))", RegexOptions.IgnoreCase);

        public static Dictionary<string, object?> Inspect(string file)
        {
            var m = Suffix.Match(Path.GetFileName(file));
            if (!m.Success) throw new ExitException(ExitCodes.Usage, $"not a TIA project or library: {file}");
            var tag = m.Groups[1].Value.ToLowerInvariant();
            var major = int.Parse(m.Groups[2].Value);
            var archive = tag.StartsWith("z", StringComparison.Ordinal);
            var info = ReadProjectInfo(file, archive);
            return new Dictionary<string, object?>
            {
                ["kind"] = tag == "als" ? "local_session" : tag.EndsWith("al", StringComparison.Ordinal) ? "library" : "project",
                ["archive"] = archive,
                ["saved_version"] = $"V{major}",
                ["saved_update"] = info?.Update ?? (archive ? null : ReadUpdate(file, major)),
                ["used_products"] = Rows(info?.Products),
                ["used_support_packages"] = Rows(info?.SupportPackages),
            };
        }

        private static List<object?> Rows(List<(string Name, string Version)>? items) =>
            (items ?? new List<(string, string)>())
            .Select(p => (object?)new Dictionary<string, object?> { ["name"] = p.Name, ["version"] = p.Version })
            .ToList();

        public sealed class ProjectInfo
        {
            public string? LastUsedVersion;
            public string? LastUsedTechnicalVersion;
            public List<(string Name, string Version)> Products = new List<(string, string)>();
            public List<(string Name, string Version)> SupportPackages = new List<(string, string)>();

            /// <summary>"21.00.04.00" -> "Upd4"; no update part -> null.</summary>
            public string? Update
            {
                get
                {
                    var parts = (LastUsedTechnicalVersion ?? "").Split('.');
                    return parts.Length >= 3 && int.TryParse(parts[2], out var n) && n > 0 ? $"Upd{n}" : null;
                }
            }
        }

        /// <summary>ProjectInfo.txt of the archive (root entry) or next to the file; null if absent.</summary>
        public static ProjectInfo? ReadProjectInfo(string file, bool archive)
        {
            try
            {
                if (archive)
                {
                    using (var zip = ZipFile.OpenRead(file))
                    {
                        var entry = zip.Entries.FirstOrDefault(e =>
                            string.Equals(e.FullName, "ProjectInfo.txt", StringComparison.OrdinalIgnoreCase));
                        if (entry == null) return null;
                        using (var r = new StreamReader(entry.Open(), Encoding.UTF8)) return ParseProjectInfo(r.ReadToEnd());
                    }
                }
                var path = Path.Combine(Path.GetDirectoryName(Path.GetFullPath(file)) ?? ".", "ProjectInfo.txt");
                return File.Exists(path) ? ParseProjectInfo(File.ReadAllText(path, Encoding.UTF8)) : null;
            }
            catch (Exception e) when (e is IOException || e is InvalidDataException || e is UnauthorizedAccessException)
            {
                return null;
            }
        }

        /// <summary>The YAML subset TIA writes: sections, "- Key: value" items.</summary>
        public static ProjectInfo ParseProjectInfo(string text)
        {
            var info = new ProjectInfo();
            string section = "", sub = "";
            List<(string, string)>? list = null;
            string? name = null;
            foreach (var raw in text.Replace("\r", "").Split('\n'))
            {
                if (raw.Trim().Length == 0) continue;
                var indent = raw.Length - raw.TrimStart().Length;
                var line = raw.Trim();
                if (indent == 0 && !line.StartsWith("-", StringComparison.Ordinal) && line.EndsWith(":", StringComparison.Ordinal))
                {
                    section = line.TrimEnd(':');
                    sub = "";
                    list = section == "UsedProducts" ? info.Products : section == "UsedSupportPackages" ? info.SupportPackages : null;
                    name = null;
                    continue;
                }
                if (!line.StartsWith("-", StringComparison.Ordinal) && line.EndsWith(":", StringComparison.Ordinal))
                {
                    sub = line.TrimEnd(':');
                    continue;
                }
                var item = line.TrimStart('-', ' ');
                var colon = item.IndexOf(':');
                if (colon < 0) continue;
                var key = item.Substring(0, colon).Trim();
                var value = item.Substring(colon + 1).Trim();
                if (section == "TiaPortal" && sub == "LastUsed")
                {
                    if (key == "Version") info.LastUsedVersion = value;
                    if (key == "TechnicalVersion") info.LastUsedTechnicalVersion = value;
                }
                else if (list != null)
                {
                    if (key == "Name") name = value;
                    else if (key == "Version" && name != null) { list.Add((name, value)); name = null; }
                }
            }
            return info;
        }

        /// <summary>Update level from the first 64 KiB of a project/library file, or null.</summary>
        public static string? ReadUpdate(string file, int major)
        {
            try
            {
                var buffer = new byte[64 * 1024];
                int read;
                using (var s = File.OpenRead(file)) read = s.Read(buffer, 0, buffer.Length);
                var text = Encoding.UTF8.GetString(buffer, 0, read);
                foreach (Match u in Update.Matches(text))
                    if (int.Parse(u.Groups[1].Value) == major) return $"Upd{u.Groups[2].Value}";
            }
            catch (IOException) { }
            catch (UnauthorizedAccessException) { }
            return null;
        }

        public static int Run(Options o)
        {
            Json.WriteFile(o.Out!, Inspect(o.File));
            return ExitCodes.Ok;
        }
    }
}
