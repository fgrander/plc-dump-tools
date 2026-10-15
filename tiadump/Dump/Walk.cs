// Object model traversals shared by the dumpers (only reads).
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.SW.Blocks;
using Siemens.Engineering.SW.Tags;
using Siemens.Engineering.SW.Types;

namespace TiaDump.Dump
{
    public static class Walk
    {
        public static List<Device> Devices(Project project)
        {
            var list = new List<Device>(project.Devices);
            void Groups(DeviceUserGroupComposition groups)
            {
                foreach (DeviceUserGroup g in groups) { list.AddRange(g.Devices); Groups(g.Groups); }
            }
            Groups(project.DeviceGroups);
            list.AddRange(project.UngroupedDevicesGroup.Devices);
            return list.Distinct().ToList();
        }

        public static IEnumerable<DeviceItem> Items(DeviceItemComposition items)
        {
            foreach (DeviceItem item in items)
            {
                yield return item;
                foreach (var child in Items(item.DeviceItems)) yield return child;
            }
        }

        /// <summary>Blocks with their folder path ("Program blocks/Conveyor").</summary>
        public static List<(PlcBlock Block, string Folder)> Blocks(PlcBlockGroup group, string folder = "")
        {
            var here = Join(folder, group.Name);
            var list = group.Blocks.Select(b => (b, here)).ToList();
            IEnumerable<PlcBlockGroup> children = group switch
            {
                PlcBlockSystemGroup s => s.Groups.Cast<PlcBlockGroup>(),
                PlcBlockUserGroup u => u.Groups.Cast<PlcBlockGroup>(),
                _ => Enumerable.Empty<PlcBlockGroup>(),
            };
            foreach (var g in children) list.AddRange(Blocks(g, here));
            return list;
        }

        public static List<(PlcType Type, string Folder)> Types(PlcTypeGroup group, string folder = "")
        {
            var here = Join(folder, group.Name);
            var list = group.Types.Select(t => (t, here)).ToList();
            IEnumerable<PlcTypeGroup> children = group switch
            {
                PlcTypeSystemGroup s => s.Groups.Cast<PlcTypeGroup>(),
                PlcTypeUserGroup u => u.Groups.Cast<PlcTypeGroup>(),
                _ => Enumerable.Empty<PlcTypeGroup>(),
            };
            foreach (var g in children) list.AddRange(Types(g, here));
            return list;
        }

        public static List<(PlcTagTable Table, string Folder)> TagTables(PlcTagTableGroup group, string folder = "")
        {
            var here = Join(folder, group.Name);
            var list = group.TagTables.Select(t => (t, here)).ToList();
            IEnumerable<PlcTagTableGroup> children = group switch
            {
                PlcTagTableSystemGroup s => s.Groups.Cast<PlcTagTableGroup>(),
                PlcTagTableUserGroup u => u.Groups.Cast<PlcTagTableGroup>(),
                _ => Enumerable.Empty<PlcTagTableGroup>(),
            };
            foreach (var g in children) list.AddRange(TagTables(g, here));
            return list;
        }

        public static string Join(string a, string b) => a.Length == 0 ? b : a + "/" + b;

        /// <summary>Attribute as text, or null when the object has no such attribute.</summary>
        public static string? Attr(IEngineeringObject obj, string name)
        {
            try { return obj.GetAttribute(name)?.ToString(); }
            catch (Exception) { return null; }
        }

        /// <summary>Order number and firmware of a device item: from its TypeIdentifier, or for
        /// a GSD device (TypeIdentifier "GSD:...") from its OrderNumber attribute.</summary>
        public static (string? OrderNo, string? Firmware) OrderNumber(DeviceItem item)
        {
            var (orderNo, firmware) = PlcDumper.SplitTypeIdentifier(Attr(item, "TypeIdentifier"));
            if (orderNo != null) return (orderNo, firmware);
            var attr = Attr(item, "OrderNumber");
            return (string.IsNullOrWhiteSpace(attr) ? null : attr!.Trim(), firmware);
        }

        /// <summary>A hardware module: an item with an order number or with input/output
        /// addresses (GSD submodules have addresses but no order number).</summary>
        public static bool IsModule(DeviceItem item)
        {
            if (OrderNumber(item).OrderNo != null) return true;
            try
            {
                foreach (Address a in item.Addresses)
                {
                    var io = a.IoType.ToString().ToLowerInvariant();
                    if ((io == "input" || io == "output") && a.Length > 0) return true;
                }
            }
            catch (EngineeringException) { }
            return false;
        }

        public static int? IntAttr(IEngineeringObject obj, string name) =>
            int.TryParse(Attr(obj, name), out var v) ? v : (int?)null;

        /// <summary>File-system safe name (kept readable: only invalid characters are replaced).</summary>
        public static string Safe(string name) =>
            string.Concat(name.Select(c => Path.GetInvalidFileNameChars().Contains(c) ? '_' : c)).Trim().TrimEnd('.');
    }
}
