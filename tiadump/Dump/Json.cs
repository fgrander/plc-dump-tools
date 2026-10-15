// Canonical JSON writer (sorted keys, 2-space indent, LF, UTF-8 without BOM).
// Values: null, bool, int/long, double, string, IDictionary<string, object?>, IEnumerable.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;

namespace TiaDump.Dump
{
    public static class Json
    {
        public static string Serialize(object? value)
        {
            var sb = new StringBuilder();
            Write(sb, value, 0);
            sb.Append('\n');
            return sb.ToString();
        }

        public static void WriteFile(string path, object? value)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
            File.WriteAllText(path, Serialize(value), new UTF8Encoding(false));
        }

        /// <summary>Sort a sequence by a string key with ordinal comparison (deterministic output).</summary>
        public static List<T> SortedBy<T>(IEnumerable<T> items, Func<T, string> key) =>
            items.OrderBy(key, StringComparer.Ordinal).ToList();

        private static void Write(StringBuilder sb, object? v, int indent)
        {
            switch (v)
            {
                case null: sb.Append("null"); return;
                case bool b: sb.Append(b ? "true" : "false"); return;
                case string s: WriteString(sb, s); return;
                case int or long or short or byte or uint or ulong:
                    sb.Append(Convert.ToString(v, CultureInfo.InvariantCulture)); return;
                case double d: sb.Append(d.ToString("R", CultureInfo.InvariantCulture)); return;
                case float f: sb.Append(((double)f).ToString("R", CultureInfo.InvariantCulture)); return;
                case IDictionary<string, object?> map: WriteObject(sb, map, indent); return;
                case IDictionary dict:
                    WriteObject(sb, dict.Keys.Cast<object>().ToDictionary(k => k.ToString()!, k => (object?)dict[k]), indent);
                    return;
                case IEnumerable seq: WriteArray(sb, seq.Cast<object?>().ToList(), indent); return;
                default: WriteString(sb, Convert.ToString(v, CultureInfo.InvariantCulture) ?? ""); return;
            }
        }

        private static void WriteObject(StringBuilder sb, IDictionary<string, object?> map, int indent)
        {
            if (map.Count == 0) { sb.Append("{}"); return; }
            sb.Append("{\n");
            var keys = map.Keys.OrderBy(k => k, StringComparer.Ordinal).ToList();
            for (var i = 0; i < keys.Count; i++)
            {
                sb.Append(' ', indent + 2);
                WriteString(sb, keys[i]);
                sb.Append(": ");
                Write(sb, map[keys[i]], indent + 2);
                if (i < keys.Count - 1) sb.Append(',');
                sb.Append('\n');
            }
            sb.Append(' ', indent).Append('}');
        }

        private static void WriteArray(StringBuilder sb, List<object?> items, int indent)
        {
            if (items.Count == 0) { sb.Append("[]"); return; }
            sb.Append("[\n");
            for (var i = 0; i < items.Count; i++)
            {
                sb.Append(' ', indent + 2);
                Write(sb, items[i], indent + 2);
                if (i < items.Count - 1) sb.Append(',');
                sb.Append('\n');
            }
            sb.Append(' ', indent).Append(']');
        }

        private static void WriteString(StringBuilder sb, string s)
        {
            sb.Append('"');
            foreach (var c in s)
            {
                switch (c)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default:
                        if (c < 0x20) sb.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                        else sb.Append(c);
                        break;
                }
            }
            sb.Append('"');
        }
    }
}
