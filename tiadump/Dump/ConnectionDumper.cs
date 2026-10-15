// The configured connections of a PLC (docs/tiadump-connections.md). Openness holds them in
// CommunicationManagement.Connections of the CPU's device item;
// A connection of a CP of the same station is read from that item (owner_item). Only reads:
// GetService, enumeration, GetAttribute and the interface/target links.
using System;
using System.Collections.Generic;
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.HW.CommunicationConnections;
using Siemens.Engineering.HW.Features;
using TiaDump.Openness;

namespace TiaDump.Dump
{
    public static class ConnectionDumper
    {
        /// <summary>Sets <c>configured_connections</c> (and, on failure,
        /// <c>configured_connections_error</c>) of the PLC's device entry.</summary>
        public static void Plc(Dictionary<string, object?> plcEntry, Device device, DeviceItem cpu)
        {
            var list = new List<Dictionary<string, object?>>();
            string? error = null;
            try
            {
                // the CPU first, then the other items of its station (CPs); interfaces and ports
                // offer the service too but hold nothing
                foreach (var item in new[] { cpu }.Concat(Walk.Items(device.DeviceItems).Where(i => !i.Equals(cpu))))
                {
                    CommunicationManagement? cm;
                    try { cm = item.GetService<CommunicationManagement>(); }
                    catch (EngineeringException) { continue; }
                    if (cm == null) continue;
                    foreach (Connection c in cm.Connections)
                    {
                        var e = Entry(c, item.Name);
                        // one PLC never has two connections with one local ID: a second sight
                        // of the same connection (through another item) is skipped
                        if (list.Any(x => Equals(x["local_id"], e["local_id"]) && Equals(x["local_name"], e["local_name"]))) continue;
                        list.Add(e);
                    }
                }
            }
            catch (EngineeringException e) { error = TiaSession.Flatten(e).Split('\n')[0]; }
            plcEntry["configured_connections"] = list
                .OrderBy(e => (string?)e["local_id"], StringComparer.Ordinal)
                .ThenBy(e => (string?)e["local_name"], StringComparer.Ordinal)
                .Cast<object?>().ToList();
            plcEntry["configured_connections_error"] = error;
        }

        private static Dictionary<string, object?> Entry(Connection c, string owner)
        {
            var node = c.LocalInterface as Node;
            var type = Safe(() => c.ConnectionType.ToString());
            return new Dictionary<string, object?>
            {
                ["class"] = c.GetType().Name,
                ["type"] = type ?? c.GetType().Name,
                ["type_value"] = Safe(() => (int?)Convert.ToInt32(c.ConnectionType)),
                ["owner_item"] = owner,
                ["local_name"] = Text(c, "LocalConnectionName"),
                ["local_id"] = Text(c, "LocalConnectionId") ?? "",
                ["local_address"] = Text(c, "LocalAddress"),
                ["local_interface"] = node?.Name,
                ["local_node_type"] = node == null ? null : Safe(() => node.NodeType.ToString()),
                ["local_subnet"] = Text(c, "LocalSubnetName"),
                ["local_rack"] = Number(c, "LocalRack"),
                ["local_slot"] = Number(c, "LocalSlot"),
                ["local_tsap"] = Text(c, "LocalTsap"),
                ["use_acc"] = Flag(c, "LocalUseSimaticACC"),
                ["local_active"] = Flag(c, "LocalActiveEstablishment"),
                ["partner_name"] = Safe(() => (c.PartnerTarget as DeviceItem)?.Name),
                ["partner_id"] = Text(c, "PartnerConnectionId"),
                ["partner_address"] = Text(c, "PartnerAddress"),
                ["partner_rack"] = Number(c, "PartnerRack"),
                ["partner_slot"] = Number(c, "PartnerSlot"),
                ["partner_tsap"] = Text(c, "PartnerTsap"),
                ["partner_active"] = Flag(c, "PartnerActiveEstablishment"),
                ["valid"] = Safe(() => (bool?)c.IsValid),
            };
        }

        /// <summary>An attribute as text, <c>null</c> when absent or empty (contract: values as
        /// found).</summary>
        private static string? Text(IEngineeringObject o, string name)
        {
            try
            {
                var v = o.GetAttribute(name)?.ToString();
                return string.IsNullOrEmpty(v) ? null : v;
            }
            catch (EngineeringException) { return null; }
        }

        private static int? Number(IEngineeringObject o, string name) =>
            int.TryParse(Text(o, name), out var n) ? n : (int?)null;

        private static bool? Flag(IEngineeringObject o, string name) =>
            bool.TryParse(Text(o, name), out var b) ? b : (bool?)null;

        private static T? Safe<T>(Func<T?> f) where T : class
        {
            try { return f(); } catch (EngineeringException) { return null; }
        }

        private static int? Safe(Func<int?> f)
        {
            try { return f(); } catch (EngineeringException) { return null; } catch (InvalidCastException) { return null; }
        }

        private static bool? Safe(Func<bool?> f)
        {
            try { return f(); } catch (EngineeringException) { return null; }
        }
    }
}
