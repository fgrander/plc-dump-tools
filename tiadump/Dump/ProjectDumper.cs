// `tiadump project <copy> --work <dir> --out <dir>` (docs/tiadump.md).
// Opens the copy (upgrading it when older), dumps every device, hardware, alarms, safety
// Signatures and counts into dump.json plus exported files, then cleans up --work.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.HW.Features;
using Siemens.Engineering.Hmi;
using Siemens.Engineering.HmiUnified;
using Siemens.Engineering.SW;
using TiaDump.Openness;

namespace TiaDump.Dump
{
    public static class ProjectDumper
    {
        public static int Run(Options o)
        {
            var probe = Probe.Inspect(o.File);
            if ((string?)probe["kind"] == "local_session")
                throw new ExitException(ExitCodes.Usage, "multiuser local session - export the server project");
            var cleanup = new Cleanup(o.Work!);
            var dump = new Dictionary<string, object?>
            {
                ["dump_version"] = 1,
                ["tool"] = new Dictionary<string, object?> { ["name"] = "tiadump", ["version"] = Program.Version, ["openness"] = AssemblyResolver.PortalVersion },
            };
            DumpContext? ctx = null;
            var code = ExitCodes.Ok;
            using (var session = new TiaSession(o))
            {
                session.Open();
                var project = session.Project ?? throw new ExitException(ExitCodes.CannotOpen, "no project opened");
                ctx = new DumpContext(o.Out!, session.MissingPackages.Select(p => (string)p["name"]!));
                dump["source"] = new Dictionary<string, object?>
                {
                    ["file"] = Path.GetFileName(o.File), ["kind"] = "project",
                    ["saved_version"] = $"V{session.SavedMajor}", ["saved_update"] = session.SavedUpdate ?? (string?)probe["saved_update"],
                };
                dump["tia"] = new Dictionary<string, object?>
                {
                    ["version"] = $"V{session.PortalMajor}",
                    ["upgrade"] = session.Upgraded
                        ? new Dictionary<string, object?> { ["from"] = $"V{session.SavedMajor}", ["to"] = $"V{session.PortalMajor}", ["messages"] = session.Messages.ToList() }
                        : null,
                };
                dump["languages"] = Languages(project);
                dump["multiuser"] = new Dictionary<string, object?> { ["kind"] = session.MultiuserKind };
                dump["used_products"] = session.UsedProducts
                    .OrderBy(u => u.Name, StringComparer.Ordinal).ThenBy(u => u.Version, StringComparer.Ordinal)
                    .Select(u => (object?)new Dictionary<string, object?> { ["name"] = u.Name, ["version"] = u.Version })
                    .ToList();
                dump["missing_packages"] = ctx.MissingProducts.Select(p => (object?)new Dictionary<string, object?> { ["name"] = p, ["objects"] = new List<object?>() }).ToList();
                CountsDumper.Project(ctx, project);
                dump["devices"] = Devices(ctx, project);
                dump["hardware"] = HardwareDumper.Dump(ctx, project);
                dump["project_library"] = ProjectLibrary(ctx, project);
                dump["library"] = null;
                if (ctx.LicenseMissing) code = ExitCodes.AccessDenied;
            }
            dump["compiled_units"] = ctx!.CompiledUnits.OrderBy(x => x, StringComparer.Ordinal).Cast<object?>().ToList();
            dump["counts"] = ctx.Counts.ToDictionary(kv => kv.Key, kv => (object?)kv.Value);
            dump["errors"] = ctx.Errors
                .OrderBy(e => (string?)e["where"], StringComparer.Ordinal).ThenBy(e => (string?)e["kind"], StringComparer.Ordinal)
                .Cast<object?>().ToList();
            var work = Path.GetFullPath(o.Work!).TrimEnd(Path.DirectorySeparatorChar);
            dump["cleanup"] = new Dictionary<string, object?>
            {
                // --work itself may be held by TIA's child processes; the caller deletes it afterwards
                ["outside_work"] = cleanup.Run().Where(p => !string.Equals(p.TrimEnd(Path.DirectorySeparatorChar), work, StringComparison.OrdinalIgnoreCase))
                    .Cast<object?>().ToList(),
            };
            Json.WriteFile(Path.Combine(ctx.Out, "dump.json"), dump);
            if (code == ExitCodes.AccessDenied) Console.Error.WriteLine("tiadump: STEP 7 Professional license missing: no program unit exported");
            return code;
        }

        private static List<object?> Devices(DumpContext ctx, Project project)
        {
            var devices = new List<object?>();
            foreach (var device in Walk.Devices(project))
            foreach (var item in Walk.Items(device.DeviceItems))
            {
                object? software;
                try { software = item.GetService<SoftwareContainer>()?.Software; }
                catch (EngineeringException e) { ctx.Error(item.Name, "export_failed", TiaSession.Flatten(e)); continue; }
                switch (software)
                {
                    case null: break;
                    case PlcSoftware plc:
                        var d = PlcDumper.Dump(ctx, item, plc);
                        if (!d.ContainsKey("missing_package"))
                        {
                            d["alarms"] = AlarmDumper.Dump(ctx, plc);
                            d["safety"] = AlarmDumper.Safety(ctx, item, plc);
                            d["library_links"] = LinkDumper.Plc(ctx, item.Name, plc);
                            ConnectionDumper.Plc(d, device, item);
                        }
                        devices.Add(d);
                        break;
                    case HmiTarget comfort: devices.Add(HmiDumper.Comfort(ctx, item, comfort)); break;
                    case HmiSoftware unified: devices.Add(HmiDumper.Unified(ctx, item, unified)); break;
                    default: devices.Add(HmiDumper.Other(ctx, item, software)); break;
                }
            }
            return devices.OrderBy(d => (string?)((Dictionary<string, object?>)d!)["name"], StringComparer.Ordinal).ToList();
        }

        private static Dictionary<string, object?>? ProjectLibrary(DumpContext ctx, Project project)
        {
            try
            {
                var lib = project.ProjectLibrary;
                return LibraryDumper.Library(ctx, project.Name, null, "project", lib.TypeFolder, lib.MasterCopyFolder,
                    "project_library", false);
            }
            catch (EngineeringException e)
            {
                ctx.Error("_project_library", "export_failed", TiaSession.Flatten(e));
                return null;
            }
        }

        private static Dictionary<string, object?> Languages(Project project)
        {
            try
            {
                var s = project.LanguageSettings;
                return new Dictionary<string, object?>
                {
                    ["project"] = s.ActiveLanguages.Select(l => (object?)l.Culture.Name).OrderBy(x => (string?)x, StringComparer.Ordinal).ToList(),
                    ["editing"] = s.EditingLanguage?.Culture.Name,
                    ["reference"] = s.ReferenceLanguage?.Culture.Name,
                };
            }
            catch (EngineeringException)
            {
                return new Dictionary<string, object?> { ["project"] = new List<object?>(), ["editing"] = null, ["reference"] = null };
            }
        }
    }
}
