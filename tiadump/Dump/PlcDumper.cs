// One PLC: program units (route per unit) and tag tables.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.SW;
using Siemens.Engineering.SW.Blocks;
using Siemens.Engineering.SW.Types;
using TiaDump.Openness;

namespace TiaDump.Dump
{
    public static class PlcDumper
    {
        // only the base product blocks the program; options (Safety, Web App) do not
        internal static readonly string[] Products = { "STEP 7 Professional", "STEP 7 Basic" };

        public static Dictionary<string, object?> Dump(DumpContext ctx, DeviceItem item, PlcSoftware plc)
        {
            var name = plc.Name;
            var (orderNo, firmware) = SplitTypeIdentifier(Walk.Attr(item, "TypeIdentifier"));
            var device = new Dictionary<string, object?>
            {
                ["name"] = name,
                ["kind"] = "plc",
                ["family"] = Family(orderNo),
                ["order_no"] = orderNo,
                ["firmware"] = firmware,
                ["library_links"] = new List<object?>(),  // (LinkDumper)
                ["connected_hmis"] = new List<object?>(),
            };
            var missing = ctx.MissingFor(Products);
            if (missing != null)
            {
                device["missing_package"] = missing;
                device["units"] = new List<object?>();
                device["tag_tables"] = new List<object?>();
                ctx.Error(name, "missing_package", $"{missing} is not installed; program not read");
                return device;
            }

            var units = new List<object?>();
            var blocks = Walk.Blocks(plc.BlockGroup);
            var types = Walk.Types(plc.TypeGroup);
            foreach (var (block, folder) in blocks) units.Add(Unit(ctx, name, block, folder, KindOf(block), block.Number, block.ProgrammingLanguage.ToString(),
                block.IsKnowHowProtected, block.IsConsistent, Attributes(block),
                dir => block.ExportAsDocuments(dir, block.Name), file => block.Export(file, ExportOptions.WithDefaults)));
            foreach (var (type, folder) in types) units.Add(Unit(ctx, name, type, folder, "UDT", null, "UDT",
                type.IsKnowHowProtected, type.IsConsistent, new Dictionary<string, object?>(),
                dir => type.ExportAsDocuments(dir, type.Name), file => type.Export(file, ExportOptions.WithDefaults)));
            device["units"] = units;
            device["tag_tables"] = TagTables(ctx, name, plc);
            return device;
        }

        private static Dictionary<string, object?> Unit(DumpContext ctx, string plc, IEngineeringServiceProvider unit, string folder,
            string kind, int? number, string language, bool isProtected, bool consistent, Dictionary<string, object?> attributes,
            Func<DirectoryInfo, DocumentExportResult> sd, Action<FileInfo> simaticml)
        {
            var unitName = Walk.Attr((IEngineeringObject)unit, "Name") ?? "?";
            var where = $"{plc}/{unitName}";
            var entry = new Dictionary<string, object?>
            {
                ["name"] = unitName, ["kind"] = kind, ["number"] = number, ["language"] = language,
                ["folder"] = folder, ["protected"] = isProtected,
                ["safety"] = language.StartsWith("F_", StringComparison.Ordinal),
                ["consistent"] = consistent, ["attributes"] = attributes,
                ["part"] = "none", ["files"] = new List<object?>(), ["error"] = null,
            };
            if (ctx.LicenseMissing)
            {
                entry["error"] = "STEP 7 Professional license missing";
                return entry;
            }

            // 1. SIMATIC SD (also for inconsistent units)
            string sdError;
            try
            {
                var r = sd(ctx.DirOf($"sd/{Walk.Safe(plc)}/{SafeFolder(folder)}"));
                if (r.State != DocumentResultState.Failure)
                {
                    var files = new List<object?>();
                    foreach (var d in (IEnumerable)r.ExportedDocuments)
                    {
                        var path = d?.ToString();
                        if (!string.IsNullOrEmpty(path) && File.Exists(path)) files.Add(ctx.Rel(Path.GetFullPath(path)));
                    }
                    files.Sort((a, b) => string.CompareOrdinal((string?)a, (string?)b));
                    entry["part"] = "sd";
                    entry["files"] = files;
                    return entry;
                }
                sdError = string.Join(" | ", r.Messages.Select(m => m.Message));
            }
            catch (EngineeringException e) { sdError = TiaSession.Flatten(e); }
            catch (Exception e) when (!(e is ExitException)) { sdError = e.GetType().Name + ": " + e.Message; }
            entry["sd_error"] = sdError;  // why SD was not used

            if (IsLicense(sdError))
            {
                ctx.LicenseMissing = true;
                ctx.Error(plc, "license", "STEP 7 Professional license missing: no program unit can be exported");
                entry["error"] = "STEP 7 Professional license missing";
                return entry;
            }
            if (isProtected)  // decided by the flag, not the text
            {
                entry["error"] = "know-how protected";
                ctx.Error(where, "protected", "know-how protected - logic not exported");
                return entry;
            }

            // 2. compile in the working copy, then SimaticML
            if (!consistent)
            {
                var c = CopyCompiler.CompileUnit(unit);
                ctx.CompiledUnits.Add(where);
                if (!c.Ok)
                {
                    entry["error"] = "compile failed: " + string.Join(" | ", c.Messages);
                    ctx.Error(where, "compile_failed", (string)entry["error"]!);
                    return entry;
                }
            }
            try
            {
                var file = new FileInfo(ctx.PathOf($"simaticml/{Walk.Safe(plc)}/units/{SafeFolder(folder)}/{Walk.Safe(unitName)}.xml"));
                simaticml(file);
                entry["part"] = "common";
                entry["files"] = new List<object?> { ctx.Rel(file.FullName) };
            }
            catch (EngineeringException e)
            {
                var text = TiaSession.Flatten(e);
                var unsupported = text.IndexOf("not supported during import and export", StringComparison.OrdinalIgnoreCase) >= 0;
                entry["error"] = text;
                ctx.Error(where, unsupported ? "unsupported" : "export_failed", text);
            }
            return entry;
        }

        private static List<object?> TagTables(DumpContext ctx, string plc, PlcSoftware software)
        {
            var list = new List<object?>();
            foreach (var (table, folder) in Walk.TagTables(software.TagTableGroup))
            {
                var file = new FileInfo(ctx.PathOf($"simaticml/{Walk.Safe(plc)}/tags/{SafeFolder(folder)}/{Walk.Safe(table.Name)}.xml"));
                try
                {
                    table.Export(file, ExportOptions.WithDefaults);  // works without license
                    list.Add(new Dictionary<string, object?> { ["name"] = table.Name, ["folder"] = folder, ["file"] = ctx.Rel(file.FullName) });
                }
                catch (EngineeringException e)
                {
                    ctx.Error($"{plc}/{table.Name}", "export_failed", TiaSession.Flatten(e));
                }
            }
            return list;
        }

        private static Dictionary<string, object?> Attributes(PlcBlock block) => new Dictionary<string, object?>
        {
            ["family"] = block.HeaderFamily ?? "",
            ["version"] = block.HeaderVersion?.ToString() ?? "",
            ["author"] = block.HeaderAuthor ?? "",  // personal data: callers may mask it
        };

        public static string KindOf(PlcBlock block) => block switch
        {
            OB _ => "OB",
            FB _ => "FB",
            FC _ => "FC",
            InstanceDB _ => "IDB",
            _ => "DB",
        };

        public static (string? OrderNo, string? Firmware) SplitTypeIdentifier(string? typeIdentifier)
        {
            // "OrderNumber:6ES7 516-3AN02-0AB0/V3.1"
            if (string.IsNullOrEmpty(typeIdentifier) || !typeIdentifier!.StartsWith("OrderNumber:", StringComparison.Ordinal))
                return (null, null);
            var rest = typeIdentifier.Substring("OrderNumber:".Length);
            var slash = rest.IndexOf('/');
            return slash < 0 ? (rest, null) : (rest.Substring(0, slash), rest.Substring(slash + 1));
        }

        public static string Family(string? orderNo)
        {
            if (orderNo == null) return "unknown";
            var o = orderNo.Replace(" ", "");
            if (o.StartsWith("6ES75", StringComparison.Ordinal)) return "S7-1500";
            if (o.StartsWith("6ES72", StringComparison.Ordinal)) return "S7-1200";
            if (o.StartsWith("6ES73", StringComparison.Ordinal)) return "S7-300";
            if (o.StartsWith("6ES74", StringComparison.Ordinal)) return "S7-400";
            return "other";
        }

        private static bool IsLicense(string text) =>
            text.IndexOf("license", StringComparison.OrdinalIgnoreCase) >= 0 && text.IndexOf("missing", StringComparison.OrdinalIgnoreCase) >= 0;

        private static string SafeFolder(string folder) =>
            string.Join("/", folder.Split('/').Select(Walk.Safe));
    }
}
