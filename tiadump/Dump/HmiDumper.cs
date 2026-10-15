// HMI devices. Comfort/Advanced: tag tables and screens are
// Exported as XML (the caller maps tags and bindings). Unified: object model.
// Devices whose product is missing are never touched (accessing them can stop TIA).
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.Hmi;
using Siemens.Engineering.HmiUnified;
using TiaDump.Openness;

namespace TiaDump.Dump
{
    public static class HmiDumper
    {
        internal static readonly string[] ComfortProducts = { "WinCC Basic", "WinCC Comfort", "WinCC Advanced", "WinCC Professional" };
        internal static readonly string[] UnifiedProducts = { "WinCC Unified" };

        public static Dictionary<string, object?> Comfort(DumpContext ctx, DeviceItem item, HmiTarget hmi)
        {
            var name = item.Name;
            var device = Base(name, Family(item));
            var missing = ctx.MissingFor(ComfortProducts);
            if (missing != null) return Skip(ctx, device, missing);
            var root = $"hmi/{Walk.Safe(name)}";

            device["connections"] = Guard(ctx, name, () => hmi.Connections.Cast<IEngineeringObject>()
                .Select(c => (object?)new Dictionary<string, object?> { ["name"] = Walk.Attr(c, "Name"), ["partner"] = Walk.Attr(c, "Partner") })
                .ToList());
            var tagFiles = new List<object?>();
            foreach (dynamic table in Tables(hmi.TagFolder))
            {
                var file = new FileInfo(ctx.PathOf($"{root}/tags/{Walk.Safe((string)table.Name)}.xml"));
                Try(ctx, $"{name}/{table.Name}", () => { table.Export(file, ExportOptions.WithDefaults); tagFiles.Add(ctx.Rel(file.FullName)); });
            }
            var screenFiles = new List<object?>();
            foreach (dynamic screen in Screens(hmi.ScreenFolder))
            {
                var file = new FileInfo(ctx.PathOf($"{root}/screens/{Walk.Safe((string)screen.Name)}.xml"));
                Try(ctx, $"{name}/{screen.Name}", () => { screen.Export(file, ExportOptions.WithDefaults); screenFiles.Add(ctx.Rel(file.FullName)); });
            }
            tagFiles.Sort((a, b) => string.CompareOrdinal((string?)a, (string?)b));
            screenFiles.Sort((a, b) => string.CompareOrdinal((string?)a, (string?)b));
            device["tag_files"] = tagFiles;
            device["screen_files"] = screenFiles;
            ctx.Error(name, "unsupported", "Comfort/Advanced alarms are not exposed by TIA Openness V21");
            return device;
        }

        public static Dictionary<string, object?> Unified(DumpContext ctx, DeviceItem item, HmiSoftware hmi)
        {
            var name = item.Name;
            var device = Base(name, "unified");
            var missing = ctx.MissingFor(UnifiedProducts);
            if (missing != null) return Skip(ctx, device, missing);

            device["connections"] = Guard(ctx, name, () => Objects(hmi.Connections, "Name", "Partner", "Station", "CommunicationDriver"));
            device["tags"] = Guard(ctx, name, () => Objects(hmi.Tags, "Name", "Connection", "PlcTag", "DataType", "Address", "Comment"));
            var alarms = new List<object?>();
            alarms.AddRange(Guard(ctx, name, () => Objects(hmi.DiscreteAlarms, "Name", "AlarmClass", "EventText", "RaisedStateTag", "TriggerBitAddress"))
                .Select(a => Tag(a, "discrete")));
            alarms.AddRange(Guard(ctx, name, () => Objects(hmi.AnalogAlarms, "Name", "AlarmClass", "EventText", "RaisedStateTag", "Limit"))
                .Select(a => Tag(a, "analog")));
            device["alarms"] = alarms;
            device["screens"] = Guard(ctx, name, () => hmi.Screens.Cast<IEngineeringObject>().Select(s => (object?)new Dictionary<string, object?>
            {
                ["name"] = Walk.Attr(s, "Name"),
                ["objects"] = Objects((IEnumerable)((dynamic)s).ScreenItems, "Name"),
            }).ToList());
            return device;
        }

        public static Dictionary<string, object?> Other(DumpContext ctx, DeviceItem item, object software)
        {
            ctx.Error(item.Name, "unsupported", $"HMI family {software.GetType().Name} is not supported");
            return Base(item.Name, "other");
        }

        private static Dictionary<string, object?> Base(string name, string family) => new Dictionary<string, object?>
        {
            ["name"] = name, ["kind"] = "hmi", ["hmi_family"] = family,
            ["connections"] = new List<object?>(), ["tags"] = new List<object?>(), ["screens"] = new List<object?>(),
            ["alarms"] = new List<object?>(), ["library_links"] = new List<object?>(),
        };

        private static Dictionary<string, object?> Skip(DumpContext ctx, Dictionary<string, object?> device, string missing)
        {
            device["missing_package"] = missing;
            ctx.Error((string)device["name"]!, "missing_package", $"{missing} is not installed; HMI not read");
            return device;
        }

        private static string Family(DeviceItem item)
        {
            var type = Walk.Attr(item, "TypeIdentifier") ?? "";
            return type.IndexOf("RT Advanced", StringComparison.OrdinalIgnoreCase) >= 0 || type.IndexOf("WinCC RT", StringComparison.OrdinalIgnoreCase) >= 0
                ? "advanced" : "comfort";
        }

        private static object? Tag(object? alarm, string kind)
        {
            if (alarm is Dictionary<string, object?> d) d["kind"] = kind;
            return alarm;
        }

        private static List<object?> Objects(IEnumerable items, params string[] attributes) =>
            items.Cast<object>().OfType<IEngineeringObject>()
                .Select(o => (object?)attributes.ToDictionary(a => Snake(a), a => (object?)Walk.Attr(o, a)))
                .OrderBy(o => (string?)((Dictionary<string, object?>)o!)["name"], StringComparer.Ordinal)
                .ToList();

        private static string Snake(string pascal) =>
            string.Concat(pascal.Select((c, i) => i > 0 && char.IsUpper(c) ? "_" + char.ToLowerInvariant(c) : char.ToLowerInvariant(c).ToString()));

        internal static IEnumerable<object> Tables(dynamic folder)
        {
            foreach (var t in folder.TagTables) yield return t;
            foreach (var f in folder.Folders) foreach (var t in Tables(f)) yield return t;
        }

        internal static IEnumerable<object> Screens(dynamic folder)
        {
            foreach (var s in folder.Screens) yield return s;
            foreach (var f in folder.Folders) foreach (var s in Screens(f)) yield return s;
        }

        private static List<object?> Guard(DumpContext ctx, string where, Func<List<object?>> read)
        {
            try { return read(); }
            catch (EngineeringException e) { ctx.Error(where, "export_failed", TiaSession.Flatten(e)); return new List<object?>(); }
        }

        private static void Try(DumpContext ctx, string where, Action action)
        {
            try { action(); }
            catch (EngineeringException e) { ctx.Error(where, "export_failed", TiaSession.Flatten(e)); }
        }
    }
}
