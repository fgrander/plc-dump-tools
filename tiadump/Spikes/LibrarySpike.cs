// Libraries (`tiadump spike s5 <project> --work <dir> --out <dir>`).
// Records the project library of the opened working copy, the TIA system global libraries
// (read-only, opened by GlobalLibraryInfo; no .alNN/.zalNN sample exists), library type versions
// with their export formats and export results, master copies, and the library links of PLC units
// (LibraryTypeInstanceInfo). Research probe like SpikeRunner; its findings went into LibraryDumper.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.HW.Features;
using Siemens.Engineering.Library;
using Siemens.Engineering.Library.MasterCopies;
using Siemens.Engineering.Library.Types;
using Siemens.Engineering.SW;
using TiaDump.Openness;

namespace TiaDump.Spikes
{
    public static class LibrarySpike
    {
        private const int ExportsPerLibrary = 60;

        private static string? _progress;
        private static bool _variantsDone;

        // One line per risky call, flushed before the call: if TIA dies, the last line names it.
        private static void Note(string what)
        {
            if (_progress != null) File.AppendAllText(_progress, $"{DateTime.Now:HH:mm:ss.fff} {what}\n");
        }

        public static Dictionary<string, object?> Run(TiaSession session, string outDir)
        {
            var project = session.Project!;
            _progress = Path.Combine(outDir, "progress.log");
            Note("links");
            var result = new Dictionary<string, object?> { ["links"] = Links(project) };
            var infos = session.Portal.GlobalLibraries.GetGlobalLibraryInfos().ToList();
            result["global_library_infos"] = infos
                .Select(i => (object?)$"{i.LibraryType} {i.Name} open={i.IsOpen} ro={i.IsReadOnly} {i.Path}").ToList();
            var system = new List<object?>();
            foreach (var info in infos.Where(i => i.LibraryType == GlobalLibraryType.System))
            {
                var entry = new Dictionary<string, object?> { ["name"] = info.Name, ["path"] = info.Path?.ToString() };
                var clock = Stopwatch.StartNew();
                try
                {
                    Note($"open system library {info.Name}");
                    var library = session.Portal.GlobalLibraries.Open(info);
                    entry["open_ms"] = clock.ElapsedMilliseconds;
                    entry["clr"] = library.GetType().FullName;
                    entry["version"] = Read(() => library.Version?.ToString());
                    entry["read_only"] = Read(() => library.IsReadOnly.ToString());
                    entry["content"] = DescribeLibrary(library.TypeFolder, library.MasterCopyFolder,
                        Path.Combine(outDir, "lib", SpikeRunner.Safe(info.Name)));
                }
                catch (Exception e)
                {
                    entry["error"] = TiaSession.Flatten(e);
                }
                system.Add(entry);
            }
            result["system_libraries"] = system;
            Note("project library");
            result["project_library"] = DescribeLibrary(project.ProjectLibrary.TypeFolder, project.ProjectLibrary.MasterCopyFolder,
                Path.Combine(outDir, "lib", "_project"));
            Note("done");
            return result;
        }

        // ---------------------------------------------------------------- library content
        private static Dictionary<string, object?> DescribeLibrary(LibraryTypeFolder? types, MasterCopyFolder? copies, string dir)
        {
            var budget = new[] { ExportsPerLibrary };
            var result = new Dictionary<string, object?>();
            var typeList = new List<object?>();
            result["types"] = typeList;
            if (types == null) result["type_folder"] = "null";
            else result["types_error"] = Read(() => { WalkTypes(types, "", typeList, dir, budget); return null; });
            var copyList = new List<object?>();
            result["master_copies"] = copyList;
            if (copies == null) result["master_copy_folder"] = "null";
            else result["master_copies_error"] = Read(() => { WalkCopies(copies, "", copyList); return null; });
            return result;
        }

        private static void WalkTypes(LibraryTypeFolder folder, string path, List<object?> into, string dir, int[] budget)
        {
            foreach (LibraryType type in folder.Types) into.Add(DescribeType(type, path, dir, budget));
            foreach (LibraryTypeUserFolder sub in folder.Folders)
                WalkTypes(sub, path.Length == 0 ? sub.Name : path + "/" + sub.Name, into, dir, budget);
        }

        private static Dictionary<string, object?> DescribeType(LibraryType type, string folder, string dir, int[] budget)
        {
            var formats = new List<string>();
            var formatsRead = Read(() => { formats.AddRange(type.GetSupportedExportFormats()); return string.Join(",", formats); });
            var entry = new Dictionary<string, object?>
            {
                ["name"] = type.Name,
                ["folder"] = folder,
                ["clr"] = type.GetType().Name,
                ["guid"] = type.Guid.ToString(),
                ["status"] = Read(() => type.Status.ToString()),
                ["namespace"] = Read(() => type.Namespace),
                ["author"] = SpikeRunner.Attr(type, "Author"),
                ["do_not_use"] = Read(() => type.DoNotUse.ToString()),
                ["formats"] = formatsRead,
            };
            var versions = new List<object?>();
            foreach (LibraryTypeVersion v in type.Versions)
            {
                var ve = new Dictionary<string, object?>
                {
                    ["version"] = v.VersionNumber.ToString(),
                    ["state"] = v.State.ToString(),
                    ["default"] = v.IsDefault,
                    ["author"] = SpikeRunner.Attr(v, "Author"),
                    ["modified"] = Read(() => v.ModifiedDate.ToString("o")),
                    ["guid"] = v.Guid.ToString(),
                    ["original_library"] = Read(() => v.OriginalLibrary),
                    ["dependencies"] = Read(() => string.Join(", ",
                        v.Dependencies.Select(d => $"{d.TypeObject.Name}@{d.VersionNumber}"))),
                };
                if (budget[0] > 0)
                {
                    budget[0]--;
                    var target = Directory.CreateDirectory(Path.Combine(dir, SpikeRunner.Safe(type.Name)));
                    var baseName = $"{SpikeRunner.Safe(type.Name)}@{v.VersionNumber}";
                    var label = $"{type.Name}@{v.VersionNumber}";
                    Note($"{label} simaticml");
                    ve["simaticml"] = Timed(() =>
                    {
                        v.Export(new FileInfo(Path.Combine(target.FullName, baseName + ".xml")), ExportOptions.WithDefaults);
                        return "ok";
                    });
                    foreach (var format in formats)
                    {
                        Note($"{label} ExportAsDocuments {format}");
                        ve["export_" + format] = Timed(() => Describe(v.ExportAsDocuments(target, baseName, format,
                            LibraryExportOptions.WithLibraryVersionInfoFile)));
                    }
                    // "directoryInfo cannot be a relative path" on the first run (absolute path):
                    // find out what TIA objects to - the name, an existing folder, or the separator.
                    // TIA died during these calls once (22:51); only the first type gets them.
                    if (formats.Contains("SimaticSD") && !_variantsDone)
                    {
                        _variantsDone = true;
                        var plainName = SpikeRunner.Safe(type.Name);
                        if (Variant("a")) { Note($"{label} variant plain_name");
                        ve["sd_variant_plain_name"] = Timed(() => Describe(v.ExportAsDocuments(
                            Directory.CreateDirectory(Path.Combine(target.FullName, "a")), plainName, "SimaticSD", LibraryExportOptions.None))); }
                        if (Variant("b")) { Note($"{label} variant new_dir");
                        ve["sd_variant_new_dir"] = Timed(() => Describe(v.ExportAsDocuments(
                            new DirectoryInfo(Path.Combine(target.FullName, "b-not-created")), plainName, "SimaticSD", LibraryExportOptions.None))); }
                        if (Variant("c")) { Note($"{label} variant trailing_sep");
                        ve["sd_variant_trailing_sep"] = Timed(() => Describe(v.ExportAsDocuments(
                            Directory.CreateDirectory(Path.Combine(target.FullName, "c") + Path.DirectorySeparatorChar), plainName, "SimaticSD", LibraryExportOptions.None))); }
                        Note($"{label} variants returned");
                    }
                }
                versions.Add(ve);
            }
            entry["versions"] = versions;
            return entry;
        }

        private static void WalkCopies(MasterCopyFolder folder, string path, List<object?> into)
        {
            foreach (MasterCopy copy in folder.MasterCopies)
            {
                into.Add(new Dictionary<string, object?>
                {
                    ["name"] = copy.Name,
                    ["folder"] = path,
                    ["author"] = SpikeRunner.Attr(copy, "Author"),
                    ["created"] = Read(() => copy.CreationDate.ToString("o")),
                    ["contents"] = Read(() => string.Join(", ",
                        copy.ContentDescriptions.Select(c => $"{c.ContentType?.Name}:{c.ContentName}"))),
                });
            }
            foreach (MasterCopyUserFolder sub in folder.Folders)
                WalkCopies(sub, path.Length == 0 ? sub.Name : path + "/" + sub.Name, into);
        }

        // ---------------------------------------------------------------- links (R13)
        private static Dictionary<string, object?> Links(Project project)
        {
            var linked = new List<object?>();
            var unlinked = 0;
            foreach (var device in SpikeRunner.AllDevices(project))
            foreach (var item in SpikeRunner.Flatten(device.DeviceItems))
            {
                if (!(item.GetService<SoftwareContainer>()?.Software is PlcSoftware plc)) continue;
                var units = SpikeRunner.AllBlocks(plc.BlockGroup).Select(b => ((IEngineeringServiceProvider)b, b.Name, "block"))
                    .Concat(SpikeRunner.AllTypes(plc.TypeGroup).Select(t => ((IEngineeringServiceProvider)t, t.Name, "type")));
                foreach (var (unit, name, kind) in units)
                {
                    LibraryTypeInstanceInfo? info;
                    try { info = unit.GetService<LibraryTypeInstanceInfo>(); }
                    catch (Exception e) { linked.Add($"{item.Name}/{name}: error {TiaSession.Flatten(e)}"); continue; }
                    if (info == null) { unlinked++; continue; }
                    var v = info.LibraryTypeVersion;
                    linked.Add(new Dictionary<string, object?>
                    {
                        ["plc"] = item.Name, ["unit"] = name, ["kind"] = kind,
                        ["type"] = Read(() => v.TypeObject.Name),
                        ["type_guid"] = Read(() => v.TypeObject.Guid.ToString()),
                        ["version"] = Read(() => v.VersionNumber.ToString()),
                        ["state"] = Read(() => v.State.ToString()),
                        ["default"] = Read(() => v.IsDefault.ToString()),
                        ["original_library"] = Read(() => v.OriginalLibrary),
                        ["version_parent"] = Read(() => v.TypeObject.Parent?.GetType().Name),
                    });
                }
            }
            return new Dictionary<string, object?> { ["linked"] = linked, ["unlinked_units"] = unlinked };
        }

        // ---------------------------------------------------------------- helpers
        private static string Describe(ExportTransferResult r)
        {
            var docs = r.ExportedDocuments.Select(f => f.Name).ToList();
            var messages = new List<string>();
            foreach (var m in (IEnumerable)r.Messages)
                messages.Add(m?.GetType().GetProperty("Message")?.GetValue(m)?.ToString() ?? m?.ToString() ?? "");
            return $"{r.TransferResultState}" + (docs.Count > 0 ? " docs=[" + string.Join(", ", docs) + "]" : "")
                + (messages.Count > 0 ? " msgs=[" + string.Join(" | ", messages) + "]" : "");
        }

        private static string? Read(Func<string?> read)
        {
            try { return read(); }
            catch (Exception e) { return "error: " + TiaSession.Flatten(e); }
        }

        private static string Timed(Func<string> action)
        {
            var clock = Stopwatch.StartNew();
            string r;
            try { r = action(); }
            catch (Exception e) { r = "error: " + TiaSession.Flatten(e); }
            var line = $"{r} ({clock.ElapsedMilliseconds} ms)";
            Note("  -> " + line.Replace('\n', ' ').Replace('\r', ' '));
            return line;
        }

        // Spike only: TIADUMP_S5_VARIANT=a|b|c runs just that ExportAsDocuments variant (TIA died
        // shortly after the three ran together); unset runs all three.
        private static bool Variant(string name)
        {
            var only = Environment.GetEnvironmentVariable("TIADUMP_S5_VARIANT");
            return string.IsNullOrEmpty(only) || only == name;
        }
    }
}
