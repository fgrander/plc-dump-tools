// Spike commands (`tiadump spike <name> <file> --work <dir> --out <dir>`): research probes
// That record raw Openness observations; their findings went into Dump/. They use TiaSession,
// So the read-only rules and ForbiddenApiTests apply.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.HW.Features;
using Siemens.Engineering.SW;
using Siemens.Engineering.SW.Blocks;
using Siemens.Engineering.SW.Tags;
using Siemens.Engineering.SW.Types;
using TiaDump.Dump;
using TiaDump.Openness;

namespace TiaDump.Spikes
{
    public static class SpikeRunner
    {
        public static int Run(Options o)
        {
            var outDir = Directory.CreateDirectory(o.Out!).FullName;
            var report = new Dictionary<string, object?> { ["spike"] = o.SpikeName, ["file"] = Path.GetFileName(o.File) };
            var watched = WatchedLocations();
            var before = watched.ToDictionary(d => d, Cleanup.Snapshot);
            var cleanup = new Cleanup(o.Work!);
            var clock = Stopwatch.StartNew();
            int code = ExitCodes.Ok;
            using (var session = new TiaSession(o))
            {
                try
                {
                    session.Open();
                    report["open_seconds"] = Math.Round(clock.Elapsed.TotalSeconds, 1);
                    report["saved_major"] = session.SavedMajor;
                    report["portal_major"] = session.PortalMajor;
                    report["upgraded"] = session.Upgraded;
                    switch (o.SpikeName)
                    {
                        case "s1":
                            report["devices"] = DescribeDevices(session.Project!);
                            report["project"] = DescribeProject(session);
                            report["work_files_open"] = ListFiles(o.Work!);
                            break;
                        case "s2": report["exports"] = TryExports(session.Project!, outDir); break;
                        case "s3": report["alarms"] = AlarmSpike.Run(session.Project!, outDir); break;
                        case "s4": report["hmi"] = HmiSpike.Run(session.Project!, outDir); break;
                        case "s5": report["libraries"] = LibrarySpike.Run(session, outDir); break;
                        case "s7conn": report["connections"] = ConnectionSpike.Run(session.Project!); break;
                        default: throw new ExitException(ExitCodes.Usage, $"unknown spike {o.SpikeName}");
                    }
                }
                catch (ExitException e)
                {
                    report["error"] = e.Message;
                    code = e.Code;
                }
                catch (EngineeringException e)
                {
                    // TIA Portal stopped or failed during the spike: keep the report, exit 2
                    report["error"] = "TIA Portal failed: " + TiaSession.Flatten(e);
                    code = ExitCodes.CannotOpen;
                }
                finally
                {
                    report["messages"] = session.Messages.ToList();
                }
            }
            report["total_seconds"] = Math.Round(clock.Elapsed.TotalSeconds, 1);
            if (o.SpikeName == "s1")
            {
                report["work_files_closed"] = ListFiles(o.Work!);
                KeepLogs(o.Work!, Path.Combine(outDir, "logs"));
            }
            report["new_files_outside_work"] = watched
                .SelectMany(d => Cleanup.Snapshot(d).Except(before[d], StringComparer.OrdinalIgnoreCase))
                .OrderBy(x => x, StringComparer.Ordinal).ToList();
            report["cleanup_left"] = cleanup.Run();
            Json.WriteFile(Path.Combine(outDir, $"spike-{o.SpikeName}.json"), report);
            return code;
        }

        private static List<string> WatchedLocations()
        {
            var list = new List<string>
            {
                Path.GetTempPath().TrimEnd(Path.DirectorySeparatorChar),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Siemens"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Siemens"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "Automation"),
            };
            list.AddRange(Cleanup.KnownLocations());
            return list.Distinct(StringComparer.OrdinalIgnoreCase).ToList();
        }

        // ---------------------------------------------------------------- S1: project, logs
        private static Dictionary<string, object?> DescribeProject(TiaSession session)
        {
            var p = session.Project!;
            var installed = session.Portal.GetCurrentProcess().InstalledSoftware
                .Select(s => $"{s.Name} {s.Version}").OrderBy(x => x, StringComparer.Ordinal).ToList();
            var used = p.UsedProducts.Select(u => $"{u.Name} {u.Version}").OrderBy(x => x, StringComparer.Ordinal).ToList();
            return new Dictionary<string, object?>
            {
                ["type"] = p.GetType().FullName,
                ["name"] = p.Name,
                ["version"] = Safe(() => p.Version),
                ["is_modified"] = Safe(() => p.IsModified.ToString()),
                ["size"] = Safe(() => p.Size.ToString()),
                ["last_modified"] = Safe(() => p.LastModified.ToString("o")),
                ["history"] = p.HistoryEntries.Select(h => (object?)$"{h.DateTime:o} {h.Text}").ToList(),
                ["used_products"] = used,
                ["installed_software"] = installed,
                ["missing_packages"] = session.MissingPackages.Select(m => m["name"]).ToList(),
                ["saved_update"] = session.SavedUpdate,
                ["local_sessions"] = Safe(() => session.Portal.LocalSessions.Count.ToString()),
            };
        }

        private static string? Safe(Func<string?> read)
        {
            try { return read(); }
            catch (Exception e) { return "error: " + TiaSession.Flatten(e); }
        }

        private static List<string> ListFiles(string work)
        {
            if (!Directory.Exists(work)) return new List<string>();
            return Directory.EnumerateFiles(work, "*", SearchOption.AllDirectories)
                .Where(f => !f.Contains(Path.DirectorySeparatorChar + "IM" + Path.DirectorySeparatorChar))
                .Select(f => $"{f.Substring(work.Length).TrimStart(Path.DirectorySeparatorChar)} {new FileInfo(f).Length}")
                .OrderBy(x => x, StringComparer.Ordinal).ToList();
        }

        private static void KeepLogs(string work, string target)
        {
            if (!Directory.Exists(work)) return;
            foreach (var f in Directory.EnumerateFiles(work, "*", SearchOption.AllDirectories)
                         .Where(f => f.IndexOf(Path.DirectorySeparatorChar + "Logs" + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) >= 0))
            {
                Directory.CreateDirectory(target);
                File.Copy(f, Path.Combine(target, Path.GetFileName(f)), true);
            }
        }

        // ---------------------------------------------------------------- S1: devices
        private static List<object?> DescribeDevices(Project project)
        {
            var result = new List<object?>();
            foreach (var device in AllDevices(project))
            {
                var items = new List<object?>();
                foreach (var item in Flatten(device.DeviceItems))
                {
                    var software = item.GetService<SoftwareContainer>()?.Software;
                    var entry = new Dictionary<string, object?>
                    {
                        ["name"] = item.Name,
                        ["type_identifier"] = Attr(item, "TypeIdentifier"),
                        ["position"] = Attr(item, "PositionNumber"),
                        ["software"] = software?.GetType().FullName,
                    };
                    if (software is PlcSoftware plc)
                    {
                        entry["blocks"] = AllBlocks(plc.BlockGroup).Count;
                        entry["types"] = AllTypes(plc.TypeGroup).Count;
                        entry["tag_tables"] = AllTagTables(plc.TagTableGroup).Count;
                        entry["languages"] = AllBlocks(plc.BlockGroup)
                            .GroupBy(b => b.ProgrammingLanguage.ToString())
                            .ToDictionary(g => g.Key, g => (object?)g.Count());
                    }
                    if (software != null || item.DeviceItems.Count == 0 || Attr(item, "TypeIdentifier") != null)
                        items.Add(entry);
                }
                result.Add(new Dictionary<string, object?>
                {
                    ["name"] = device.Name,
                    ["type_identifier"] = Attr(device, "TypeIdentifier"),
                    ["items"] = items,
                });
            }
            return result;
        }

        // ---------------------------------------------------------------- S2: export routes
        private static List<object?> TryExports(Project project, string outDir)
        {
            var result = new List<object?>();
            foreach (var device in AllDevices(project))
            foreach (var item in Flatten(device.DeviceItems))
            {
                if (!(item.GetService<SoftwareContainer>()?.Software is PlcSoftware plc)) continue;
                var plcName = Safe(item.Name);
                result.Add(new Dictionary<string, object?>
                {
                    ["plc"] = plcName, ["kind"] = "plc_software",
                    ["type_identifier"] = Attr(item, "TypeIdentifier"),
                    ["properties"] = DescribeProperties(plc),
                });
                foreach (var block in AllBlocks(plc.BlockGroup))
                {
                    var entry = TryUnit(block.Name, "block", block.ProgrammingLanguage.ToString(),
                        block.IsKnowHowProtected, block.IsConsistent, plcName, outDir,
                        dir => block.ExportAsDocuments(dir, block.Name),
                        file => block.Export(file, ExportOptions.WithDefaults), block);
                    entry["block_type"] = block.GetType().Name;
                    entry["number"] = Attr(block, "Number");
                    entry["folder"] = FolderOf(block.Parent);
                    entry["is_plc_document"] = (object)block is PlcDocument;
                    result.Add(entry);
                }
                foreach (var type in AllTypes(plc.TypeGroup))
                {
                    var entry = TryUnit(type.Name, "type", "UDT", type.IsKnowHowProtected, type.IsConsistent, plcName, outDir,
                        dir => type.ExportAsDocuments(dir, type.Name),
                        file => type.Export(file, ExportOptions.WithDefaults), type);
                    entry["folder"] = FolderOf(type.Parent);
                    result.Add(entry);
                }
                foreach (var table in AllTagTables(plc.TagTableGroup))
                {
                    var entry = new Dictionary<string, object?> { ["plc"] = plcName, ["name"] = table.Name, ["kind"] = "tag_table",
                        ["is_plc_document"] = (object)table is PlcDocument, ["tags"] = table.Tags.Count,
                        ["constants"] = table.UserConstants.Count, ["folder"] = FolderOf(table.Parent) };
                    if ((object)table is PlcDocument doc)
                        entry["sd"] = Attempt(() => Describe(doc.ExportAsDocuments(SdDir(outDir, plcName), table.Name)));
                    entry["simaticml"] = Timed(() =>
                    {
                        var file = new FileInfo(Path.Combine(outDir, "simaticml", plcName, "tags", Safe(table.Name) + ".xml"));
                        Directory.CreateDirectory(file.DirectoryName!);
                        table.Export(file, ExportOptions.WithDefaults);
                        return "ok";
                    });
                    result.Add(entry);
                }
                foreach (var doc in DocumentsReachableFrom(plc))
                {
                    result.Add(new Dictionary<string, object?>
                    {
                        ["plc"] = plcName, ["kind"] = "plc_document", ["name"] = doc.Name, ["type"] = doc.GetType().FullName,
                        ["sd"] = Attempt(() => Describe(doc.ExportAsDocuments(SdDir(outDir, plcName, "documents"), doc.Name))),
                    });
                }
            }
            return result;
        }

        private static Dictionary<string, object?> TryUnit(string name, string kind, string language, bool protectedUnit,
            bool consistent, string plcName, string outDir, Func<DirectoryInfo, DocumentExportResult> sd, Action<FileInfo> xml,
            IEngineeringServiceProvider? unit = null)
        {
            var entry = new Dictionary<string, object?>
            {
                ["plc"] = plcName, ["name"] = name, ["kind"] = kind, ["language"] = language,
                ["protected"] = protectedUnit, ["consistent"] = consistent,
            };
            entry["sd"] = Timed(() => Describe(sd(SdDir(outDir, plcName))));
            // units SD refuses (not protected) are compiled in the working copy first
            if (unit != null && !protectedUnit && !((string)entry["sd"]!).StartsWith("Success", StringComparison.Ordinal))
                entry["compile"] = Timed(() =>
                {
                    var c = CopyCompiler.CompileUnit(unit);
                    return (c.Ok ? "ok" : "failed") + (c.Messages.Count > 0 ? ": " + string.Join(" | ", c.Messages.Take(5)) : "");
                });
            entry["simaticml"] = Timed(() =>
            {
                var file = new FileInfo(Path.Combine(outDir, "simaticml", plcName, kind + "s", Safe(name) + ".xml"));
                Directory.CreateDirectory(file.DirectoryName!);
                xml(file);
                return "ok";
            });
            return entry;
        }

        private static DirectoryInfo SdDir(string outDir, string plcName, string sub = "")
        {
            var dir = new DirectoryInfo(Path.Combine(outDir, "sd", plcName, sub));
            Directory.CreateDirectory(dir.FullName);
            return dir;
        }

        private static string Describe(DocumentExportResult r)
        {
            var messages = r.Messages.Select(m => m.Message).ToList();
            var docs = new List<string>();
            foreach (var d in (System.Collections.IEnumerable)r.ExportedDocuments) docs.Add(d?.ToString() ?? "");
            return $"{r.State}" + (docs.Count > 0 ? " docs=[" + string.Join(", ", docs) + "]" : "")
                + (messages.Count > 0 ? " msgs=[" + string.Join(" | ", messages) + "]" : "");
        }

        private static string Timed(Func<string> action)
        {
            var clock = Stopwatch.StartNew();
            var r = Attempt(action);
            return $"{r} ({clock.ElapsedMilliseconds} ms)";
        }

        private static string FolderOf(IEngineeringObject? parent)
        {
            var parts = new List<string>();
            for (var p = parent; p != null; p = p.Parent)
            {
                if (p is PlcSoftware || p is Device || p is Project) break;
                var name = Attr(p, "Name") as string;
                if (!string.IsNullOrEmpty(name)) parts.Insert(0, name!);
            }
            return string.Join("/", parts);
        }

        // Which PlcSoftware members hold PLC documents (not visible in the API docs).
        private static List<object?> DescribeProperties(PlcSoftware plc) =>
            plc.GetType().GetProperties()
                .OrderBy(p => p.Name, StringComparer.Ordinal)
                .Select(p => (object?)$"{p.Name}: {p.PropertyType.FullName}")
                .ToList();

        private static IEnumerable<PlcDocument> DocumentsReachableFrom(PlcSoftware plc)
        {
            foreach (var p in plc.GetType().GetProperties())
            {
                if (p.GetIndexParameters().Length > 0) continue;
                if (!(typeof(PlcDocumentComposition).IsAssignableFrom(p.PropertyType) || p.PropertyType.Name.Contains("Document"))) continue;
                object? value;
                try { value = p.GetValue(plc); } catch (Exception) { continue; }
                if (value is System.Collections.IEnumerable items)
                    foreach (var x in items) if (x is PlcDocument d) yield return d;
            }
        }

        private static string Attempt(Func<string> action)
        {
            try { return action(); }
            catch (Exception e) { return "error: " + TiaSession.Flatten(e); }
        }

        // ---------------------------------------------------------------- object model walks
        public static List<Device> AllDevices(Project project)
        {
            var list = new List<Device>(project.Devices);
            void Walk(DeviceUserGroupComposition groups)
            {
                foreach (DeviceUserGroup g in groups) { list.AddRange(g.Devices); Walk(g.Groups); }
            }
            Walk(project.DeviceGroups);
            list.AddRange(project.UngroupedDevicesGroup.Devices);
            return list.Distinct().ToList();
        }

        public static IEnumerable<DeviceItem> Flatten(DeviceItemComposition items)
        {
            foreach (DeviceItem item in items)
            {
                yield return item;
                foreach (var child in Flatten(item.DeviceItems)) yield return child;
            }
        }

        public static List<PlcBlock> AllBlocks(PlcBlockGroup group)
        {
            var list = new List<PlcBlock>(group.Blocks);
            foreach (PlcBlockUserGroup g in GroupsOf(group)) list.AddRange(AllBlocks(g));
            return list;
        }

        private static IEnumerable<PlcBlockGroup> GroupsOf(PlcBlockGroup group) => group switch
        {
            PlcBlockSystemGroup s => s.Groups.Cast<PlcBlockGroup>(),
            PlcBlockUserGroup u => u.Groups.Cast<PlcBlockGroup>(),
            _ => Enumerable.Empty<PlcBlockGroup>(),
        };

        public static List<PlcType> AllTypes(PlcTypeGroup group)
        {
            var list = new List<PlcType>(group.Types);
            var groups = group switch
            {
                PlcTypeSystemGroup s => s.Groups.Cast<PlcTypeGroup>(),
                PlcTypeUserGroup u => u.Groups.Cast<PlcTypeGroup>(),
                _ => Enumerable.Empty<PlcTypeGroup>(),
            };
            foreach (var g in groups) list.AddRange(AllTypes(g));
            return list;
        }

        public static List<PlcTagTable> AllTagTables(PlcTagTableGroup group)
        {
            var list = new List<PlcTagTable>(group.TagTables);
            var groups = group switch
            {
                PlcTagTableSystemGroup s => s.Groups.Cast<PlcTagTableGroup>(),
                PlcTagTableUserGroup u => u.Groups.Cast<PlcTagTableGroup>(),
                _ => Enumerable.Empty<PlcTagTableGroup>(),
            };
            foreach (var g in groups) list.AddRange(AllTagTables(g));
            return list;
        }

        public static object? Attr(IEngineeringObject obj, string name)
        {
            try { return obj.GetAttribute(name)?.ToString(); }
            catch (Exception) { return null; }
        }

        public static string Safe(string name) =>
            string.Concat(name.Select(c => Path.GetInvalidFileNameChars().Contains(c) ? '_' : c));
    }
}
