// `tiadump installed --tia V21 --out installed.json` (docs/tiadump-installed.md).
// The software of one TIA Portal installation, so that an export worker can declare it.
// Starts TIA Portal without user interface and opens no project: read-only by construction.
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using Siemens.Engineering;
using TiaDump.Openness;

namespace TiaDump.Dump
{
    public static class Installed
    {
        public const string Portal = "Totally Integrated Automation Portal";
        private static readonly Regex UpdatePart = new Regex(@"\b(?:Upd(?:ate)?)\s*(\d+)", RegexOptions.IgnoreCase);

        public static int Run(Options o)
        {
            List<(string Name, string Version)> items;
            try
            {
                using (var portal = new TiaPortal(TiaPortalMode.WithoutUserInterface))
                {
                    items = portal.GetCurrentProcess().InstalledSoftware.Select(s => (s.Name, s.Version)).ToList();
                }
            }
            catch (EngineeringSecurityException e)
            {
                throw new ExitException(ExitCodes.AccessDenied, $"Openness access denied: {e.Message}");
            }
            Json.WriteFile(o.Out!, Document(AssemblyResolver.PortalVersion ?? "", items));
            return ExitCodes.Ok;
        }

        /// <summary>installed.json: the installation's major and update, its software by name.</summary>
        public static Dictionary<string, object?> Document(string portalVersion, IEnumerable<(string Name, string Version)> items)
        {
            var list = items.ToList();
            var portal = list.FirstOrDefault(i => string.Equals(i.Name, Portal, StringComparison.OrdinalIgnoreCase));
            return new Dictionary<string, object?>
            {
                ["tool"] = new Dictionary<string, object?> { ["name"] = "tiadump", ["version"] = Program.Version, ["openness"] = portalVersion },
                ["tia"] = new Dictionary<string, object?> { ["version"] = portalVersion, ["update"] = UpdateOf(portal.Version) },
                ["installed"] = list
                    .OrderBy(i => i.Name, StringComparer.Ordinal).ThenBy(i => i.Version, StringComparer.Ordinal)
                    .Select(i => (object?)new Dictionary<string, object?> { ["name"] = i.Name, ["version"] = i.Version })
                    .ToList(),
            };
        }

        /// <summary>"V21 Update 2" or "V20 Upd4" -> "Upd2"/"Upd4"; no update -> null.</summary>
        public static string? UpdateOf(string? version)
        {
            var m = UpdatePart.Match(version ?? "");
            return m.Success && int.Parse(m.Groups[1].Value) > 0 ? $"Upd{m.Groups[1].Value}" : null;
        }
    }
}
