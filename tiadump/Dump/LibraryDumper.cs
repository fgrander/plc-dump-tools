// Library content (docs/tiadump.md). `tiadump library`
// Dumps a global library opened read-only (or retrieved/upgraded in --work); `tiadump project`
// Uses Library() for the project library. Every type with every version and its metadata; the
// content of PLC types through SimaticML (LibraryTypeVersion.ExportAsDocuments failed in S5),
// HMI types and master copies as metadata only (S5: no export for them).
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.Library;
using Siemens.Engineering.Library.MasterCopies;
using Siemens.Engineering.Library.Types;
using TiaDump.Openness;

namespace TiaDump.Dump
{
    public static class LibraryDumper
    {
        public const string HmiMetadataOnly = "HMI type: metadata only";
        public const string ProjectLibraryNoContent = "project library: the linked units hold the content";

        public static int Run(Options o)
        {
            var cleanup = new Cleanup(o.Work!);
            var dump = new Dictionary<string, object?>
            {
                ["dump_version"] = 1,
                ["tool"] = new Dictionary<string, object?> { ["name"] = "tiadump", ["version"] = Program.Version, ["openness"] = AssemblyResolver.PortalVersion },
            };
            DumpContext? ctx = null;
            using (var session = new TiaSession(o))
            {
                if (!session.IsLibrary) throw new ExitException(ExitCodes.Usage, "tiadump library needs a .alNN or .zalNN file");
                session.Open();
                var library = session.Library ?? throw new ExitException(ExitCodes.CannotOpen, "no library opened");
                ctx = new DumpContext(o.Out!, session.MissingPackages.Select(p => (string)p["name"]!));
                dump["source"] = new Dictionary<string, object?>
                {
                    ["file"] = Path.GetFileName(o.File), ["kind"] = "library",
                    ["saved_version"] = $"V{session.SavedMajor}", ["saved_update"] = null,
                };
                dump["tia"] = new Dictionary<string, object?>
                {
                    ["version"] = $"V{session.PortalMajor}",
                    ["upgrade"] = session.Upgraded
                        ? new Dictionary<string, object?> { ["from"] = $"V{session.SavedMajor}", ["to"] = $"V{session.PortalMajor}", ["messages"] = session.Messages.ToList() }
                        : null,
                };
                dump["languages"] = new Dictionary<string, object?> { ["project"] = new List<object?>(), ["editing"] = null, ["reference"] = null };
                dump["multiuser"] = new Dictionary<string, object?> { ["kind"] = "none" };
                dump["missing_packages"] = ctx.MissingProducts.Select(p => (object?)new Dictionary<string, object?> { ["name"] = p, ["objects"] = new List<object?>() }).ToList();
                dump["devices"] = new List<object?>();
                dump["hardware"] = new Dictionary<string, object?> { ["devices"] = new List<object?>(), ["subnets"] = new List<object?>() };
                dump["project_library"] = null;
                string? version = null;
                try { version = library.Version?.ToString(); } catch (EngineeringException) { }
                CountsDumper.Library(ctx, "_library", library.TypeFolder, library.MasterCopyFolder);
                dump["library"] = Library(ctx, library.Name, version, "global", library.TypeFolder, library.MasterCopyFolder, "library", true);
            }
            dump["compiled_units"] = new List<object?>();
            dump["counts"] = ctx!.Counts.ToDictionary(kv => kv.Key, kv => (object?)kv.Value);
            dump["errors"] = ctx.Errors
                .OrderBy(e => (string?)e["where"], StringComparer.Ordinal).ThenBy(e => (string?)e["kind"], StringComparer.Ordinal)
                .Cast<object?>().ToList();
            var work = Path.GetFullPath(o.Work!).TrimEnd(Path.DirectorySeparatorChar);
            dump["cleanup"] = new Dictionary<string, object?>
            {
                ["outside_work"] = cleanup.Run().Where(p => !string.Equals(p.TrimEnd(Path.DirectorySeparatorChar), work, StringComparison.OrdinalIgnoreCase))
                    .Cast<object?>().ToList(),
            };
            Json.WriteFile(Path.Combine(ctx.Out, "dump.json"), dump);
            return ExitCodes.Ok;
        }

        /// <summary>One library: types with all versions, and master copies. <paramref name="root"/>
        /// is the folder below --out for exported content;
        /// <paramref name="content"/> false lists versions without exporting them (project library).</summary>
        public static Dictionary<string, object?> Library(DumpContext ctx, string name, string? version, string kind,
            LibraryTypeFolder? typeFolder, MasterCopyFolder? copyFolder, string root, bool content)
        {
            var types = new List<Dictionary<string, object?>>();
            if (typeFolder != null)
                foreach (var (type, folder) in Types(typeFolder, "")) types.Add(Type(ctx, type, folder, root, name, content));
            var copies = new List<Dictionary<string, object?>>();
            if (copyFolder != null)
                foreach (var (copy, folder) in Copies(copyFolder, "")) copies.Add(Copy(ctx, copy, folder, name));
            return new Dictionary<string, object?>
            {
                ["name"] = name,
                ["version"] = version,
                ["kind"] = kind,
                ["types"] = types.OrderBy(t => (string?)t["folder"], StringComparer.Ordinal).ThenBy(t => (string?)t["name"], StringComparer.Ordinal).Cast<object?>().ToList(),
                ["master_copies"] = copies.OrderBy(c => (string?)c["folder"], StringComparer.Ordinal).ThenBy(c => (string?)c["name"], StringComparer.Ordinal).Cast<object?>().ToList(),
            };
        }

        internal static IEnumerable<(LibraryType Type, string Folder)> Types(LibraryTypeFolder folder, string path)
        {
            foreach (LibraryType type in folder.Types) yield return (type, path);
            foreach (LibraryTypeUserFolder sub in folder.Folders)
                foreach (var x in Types(sub, Walk.Join(path, sub.Name))) yield return x;
        }

        internal static IEnumerable<(MasterCopy Copy, string Folder)> Copies(MasterCopyFolder folder, string path)
        {
            foreach (MasterCopy copy in folder.MasterCopies) yield return (copy, path);
            foreach (MasterCopyUserFolder sub in folder.Folders)
                foreach (var x in Copies(sub, Walk.Join(path, sub.Name))) yield return x;
        }

        /// <summary>Type kind from its Openness class (S5: CodeBlockLibraryType, FaceplateLibraryType,
        /// StyleLibraryType; PLC data types are PlcTypeLibraryType).</summary>
        public static string KindOf(string clrName)
        {
            if (clrName.StartsWith("CodeBlock", StringComparison.Ordinal)) return "plc_block";
            if (clrName.StartsWith("PlcType", StringComparison.Ordinal)) return "plc_type";
            if (clrName.StartsWith("Faceplate", StringComparison.Ordinal)) return "faceplate";
            if (clrName.IndexOf("Hmi", StringComparison.Ordinal) >= 0 || clrName.StartsWith("Style", StringComparison.Ordinal)
                || clrName.StartsWith("Screen", StringComparison.Ordinal)) return "hmi_type";
            return "other";
        }

        private static Dictionary<string, object?> Type(DumpContext ctx, LibraryType type, string folder, string root, string library, bool export)
        {
            var kind = KindOf(type.GetType().Name);
            var versions = new List<object?>();
            // Type names may hold characters a file name cannot (LBCFC_CMP_<, _>, _<=): two types
            // then get the same safe name, so such a folder also carries the type's GUID.
            var dir = Walk.Safe(type.Name);
            if (dir != type.Name) dir += "~" + type.Guid.ToString("N").Substring(0, 8);
            foreach (LibraryTypeVersion v in type.Versions.Cast<LibraryTypeVersion>().OrderBy(v => v.VersionNumber))
            {
                var number = v.VersionNumber.ToString();
                var where = $"{library}/{Walk.Join(folder, type.Name)}@{number}";
                var content = new Dictionary<string, object?> { ["part"] = "none", ["path"] = null, ["error"] = null };
                if (!export) content["error"] = ProjectLibraryNoContent;
                else if (kind == "plc_block" || kind == "plc_type")
                {
                    try
                    {
                        var file = new FileInfo(ctx.PathOf($"{root}/simaticml/{dir}/{Walk.Safe(number)}.xml"));
                        v.Export(file, ExportOptions.WithDefaults);
                        content["part"] = "common";
                        content["path"] = ctx.Rel(file.FullName);
                    }
                    catch (EngineeringException e)
                    {
                        content["error"] = TiaSession.Flatten(e);
                        ctx.Error(where, "export_failed", (string)content["error"]!);
                    }
                }
                else content["error"] = HmiMetadataOnly;
                versions.Add(new Dictionary<string, object?>
                {
                    ["version"] = number,
                    ["status"] = Status(v),
                    ["author"] = NullIfEmpty(Walk.Attr(v, "Author")),
                    ["date"] = Date(v),
                    ["comment"] = Comment(v),
                    ["guid"] = v.Guid.ToString(),
                    ["content"] = content,
                });
            }
            return new Dictionary<string, object?>
            {
                ["name"] = type.Name, ["folder"] = folder, ["kind"] = kind, ["guid"] = type.Guid.ToString(), ["versions"] = versions,
            };
        }

        private static Dictionary<string, object?> Copy(DumpContext ctx, MasterCopy copy, string folder, string library)
        {
            var objects = new List<object?>();
            try
            {
                objects.AddRange(copy.ContentDescriptions
                    .Select(c => (object?)$"{c.ContentName} ({c.ContentType?.Name})")
                    .OrderBy(x => (string?)x, StringComparer.Ordinal));
            }
            catch (Exception e) when (e is EngineeringException || e is TypeLoadException)
            {
                ctx.Error($"{library}/{Walk.Join(folder, copy.Name)}", "export_failed", TiaSession.Flatten(e));  // S5: templates
            }
            return new Dictionary<string, object?> { ["name"] = copy.Name, ["folder"] = folder, ["objects"] = objects, ["path"] = null };
        }

        public static string Status(LibraryTypeVersion v) =>
            v.State == LibraryTypeVersionState.InWork ? "in_work" : "released";

        private static string? Date(LibraryTypeVersion v)
        {
            try { return v.ModifiedDate.ToString("yyyy-MM-dd"); } catch (EngineeringException) { return null; }
        }

        /// <summary>The version comment per language, if Openness exposes one ("Comment" attribute).</summary>
        private static Dictionary<string, object?> Comment(LibraryTypeVersion v)
        {
            var result = new Dictionary<string, object?>();
            object? value;
            try { value = ((IEngineeringObject)v).GetAttribute("Comment"); }
            catch (EngineeringException) { return result; }
            if (value is MultilingualText text)
            {
                foreach (MultilingualTextItem item in text.Items)
                    if (!string.IsNullOrEmpty(item.Text)) result[item.Language.Culture.Name] = item.Text;
            }
            else if (value is string s && s.Length > 0) result["und"] = s;
            return result;
        }

        private static string? NullIfEmpty(string? s) => string.IsNullOrEmpty(s) ? null : s;
    }
}
