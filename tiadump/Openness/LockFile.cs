// TIA Portal keeps `<project>.info` (User, Computer, Time) next to an open
// Project. The open failure text is in the TIA UI language of the host, so a lock is recognized by
// The holder named in this file, not by wording. No Siemens types here (unit-testable without TIA).
using System;
using System.IO;
using System.Xml;
using System.Xml.Linq;

namespace TiaDump.Openness
{
    public static class LockFile
    {
        /// <summary>
        /// "user on computer since time" when the failure text names the holder recorded in
        /// <c>&lt;project&gt;.info</c>; otherwise null (no lock file, or a failure for another reason).
        /// </summary>
        public static string? Holder(string projectFile, string failureText)
        {
            var info = Path.ChangeExtension(projectFile, ".info");
            try
            {
                if (!File.Exists(info)) return null;
                string xml;
                using (var s = new FileStream(info, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
                using (var r = new StreamReader(s)) xml = r.ReadToEnd();
                var root = XDocument.Parse(xml).Root;
                var user = root?.Element("User")?.Value;
                var computer = root?.Element("Computer")?.Value;
                var time = root?.Element("Time")?.Value;
                if (string.IsNullOrEmpty(user) || string.IsNullOrEmpty(computer)) return null;
                if (failureText.IndexOf(user, StringComparison.OrdinalIgnoreCase) < 0 ||
                    failureText.IndexOf(computer, StringComparison.OrdinalIgnoreCase) < 0) return null;
                return $"{user} on {computer} since {time}";
            }
            catch (Exception x) when (x is IOException || x is UnauthorizedAccessException || x is XmlException)
            {
                return null;
            }
        }
    }
}
