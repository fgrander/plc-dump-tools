// What Openness V21 exposes for WinCC Comfort/Advanced (HmiTarget) and
// WinCC Unified (HmiSoftware): tags, connections, screens, alarms. Research probe; its findings went
// Into Dump/HmiDumper.cs. Only reads and exports.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.HW.Features;
using Siemens.Engineering.Hmi;
using Siemens.Engineering.HmiUnified;

namespace TiaDump.Spikes
{
    public static class HmiSpike
    {
        private const int Sample = 3;  // attributes of the first N objects per collection

        public static List<object?> Run(Project project, string outDir)
        {
            var result = new List<object?>();
            foreach (var device in SpikeRunner.AllDevices(project))
            foreach (var item in SpikeRunner.Flatten(device.DeviceItems))
            {
                var software = item.GetService<SoftwareContainer>()?.Software;
                if (software is HmiTarget comfort) result.Add(Comfort(item.Name, comfort, outDir));
                else if (software is HmiSoftware unified) result.Add(Unified(item.Name, unified));
                else if (software != null && !(software is Siemens.Engineering.SW.PlcSoftware))
                    result.Add(new Dictionary<string, object?> { ["device"] = item.Name, ["software"] = software.GetType().FullName });
            }
            return result;
        }

        private static Dictionary<string, object?> Comfort(string name, HmiTarget hmi, string outDir)
        {
            var dir = Path.Combine(outDir, "hmi", SpikeRunner.Safe(name));
            Directory.CreateDirectory(dir);
            var r = new Dictionary<string, object?> { ["device"] = name, ["family"] = "HmiTarget" };
            r["connections"] = Probe(() => Describe(hmi.Connections));
            r["tag_tables"] = Probe(() =>
            {
                var tables = new List<object?>();
                foreach (Siemens.Engineering.Hmi.Tag.TagTable t in AllTagTables(hmi.TagFolder))
                {
                    var file = new FileInfo(Path.Combine(dir, "tags_" + SpikeRunner.Safe(t.Name) + ".xml"));
                    var export = Probe(() => { t.Export(file, ExportOptions.WithDefaults); return $"ok {file.Length} bytes"; });
                    tables.Add(new Dictionary<string, object?> { ["name"] = t.Name, ["tags"] = t.Tags.Count, ["export"] = export, ["sample"] = Describe(t.Tags) });
                }
                return tables;
            });
            r["screens"] = Probe(() =>
            {
                var screens = new List<object?>();
                foreach (Siemens.Engineering.Hmi.Screen.Screen s in AllScreens(hmi.ScreenFolder))
                {
                    var file = new FileInfo(Path.Combine(dir, "screen_" + SpikeRunner.Safe(s.Name) + ".xml"));
                    screens.Add(s.Name + ": " + Probe(() => { s.Export(file, ExportOptions.WithDefaults); return $"ok {file.Length} bytes"; }));
                }
                return screens;
            });
            r["text_lists"] = Probe(() => hmi.TextLists.Count);
            r["attributes"] = Probe(() => Attributes(hmi));
            return r;
        }

        private static Dictionary<string, object?> Unified(string name, HmiSoftware hmi)
        {
            var r = new Dictionary<string, object?> { ["device"] = name, ["family"] = "HmiSoftware" };
            r["connections"] = Probe(() => Describe(hmi.Connections));
            r["tags"] = Probe(() => Describe(hmi.Tags));
            r["tag_tables"] = Probe(() => hmi.TagTables.Count);
            r["discrete_alarms"] = Probe(() => Describe(hmi.DiscreteAlarms));
            r["analog_alarms"] = Probe(() => Describe(hmi.AnalogAlarms));
            r["alarm_classes"] = Probe(() => Describe(hmi.AlarmClasses));
            r["screens"] = Probe(() => Describe(hmi.Screens));
            r["screen_items"] = Probe(() =>
            {
                var items = new List<object?>();
                foreach (dynamic screen in hmi.Screens.Cast<object>().Take(2))
                    items.Add(new Dictionary<string, object?> { ["screen"] = (string)screen.Name, ["items"] = Describe((IEnumerable)screen.ScreenItems) });
                return items;
            });
            r["text_lists"] = Probe(() => hmi.HmiTextLists.Count);
            return r;
        }

        private static IEnumerable<object> AllTagTables(dynamic folder)
        {
            foreach (var t in folder.TagTables) yield return t;
            foreach (var f in folder.Folders) foreach (var t in AllTagTables(f)) yield return t;
        }

        private static IEnumerable<object> AllScreens(dynamic folder)
        {
            foreach (var s in folder.Screens) yield return s;
            foreach (var f in folder.Folders) foreach (var s in AllScreens(f)) yield return s;
        }

        private static Dictionary<string, object?> Describe(IEnumerable items)
        {
            var list = items.Cast<object>().ToList();
            return new Dictionary<string, object?>
            {
                ["count"] = list.Count,
                ["sample"] = list.Take(Sample).Select(o => (object?)(o is IEngineeringObject e ? Attributes(e) : o.ToString())).ToList(),
            };
        }

        private static Dictionary<string, object?> Attributes(IEngineeringObject o)
        {
            var d = new Dictionary<string, object?> { ["_type"] = o.GetType().Name };
            foreach (var info in o.GetAttributeInfos())
            {
                try
                {
                    var v = o.GetAttribute(info.Name);
                    d[info.Name] = v is IEngineeringObject eo ? $"<{eo.GetType().Name} {TryName(eo)}>"
                        : v is IEnumerable en && !(v is string) ? $"[{en.Cast<object>().Count()} items]"
                        : v?.ToString();
                }
                catch (Exception e) { d[info.Name] = "error: " + e.Message.Split('\n')[0]; }
            }
            return d;
        }

        private static string TryName(IEngineeringObject o)
        {
            try { return o.GetAttribute("Name")?.ToString() ?? ""; } catch (Exception) { return ""; }
        }

        private static object? Probe(Func<object?> action)
        {
            try { return action(); }
            catch (Exception e) { return "error: " + Openness.TiaSession.Flatten(e); }
        }
    }
}
