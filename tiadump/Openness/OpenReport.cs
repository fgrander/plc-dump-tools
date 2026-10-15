// What an open reports besides the project itself. No Siemens types here
// (unit-testable without TIA).
// - Upgrade messages: TIA raises no notifications while upgrading; it writes
//   <original project>\Logs\ConversionLog_<from>_to_<to>.xml (MessageCell elements with
//   MessageClass Information|Warning|Error|Success, texts in the TIA UI language).
// - Missing packages: Project.UsedProducts against TiaPortalProcess.InstalledSoftware. Installed
//   names can bundle several products ("WinCC Basic/Comfort/Advanced V21" covers "WinCC Comfort V21").
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Xml;
using System.Xml.Linq;

namespace TiaDump.Openness
{
    public static class OpenReport
    {
        /// <summary>"Warning: text" for every non-informational message of the conversion logs below <paramref name="folder"/>.</summary>
        public static List<string> UpgradeMessages(string folder)
        {
            var result = new List<string>();
            if (!Directory.Exists(folder)) return result;
            var logs = Directory.EnumerateFiles(folder, "ConversionLog_*_to_*.xml", SearchOption.AllDirectories)
                .Where(f => string.Equals(Path.GetFileName(Path.GetDirectoryName(f)), "Logs", StringComparison.OrdinalIgnoreCase))
                .OrderBy(f => f, StringComparer.Ordinal)
                // TIA writes the same log into the original and the upgraded <name>_V21 folder.
                .GroupBy(f => Path.GetFileName(f), StringComparer.OrdinalIgnoreCase)
                .Select(g => g.First());
            foreach (var log in logs)
            {
                XDocument doc;
                try { doc = XDocument.Load(log); }
                catch (Exception e) when (e is IOException || e is XmlException)
                {
                    result.Add($"Warning: conversion log {Path.GetFileName(log)} unreadable: {e.Message}");
                    continue;
                }
                foreach (var cell in doc.Descendants("MessageCell"))
                {
                    var cls = (string?)cell.Attribute("MessageClass") ?? "";
                    if (cls == "Information" || cls == "Success") continue;
                    var text = (string?)cell.Element("Text")?.Attribute("FeedbackText") ?? "";
                    result.Add($"{cls}: {text}".Trim());
                }
            }
            return result;
        }

        private static readonly Regex Technical = new Regex(@"\b(\d{1,2})00\.(\d+)\.\d+\.\d+\b");

        /// <summary>Saved update level ("Upd3") from the conversion log, which names the technical source version (1900.3.501.1).</summary>
        public static string? SavedUpdate(string folder, int savedMajor)
        {
            if (!Directory.Exists(folder)) return null;
            foreach (var log in Directory.EnumerateFiles(folder, "ConversionLog_*_to_*.xml", SearchOption.AllDirectories))
            {
                string text;
                try { text = File.ReadAllText(log); }
                catch (IOException) { continue; }
                foreach (Match m in Technical.Matches(text))
                    if (int.Parse(m.Groups[1].Value) == savedMajor) return $"Upd{m.Groups[2].Value}";
            }
            return null;
        }

        /// <summary>Used products that no installed product covers, as "name version".</summary>
        public static List<string> MissingProducts(IEnumerable<(string Name, string Version)> used, IEnumerable<(string Name, string Version)> installed)
        {
            var covered = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var (name, version) in installed)
                foreach (var single in Expand(name)) covered.Add($"{single}|{version}");
            return used
                .Where(u => !covered.Contains($"{u.Name}|{u.Version}"))
                .Select(u => $"{u.Name} {u.Version}")
                .OrderBy(x => x, StringComparer.Ordinal)
                .ToList();
        }

        // "WinCC Basic/Comfort/Advanced" -> WinCC Basic, WinCC Comfort, WinCC Advanced (and the name itself).
        private static IEnumerable<string> Expand(string name)
        {
            yield return name;
            if (!name.Contains("/")) yield break;
            var parts = name.Split('/');
            var first = parts[0];
            var space = first.LastIndexOf(' ');
            var prefix = space >= 0 ? first.Substring(0, space + 1) : "";
            yield return first;
            foreach (var p in parts.Skip(1)) yield return prefix + p.Trim();
        }
    }
}
