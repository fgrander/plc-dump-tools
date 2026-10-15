// A project opened elsewhere is recognized by its lock file, in any TIA UI language.
using System;
using System.IO;
using System.Text;
using TiaDump.Openness;
using Xunit;

namespace TiaDump.Tests
{
    public class LockFileTests
    {
        private const string Info =
            "<?xml version=\"1.0\"?>\n<InfoFile xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">\n" +
            "  <User>operator7</User>\n  <Computer>ENG-PC-12</Computer>\n  <Time>2026-10-09T19:19:26.2641439Z</Time>\n</InfoFile>";

        private const string GermanLockText =
            "Error when calling method 'Open' of type 'Siemens.Engineering.ProjectComposition'. | " +
            "Auf das Projekt/die Bibliothek C:\\w\\Line3\\Line3.ap21 kann nicht zugegriffen werden. " +
            "Es/sie wurde bereits vom Benutzer operator7 auf dem Computer ENG-PC-12 geöffnet.";

        private static string Project(string? info)
        {
            var dir = Path.Combine(Path.GetTempPath(), "tiadump-lock-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(dir);
            var file = Path.Combine(dir, "Line3.ap21");
            File.WriteAllText(file, "");
            if (info != null) File.WriteAllText(Path.Combine(dir, "Line3.info"), info, Encoding.UTF8);
            return file;
        }

        [Fact]
        public void LockedWhenTheFailureNamesTheHolder()
        {
            Assert.Equal("operator7 on ENG-PC-12 since 2026-10-09T19:19:26.2641439Z",
                LockFile.Holder(Project(Info), GermanLockText));
        }

        [Fact]
        public void NotLockedWithoutLockFile()
        {
            Assert.Null(LockFile.Holder(Project(null), GermanLockText));
        }

        [Fact]
        public void NotLockedWhenTheFailureHasAnotherCause()
        {
            Assert.Null(LockFile.Holder(Project(Info), "Required products are missing in the installation."));
        }

        [Fact]
        public void NotLockedWhenTheLockFileIsDamaged()
        {
            Assert.Null(LockFile.Holder(Project("<InfoFile><User>operator7"), GermanLockText));
        }
    }
}
