// Load Siemens.Engineering*.dll from the installed TIA Portal.
// Registry layout (V21): HKLM\SOFTWARE\Siemens\Automation\Openness\21.0\PublicAPI\21.0.0.0\net48
// With value "Siemens.Engineering.Base" = full path of the DLL; the other assemblies sit next to it.
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using Microsoft.Win32;

namespace TiaDump.Openness
{
    public static class AssemblyResolver
    {
        private const string Root = @"SOFTWARE\Siemens\Automation\Openness";
        private static string? _folder;

        /// <summary>Folder of the Openness assemblies in use (after <see cref="Install"/>).</summary>
        public static string? Folder => _folder;

        /// <summary>The TIA major version in use, e.g. "V21" (after <see cref="Install"/>).</summary>
        public static string? PortalVersion { get; private set; }

        /// <param name="tia">"V21", "21" or null for the newest installed version.</param>
        public static void Install(string? tia)
        {
            var (version, folder) = Locate(tia);
            _folder = folder;
            PortalVersion = version;
            AppDomain.CurrentDomain.AssemblyResolve += Resolve;
        }

        public static (string version, string folder) Locate(string? tia)
        {
            using var root = Registry.LocalMachine.OpenSubKey(Root)
                ?? throw new ExitException(ExitCodes.AccessDenied, "TIA Portal Openness not found (no registry key)");
            var majors = root.GetSubKeyNames()
                .Select(n => (name: n, major: ParseMajor(n)))
                .Where(x => x.major > 0)
                .OrderByDescending(x => x.major)
                .ToList();
            if (tia != null)
            {
                var want = ParseMajor(tia.TrimStart('V', 'v'));
                majors = majors.Where(x => x.major == want).ToList();
            }
            foreach (var (name, major) in majors)
            {
                using var api = root.OpenSubKey($@"{name}\PublicAPI");
                if (api == null) continue;
                foreach (var asmVersion in api.GetSubKeyNames().OrderByDescending(n => n))
                {
                    using var net48 = api.OpenSubKey($@"{asmVersion}\net48");
                    if (net48?.GetValue("Siemens.Engineering.Base") is string basePath && File.Exists(basePath))
                        return ($"V{major}", Path.GetDirectoryName(basePath)!);
                }
            }
            throw new ExitException(ExitCodes.AccessDenied,
                tia == null ? "TIA Portal Openness not found" : $"TIA Portal Openness {tia} not found");
        }

        private static int ParseMajor(string s)
        {
            var head = s.Split('.')[0];
            return int.TryParse(head, out var v) ? v : 0;
        }

        private static Assembly? Resolve(object sender, ResolveEventArgs args)
        {
            if (_folder == null) return null;
            var name = new AssemblyName(args.Name).Name;
            if (name == null || !name.StartsWith("Siemens.Engineering", StringComparison.Ordinal)) return null;
            var path = Path.Combine(_folder, name + ".dll");
            return File.Exists(path) ? Assembly.LoadFrom(path) : null;
        }
    }
}
