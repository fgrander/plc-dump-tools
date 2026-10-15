// Where PLC alarm texts, alarm classes, text lists and supervisions come from.
// Research probe; its findings went into Dump/AlarmDumper.cs.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.HW.Features;
using Siemens.Engineering.SW;
using Siemens.Engineering.SW.Alarm;
using Siemens.Engineering.SW.Blocks;
using Siemens.Engineering.SW.Supervision;

namespace TiaDump.Spikes
{
    public static class AlarmSpike
    {
        public static List<object?> Run(Project project, string outDir)
        {
            var result = new List<object?>();
            foreach (var device in SpikeRunner.AllDevices(project))
            foreach (var item in SpikeRunner.Flatten(device.DeviceItems))
            {
                if (!(item.GetService<SoftwareContainer>()?.Software is PlcSoftware plc)) continue;
                var name = SpikeRunner.Safe(item.Name);
                var dir = Path.Combine(outDir, "alarms", name);
                Directory.CreateDirectory(dir);
                var entry = new Dictionary<string, object?> { ["plc"] = name };

                // alarm instance texts (program alarms, ProDiag, system diagnostics) as xlsx
                entry["text_provider_on"] = Where<PlcAlarmTextProvider>(plc, item, project);
                entry["texts_xlsx"] = Probe(() =>
                {
                    var provider = Find<PlcAlarmTextProvider>(plc, item, project)
                        ?? throw new InvalidOperationException("no PlcAlarmTextProvider");
                    var file = new FileInfo(Path.Combine(dir, "alarm_texts.xlsx"));
                    var r = provider.ExportInstanceTextsToXlsx(file, null, PlcAlarmTextXlsxExportOption.All);
                    return $"{r.State} size={(file.Exists ? file.Length : -1)} log={r.LogFilePath}";
                });

                // alarm classes
                entry["class_provider_on"] = Where<AlarmClassDataProvider>(plc, item, project);
                entry["classes"] = Probe(() =>
                {
                    var provider = Find<AlarmClassDataProvider>(plc, item, project)
                        ?? throw new InvalidOperationException("no AlarmClassDataProvider");
                    var file = new FileInfo(Path.Combine(dir, "alarm_classes.xml"));
                    var r = provider.Export(file);
                    return $"{r.GetType().Name} size={(file.Exists ? file.Length : -1)}";
                });

                // supervisions (ProDiag)
                entry["supervision_provider_on"] = Where<SupervisionProvider>(plc, item, project);
                entry["supervisions"] = Probe(() =>
                {
                    var provider = Find<SupervisionProvider>(plc, item, project)
                        ?? throw new InvalidOperationException("no SupervisionProvider");
                    var file = new FileInfo(Path.Combine(dir, "supervisions.xlsx"));
                    var r = provider.ExportSupervisionsToXlsx(file);
                    return $"{r.State} size={(file.Exists ? file.Length : -1)} log={r.LogFilePath}";
                });

                // text lists
                entry["user_textlists"] = Probe(() => string.Join(", ",
                    plc.PlcAlarmTextlistGroup.PlcAlarmUserTextlists.Select(t => t.Name)));
                entry["system_textlists"] = Probe(() =>
                    plc.PlcAlarmTextlistGroup.PlcAlarmSystemTextlists.Count.ToString());
                // type-level alarm texts: SimaticML of FBs (compiled in the working copy, FR-004b)
                var fbs = new List<object?>();
                foreach (var block in SpikeRunner.AllBlocks(plc.BlockGroup).OfType<FB>())
                {
                    if (block.IsKnowHowProtected) continue;
                    var file = new FileInfo(Path.Combine(dir, "fb", SpikeRunner.Safe(block.Name) + ".xml"));
                    Directory.CreateDirectory(file.DirectoryName!);
                    fbs.Add(block.Name + ": " + Probe(() =>
                    {
                        var c = Openness.CopyCompiler.CompileUnit(block);
                        block.Export(file, ExportOptions.WithDefaults);
                        return "compile " + (c.Ok ? "ok" : "failed") + ", xml ok";
                    }));
                }
                entry["fb_simaticml"] = fbs;
                result.Add(entry);
            }
            return result;
        }

        private static T? Find<T>(params IEngineeringServiceProvider[] owners) where T : class, IEngineeringService
        {
            foreach (var o in owners)
            {
                try
                {
                    var s = o.GetService<T>();
                    if (s != null) return s;
                }
                catch (Exception) { }
            }
            return null;
        }

        private static string Where<T>(PlcSoftware plc, DeviceItem item, Project project) where T : class, IEngineeringService
        {
            var found = new List<string>();
            if (Find<T>(plc) != null) found.Add("PlcSoftware");
            if (Find<T>(item) != null) found.Add("DeviceItem");
            if (Find<T>(project) != null) found.Add("Project");
            return found.Count == 0 ? "none" : string.Join(",", found);
        }

        private static string Probe(Func<string> action)
        {
            try { return action(); }
            catch (Exception e) { return "error: " + Openness.TiaSession.Flatten(e); }
        }
    }
}
