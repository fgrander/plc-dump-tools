// Hardware configuration by walking the object model. Only reads.
using System;
using System.Collections.Generic;
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.HW.Features;

namespace TiaDump.Dump
{
    public static class HardwareDumper
    {
        public static Dictionary<string, object?> Dump(DumpContext ctx, Project project)
        {
            var devices = new List<object?>();
            var controllers = IoControllers(project);
            foreach (var device in Walk.Devices(project))
            {
                var items = new List<object?>();
                foreach (var item in Walk.Items(device.DeviceItems))
                {
                    var (orderNo, firmware) = Walk.OrderNumber(item);
                    var addresses = Addresses(item);
                    var interfaces = Interfaces(item);
                    // modules: items with an order number, I/O addresses or a network interface
                    if (orderNo == null && addresses.Count == 0 && interfaces.Count == 0) continue;
                    var entry = new Dictionary<string, object?>
                    {
                        ["name"] = item.Name,
                        ["path"] = PathOf(item),
                        ["rack"] = RackOf(item),
                        ["slot"] = Walk.IntAttr(item, "PositionNumber"),
                        ["order_no"] = orderNo,
                        ["firmware"] = NullIfEmpty(Walk.Attr(item, "FirmwareVersion")) ?? firmware,
                        ["addresses"] = addresses,
                        ["interfaces"] = interfaces,
                    };
                    if (interfaces.Count > 0) IoFacts(item, entry, controllers);
                    items.Add(entry);
                }
                devices.Add(new Dictionary<string, object?> { ["name"] = device.Name, ["items"] = items });
            }
            return new Dictionary<string, object?> { ["devices"] = devices, ["subnets"] = Subnets(project) };
        }

        private static List<object?> Addresses(DeviceItem item)
        {
            var list = new List<object?>();
            try
            {
                foreach (Address a in item.Addresses)
                {
                    var io = a.IoType.ToString().ToLowerInvariant();
                    if (io != "input" && io != "output") continue;  // diagnostics/substitute addresses
                    list.Add(new Dictionary<string, object?> { ["io"] = io, ["start"] = a.StartAddress, ["length"] = a.Length });
                }
            }
            catch (EngineeringException) { }
            return list;
        }

        private static List<object?> Interfaces(DeviceItem item)
        {
            var list = new List<object?>();
            NetworkInterface? ni;
            try { ni = item.GetService<NetworkInterface>(); } catch (EngineeringException) { return list; }
            if (ni == null) return list;
            foreach (Node node in ni.Nodes)
            {
                var ip = Walk.Attr(node, "Address");
                var mask = Walk.Attr(node, "SubnetMask");
                list.Add(new Dictionary<string, object?>
                {
                    ["node"] = node.Name,
                    ["type"] = node.NodeType.ToString(),
                    ["address"] = ip != null && mask != null ? $"{ip}/{PrefixLength(mask)}" : ip,
                    ["device_name"] = Walk.Attr(node, "PnDeviceName"),
                    ["subnet"] = SafeName(() => node.ConnectedSubnet?.Name),
                });
            }
            return list;
        }

        /// <summary>IO system name -> the device item (CPU) that controls it,
        /// as "&lt;device&gt;/&lt;path&gt;".</summary>
        private static Dictionary<string, string> IoControllers(Project project)
        {
            var map = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var device in Walk.Devices(project))
            foreach (var item in Walk.Items(device.DeviceItems))
            {
                NetworkInterface? ni;
                try { ni = item.GetService<NetworkInterface>(); } catch (EngineeringException) { continue; }
                if (ni == null) continue;
                try
                {
                    foreach (IoController c in ni.IoControllers)
                        if (c.IoSystem != null && item.Parent is DeviceItem cpu)
                            map[c.IoSystem.Name] = $"{device.Name}/{PathOf(cpu)}";
                }
                catch (EngineeringException) { }
            }
            return map;
        }

        /// <summary>the IO system an interface is an IO device in, and its
        /// transfer areas (PN/PN coupler sides) with the controller's addresses.</summary>
        private static void IoFacts(DeviceItem item, Dictionary<string, object?> entry, Dictionary<string, string> controllers)
        {
            NetworkInterface? ni;
            try { ni = item.GetService<NetworkInterface>(); } catch (EngineeringException) { return; }
            if (ni == null) return;
            try
            {
                var system = ni.IoConnectors.Cast<IoConnector>().Select(c => c.ConnectedToIoSystem).FirstOrDefault(s => s != null);
                if (system != null)
                    entry["io_system"] = new Dictionary<string, object?>
                    {
                        ["name"] = system.Name,
                        ["number"] = system.Number,
                        ["controller"] = controllers.TryGetValue(system.Name, out var c) ? c : null,
                    };
            }
            catch (EngineeringException) { }
            var areas = new List<object?>();
            try
            {
                foreach (TransferArea t in ni.TransferAreas)
                {
                    var addresses = new List<object?>();
                    foreach (Address a in t.PartnerAddresses)
                    {
                        var io = a.IoType.ToString().ToLowerInvariant();
                        if (io != "input" && io != "output") continue;
                        var owner = a.AddressControllers.Cast<object>().FirstOrDefault() is IEngineeringObject ac && ac.Parent is DeviceItem cpu
                            ? cpu.Name : null;
                        addresses.Add(new Dictionary<string, object?>
                        {
                            ["io"] = io, ["start"] = a.StartAddress, ["bits"] = a.Length, ["controller"] = owner,
                        });
                    }
                    areas.Add(new Dictionary<string, object?>
                    {
                        ["name"] = t.Name,
                        ["type"] = t.Type.ToString(),
                        ["direction"] = t.Direction.ToString(),
                        ["position"] = t.PositionNumber,
                        ["local_to_partner_bytes"] = t.LocalToPartnerLength,
                        ["partner_to_local_bytes"] = t.PartnerToLocalLength,
                        ["controller_addresses"] = addresses,
                    });
                }
            }
            catch (EngineeringException) { }
            if (areas.Count > 0) entry["transfer_areas"] = areas;
        }

        private static List<object?> Subnets(Project project)
        {
            var list = new List<object?>();
            foreach (Subnet s in project.Subnets)
            {
                list.Add(new Dictionary<string, object?>
                {
                    ["name"] = s.Name,
                    ["kind"] = s.NetType.ToString(),
                    ["io_systems"] = s.IoSystems.Cast<IoSystem>().Select(io => (object?)io.Name).ToList(),
                    ["nodes"] = s.Nodes.Cast<Node>().Select(n => (object?)$"{DeviceOf(n)}/{n.Name}").ToList(),
                });
            }
            return list;
        }

        private static string PathOf(DeviceItem item)
        {
            var parts = new List<string>();
            for (IEngineeringObject? o = item; o is DeviceItem d; o = d.Parent) parts.Insert(0, d.Name);
            return string.Join("/", parts);
        }

        private static string? RackOf(DeviceItem item)
        {
            // the topmost device item below the device is the rack (or the device's head item)
            DeviceItem top = item;
            while (top.Parent is DeviceItem parent) top = parent;
            return top.Name;
        }

        private static string DeviceOf(Node node)
        {
            IEngineeringObject? o = node.Parent;
            while (o != null && !(o is Device)) o = o.Parent;
            return (o as Device)?.Name ?? "?";
        }

        private static string? NullIfEmpty(string? s) => string.IsNullOrEmpty(s) ? null : s;

        public static int PrefixLength(string mask)
        {
            var bits = 0;
            foreach (var part in mask.Split('.'))
                if (byte.TryParse(part, out var b)) bits += Convert.ToString(b, 2).Count(c => c == '1');
            return bits;
        }

        private static string? SafeName(Func<string?> f)
        {
            try { return f(); } catch (EngineeringException) { return null; }
        }
    }
}
