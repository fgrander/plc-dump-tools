// What Openness V21 exposes for configured connections (S7, TCP, ISO-on-TCP, ...):
// The services that hold them, every attribute of each connection and the objects its local
// And partner interface and target links point to. Only reads (GetService, GetAttribute,
// enumeration).
using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.HW.CommunicationConnections;
using Siemens.Engineering.HW.Features;
using TiaDump.Openness;

namespace TiaDump.Spikes
{
    public static class ConnectionSpike
    {
        public static Dictionary<string, object?> Run(Project project)
        {
            var services = typeof(CommunicationManagement).Assembly.GetTypes()
                .Concat(AppDomain.CurrentDomain.GetAssemblies()
                    .Where(a => a.GetName().Name.StartsWith("Siemens.Engineering", StringComparison.Ordinal))
                    .SelectMany(SafeTypes))
                .Where(t => typeof(CommunicationManagement).IsAssignableFrom(t) && !t.IsAbstract)
                .Distinct().ToList();
            var found = new List<object?>();
            foreach (var device in SpikeRunner.AllDevices(project))
            foreach (var item in SpikeRunner.Flatten(device.DeviceItems))
            foreach (var service in services)
            {
                object? provider;
                try { provider = GetService(item, service); }
                catch (Exception e) { found.Add(new Dictionary<string, object?> { ["item"] = item.Name, ["service"] = service.Name, ["error"] = First(e) }); continue; }
                if (!(provider is CommunicationManagement cm)) continue;
                var connections = new List<object?>();
                try
                {
                    foreach (Connection c in cm.Connections) connections.Add(Describe(c));
                }
                catch (Exception e) { connections.Add("error: " + First(e)); }
                found.Add(new Dictionary<string, object?>
                {
                    ["device"] = device.Name, ["item"] = item.Name, ["service"] = service.FullName,
                    ["count"] = connections.Count, ["connections"] = connections,
                });
            }
            return new Dictionary<string, object?>
            {
                ["services"] = services.Select(t => (object?)t.FullName).ToList(),
                ["found"] = found,
                ["io"] = Io(project),
            };
        }

        /// <summary>per device item its order number, its I/O addresses
        /// with the controllers that own them, and for network interfaces the IO systems they
        /// are connected to or control, and their transfer areas.</summary>
        private static List<object?> Io(Project project)
        {
            var items = new List<object?>();
            foreach (var device in SpikeRunner.AllDevices(project))
            foreach (var item in SpikeRunner.Flatten(device.DeviceItems))
            {
                var d = new Dictionary<string, object?> { ["device"] = device.Name, ["item"] = Name(item) };
                d["order_no"] = Try(() => item.GetAttribute("OrderNumber")?.ToString());
                d["type"] = Try(() => item.GetAttribute("TypeIdentifier")?.ToString());
                var addresses = new List<object?>();
                try
                {
                    foreach (Address a in item.Addresses)
                        addresses.Add($"{a.IoType} {a.StartAddress} len {a.Length} controllers [" +
                            string.Join(", ", a.AddressControllers.Cast<object>().Select(Name)) + "]");
                }
                catch (Exception e) { addresses.Add("error: " + First(e)); }
                if (addresses.Count > 0) d["addresses"] = addresses;
                NetworkInterface? ni = null;
                try { ni = item.GetService<NetworkInterface>(); } catch (Exception) { }
                if (ni != null)
                {
                    d["connectors"] = Try(() => string.Join("; ", ni.IoConnectors.Cast<IoConnector>()
                        .Select(c => c.ConnectedToIoSystem == null ? "(none)" : $"{c.ConnectedToIoSystem.Name} #{c.ConnectedToIoSystem.Number}")));
                    d["controls"] = Try(() => string.Join("; ", ni.IoControllers.Cast<IoController>()
                        .Select(c => c.IoSystem == null ? "(none)" : $"{c.IoSystem.Name} #{c.IoSystem.Number}")));
                    d["transfer_areas"] = Try(() => string.Join("; ", ni.TransferAreas.Cast<IEngineeringObject>()
                        .Select(t => string.Join(", ", Attributes(t).Select(kv => kv.Key + "=" + kv.Value)))));
                    d["transfer_area_addresses"] = Try(() => string.Join("; ", ni.TransferAreas.Cast<TransferArea>()
                        .Select(t => $"{t.Name}: local [{Addresses(t.LocalAddresses)}] partner [{Addresses(t.PartnerAddresses)}]")));
                }
                if (addresses.Count > 0 || ni != null) items.Add(d);
            }
            return items;
        }

        private static string Addresses(IEnumerable? addresses) => addresses == null ? "" :
            string.Join(", ", addresses.Cast<Address>().Select(a => $"{a.IoType} {a.StartAddress} len {a.Length} by [" +
                string.Join(", ", a.AddressControllers.Cast<object>().Select(Name)) + "]"));

        private static IEnumerable<Type> SafeTypes(Assembly a)
        {
            try { return a.GetTypes(); }
            catch (ReflectionTypeLoadException e) { return e.Types.Where(t => t != null)!; }
        }

        private static object? GetService(DeviceItem item, Type service)
        {
            var generic = typeof(IEngineeringServiceProvider).GetMethod("GetService")!.MakeGenericMethod(service);
            return generic.Invoke(item, null);
        }

        private static Dictionary<string, object?> Describe(Connection c)
        {
            var d = Attributes(c);
            d["_class"] = c.GetType().FullName;
            d["_type"] = Try(() => c.ConnectionType.ToString());
            d["_valid"] = Try(() => c.IsValid.ToString());
            d["_local_interface"] = Try(() => Name(c.LocalInterface));
            d["_partner_interface"] = Try(() => Name(c.PartnerInterface));
            d["_local_target"] = Try(() => Name(c.LocalTarget));
            d["_partner_target"] = Try(() => Name(c.PartnerTarget));
            d["_local_subnet"] = Try(() => c.LocalSubnetName);
            d["_partner_subnet"] = Try(() => c.PartnerSubnetName);
            if (c.LocalInterface is IEngineeringObject li) d["_local_interface_attributes"] = Attributes(li);
            if (c.PartnerInterface is IEngineeringObject pi) d["_partner_interface_attributes"] = Attributes(pi);
            return d;
        }

        private static string? Name(object? o)
        {
            if (o == null) return null;
            var parts = new List<string>();
            for (var x = o as IEngineeringObject; x != null && parts.Count < 6; x = x.Parent as IEngineeringObject)
                parts.Add(TryName(x) ?? x.GetType().Name);
            parts.Reverse();
            return $"<{o.GetType().Name}> " + string.Join(" / ", parts);
        }

        private static Dictionary<string, object?> Attributes(IEngineeringObject o)
        {
            var d = new Dictionary<string, object?>();
            foreach (var info in o.GetAttributeInfos())
            {
                try
                {
                    var v = o.GetAttribute(info.Name);
                    d[info.Name] = v is IEngineeringObject eo ? Name(eo)
                        : v is byte[] bytes ? BitConverter.ToString(bytes)
                        : v is IEnumerable en && !(v is string) ? "[" + string.Join(", ", en.Cast<object>().Take(20)) + "]"
                        : v?.ToString();
                }
                catch (Exception e) { d[info.Name] = "error: " + First(e); }
            }
            return d;
        }

        private static string? TryName(IEngineeringObject o)
        {
            try { return o.GetAttribute("Name")?.ToString(); } catch (Exception) { return null; }
        }

        private static string? Try(Func<string?> f)
        {
            try { return f(); } catch (Exception e) { return "error: " + First(e); }
        }

        private static string First(Exception e) => TiaSession.Flatten(e).Split('\n')[0];
    }
}
