// Completeness counts. A pass of its own over the object
// Model, before and independent of the export calls, so a failed export cannot lower a count.
// A count that cannot be read is left out (the dumper records the same failure), never set to 0.
// Not counted, because Openness V21 has no collection for them: PLC alarms (only the
// xlsx export) and Comfort/Advanced HMI alarms.
using System;
using System.Collections;
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.HW.Features;
using Siemens.Engineering.Hmi;
using Siemens.Engineering.HmiUnified;
using Siemens.Engineering.Library.MasterCopies;
using Siemens.Engineering.Library.Types;
using Siemens.Engineering.SW;

namespace TiaDump.Dump
{
    public static class CountsDumper
    {
        /// <summary>Per PLC and HMI (scope = device name), `_hardware` and `_project_library`.</summary>
        public static void Project(DumpContext ctx, Project project)
        {
            var modules = 0;
            foreach (var device in Walk.Devices(project))
            foreach (var item in Walk.Items(device.DeviceItems))
            {
                if (Walk.IsModule(item)) modules++;
                object? software;
                try { software = item.GetService<SoftwareContainer>()?.Software; }
                catch (EngineeringException) { continue; }
                switch (software)
                {
                    case PlcSoftware plc: Plc(ctx, plc); break;
                    case HmiTarget comfort: Comfort(ctx, item.Name, comfort); break;
                    case HmiSoftware unified: Unified(ctx, item.Name, unified); break;
                }
            }
            ctx.Count("_hardware", "modules", modules);
            Try(() => Library(ctx, "_project_library", project.ProjectLibrary.TypeFolder, project.ProjectLibrary.MasterCopyFolder));
        }

        /// <summary>Types, type versions and master copies of one library.</summary>
        public static void Library(DumpContext ctx, string scope, LibraryTypeFolder? typeFolder, MasterCopyFolder? copyFolder)
        {
            var types = typeFolder == null ? 0 : LibraryDumper.Types(typeFolder, "").Count();
            var versions = typeFolder == null ? 0 : LibraryDumper.Types(typeFolder, "").Sum(t => t.Type.Versions.Count);
            var copies = copyFolder == null ? 0 : LibraryDumper.Copies(copyFolder, "").Count();
            ctx.Count(scope, "types", types);
            ctx.Count(scope, "type_versions", versions);
            ctx.Count(scope, "master_copies", copies);
        }

        private static void Plc(DumpContext ctx, PlcSoftware plc)
        {
            if (ctx.MissingFor(PlcDumper.Products) != null) return;  // the program is not read
            var name = plc.Name;
            Try(() => ctx.Count(name, "units", Walk.Blocks(plc.BlockGroup).Count + Walk.Types(plc.TypeGroup).Count));
            Try(() =>
            {
                var tables = Walk.TagTables(plc.TagTableGroup);
                var tags = tables.Sum(t => t.Table.Tags.Count + t.Table.UserConstants.Count);
                ctx.Count(name, "tag_tables", tables.Count);
                ctx.Count(name, "tags", tags);
            });
        }

        private static void Comfort(DumpContext ctx, string name, HmiTarget hmi)
        {
            if (ctx.MissingFor(HmiDumper.ComfortProducts) != null) return;  // never touched
            Try(() => ctx.Count(name, "hmi_tags", HmiDumper.Tables(hmi.TagFolder).Sum(t => (int)((dynamic)t).Tags.Count)));
            Try(() => ctx.Count(name, "screens", HmiDumper.Screens(hmi.ScreenFolder).Count()));
        }

        private static void Unified(DumpContext ctx, string name, HmiSoftware hmi)
        {
            if (ctx.MissingFor(HmiDumper.UnifiedProducts) != null) return;
            Try(() => ctx.Count(name, "hmi_tags", Size(hmi.Tags)));
            Try(() => ctx.Count(name, "screens", Size(hmi.Screens)));
            Try(() => ctx.Count(name, "hmi_alarms", Size(hmi.DiscreteAlarms) + Size(hmi.AnalogAlarms)));
        }

        private static int Size(IEnumerable items) => items.Cast<object>().OfType<IEngineeringObject>().Count();

        private static void Try(Action count)
        {
            try { count(); }
            catch (EngineeringException) { }
        }
    }
}
