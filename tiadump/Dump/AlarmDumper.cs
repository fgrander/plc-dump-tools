// PLC alarms and safety signatures. Only reads and exports.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.Safety;
using Siemens.Engineering.SW;
using Siemens.Engineering.SW.Alarm;
using Siemens.Engineering.SW.Supervision;
using TiaDump.Openness;

namespace TiaDump.Dump
{
    public static class AlarmDumper
    {
        /// <summary>Alarm instance texts and ProDiag supervisions as xlsx (the caller reads them).</summary>
        public static Dictionary<string, object?> Dump(DumpContext ctx, PlcSoftware plc)
        {
            var root = $"alarms/{Walk.Safe(plc.Name)}";
            var result = new Dictionary<string, object?> { ["texts_file"] = null, ["supervisions_file"] = null };
            try
            {
                var provider = plc.GetService<PlcAlarmTextProvider>();
                if (provider != null)
                {
                    var file = new FileInfo(ctx.PathOf($"{root}/alarm_texts.xlsx"));
                    provider.ExportInstanceTextsToXlsx(file, null, PlcAlarmTextXlsxExportOption.All);
                    if (file.Exists) result["texts_file"] = ctx.Rel(file.FullName);
                }
            }
            catch (EngineeringException e)
            {
                // "there is no exportable alarm" (in the TIA UI language) = no alarms; anything
                // else is recorded. The texts file is simply absent in both cases.
                var text = TiaSession.Flatten(e);
                if (!LooksLikeNoAlarms(text)) ctx.Error($"{plc.Name}/alarms", "export_failed", text);
            }
            try
            {
                var provider = plc.GetService<SupervisionProvider>();
                if (provider != null)
                {
                    var file = new FileInfo(ctx.PathOf($"{root}/supervisions.xlsx"));
                    var r = provider.ExportSupervisionsToXlsx(file);
                    if (r.State == SupervisionXlsxResultState.Success && file.Exists) result["supervisions_file"] = ctx.Rel(file.FullName);
                }
            }
            catch (EngineeringException e) { ctx.Error($"{plc.Name}/supervisions", "export_failed", TiaSession.Flatten(e)); }
            return result;
        }

        private static bool LooksLikeNoAlarms(string text) =>
            text.IndexOf("exportierbare Meldung", StringComparison.OrdinalIgnoreCase) >= 0
            || text.IndexOf("no exportable", StringComparison.OrdinalIgnoreCase) >= 0
            || text.IndexOf("exportable alarm", StringComparison.OrdinalIgnoreCase) >= 0;

        /// <summary>Safety signatures as TIA records them; never compiled for.</summary>
        public static Dictionary<string, object?> Safety(DumpContext ctx, DeviceItem item, PlcSoftware plc)
        {
            var signatures = new List<object?>();
            foreach (var owner in new IEngineeringServiceProvider[] { plc, item })
            {
                try
                {
                    var provider = owner.GetService<SafetySignatureProvider>();
                    if (provider == null) continue;
                    foreach (SafetySignature s in provider.Signatures)
                        signatures.Add(new Dictionary<string, object?> { ["kind"] = s.Type.ToString(), ["value"] = $"0x{s.Value:X8}" });
                    break;
                }
                catch (EngineeringException e) { ctx.Error($"{plc.Name}/safety", "export_failed", TiaSession.Flatten(e)); }
            }
            signatures = signatures.OrderBy(s => (string?)((Dictionary<string, object?>)s!)["kind"], StringComparer.Ordinal).ToList();
            return new Dictionary<string, object?> { ["signatures"] = signatures };
        }
    }
}
