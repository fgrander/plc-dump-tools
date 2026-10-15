// Library links of PLC units. A link is what
// LibraryTypeInstanceInfo reports for the object - never inferred from names or content.
// The link points to the project library's type version; its global origin is only known by the
// library name (LibraryTypeVersion.OriginalLibrary).
using System;
using System.Collections.Generic;
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.Library.Types;
using Siemens.Engineering.SW;
using TiaDump.Openness;

namespace TiaDump.Dump
{
    public static class LinkDumper
    {
        public static List<object?> Plc(DumpContext ctx, string plcName, PlcSoftware plc)
        {
            var units = Walk.Blocks(plc.BlockGroup).Select(b => ((IEngineeringServiceProvider)b.Block, b.Block.Name))
                .Concat(Walk.Types(plc.TypeGroup).Select(t => ((IEngineeringServiceProvider)t.Type, t.Type.Name)));
            var links = new List<Dictionary<string, object?>>();
            foreach (var (unit, name) in units)
            {
                try
                {
                    var info = unit.GetService<LibraryTypeInstanceInfo>();
                    if (info != null) links.Add(Link(name, "unit", info.LibraryTypeVersion));
                }
                catch (EngineeringException e)
                {
                    ctx.Error($"{plcName}/{name}", "export_failed", "library link: " + TiaSession.Flatten(e));
                }
            }
            return links.OrderBy(l => (string?)l["object"], StringComparer.Ordinal).Cast<object?>().ToList();
        }

        public static Dictionary<string, object?> Link(string objectName, string objectKind, LibraryTypeVersion v)
        {
            var type = v.TypeObject;
            string? original = null;
            try { original = v.OriginalLibrary; } catch (EngineeringException) { }
            return new Dictionary<string, object?>
            {
                ["object"] = objectName,
                ["object_kind"] = objectKind,
                ["type_name"] = type.Name,
                ["type_folder"] = FolderOf(type),
                ["version"] = v.VersionNumber.ToString(),
                ["status"] = LibraryDumper.Status(v),
                ["original_library"] = string.IsNullOrEmpty(original) ? null : original,
                ["type_guid"] = type.Guid.ToString(),
            };
        }

        /// <summary>"Types/Material": the user folders between the library's type folder and the type.</summary>
        private static string FolderOf(LibraryType type)
        {
            var parts = new List<string>();
            for (var o = type.Parent; o is LibraryTypeUserFolder f; o = f.Parent) parts.Insert(0, f.Name);
            return string.Join("/", parts);
        }
    }
}
