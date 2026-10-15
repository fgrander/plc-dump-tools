// Upgrade messages, saved update and missing products reported on open.
using System;
using System.IO;
using System.Text;
using TiaDump.Openness;
using Xunit;

namespace TiaDump.Tests
{
    public class OpenReportTests
    {
        // Shape of TIA V21's Logs\ConversionLog_19.0.0.0_to_21.0.0.0.xml (texts in the TIA UI language).
        private const string Log =
            "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<LogFile projectName=\"Line3_V21\" typeText=\"Typ\" messageText=\"Meldung\" timeText=\"Zeit\">\n" +
            "<MessageCell ServiceId=\"80\" MessageId=\"30\" MessageClass=\"Information\" Timestamp=\"09.10.2026 21:34:56\"><Number ServiceNumber=\"80\" MessageNumber=\"30\" /><Text FeedbackText=\"Hochrüsten gestartet\" /><Help HelpId=\"-1\" /></MessageCell>\n" +
            "<MessageCell ServiceId=\"80\" MessageId=\"30\" MessageClass=\"Information\" Timestamp=\"09.10.2026 21:34:57\"><Number ServiceNumber=\"80\" MessageNumber=\"30\" /><Text FeedbackText=\"Projekt hochgerüstet von Version: 1900.3.501.1.\" /><Help HelpId=\"-1\" /></MessageCell>\n" +
            "<Details ServiceId=\"80\" MessageId=\"30\" Timestamp=\"09.10.2026 21:34:58\" Debug=\"false\"><Text>Reorganization succeed!</Text></Details>\n" +
            "<MessageCell ServiceId=\"80\" MessageId=\"31\" MessageClass=\"Warning\" Timestamp=\"09.10.2026 21:35:10\"><Number ServiceNumber=\"80\" MessageNumber=\"31\" /><Text FeedbackText=\"Projektelement: '\\PLC_1\\ProgramBlocksFolder\\RUN' - Prüfsummeninkonsistenz für 'CallerMemoryLayout'.\" /><Help HelpId=\"-1\" /></MessageCell>\n" +
            "<MessageCell ServiceId=\"80\" MessageId=\"32\" MessageClass=\"Success\" Timestamp=\"09.10.2026 21:35:59\"><Number ServiceNumber=\"80\" MessageNumber=\"32\" /><Text FeedbackText=\"Fertig\" /><Help HelpId=\"-1\" /></MessageCell>\n" +
            "</LogFile>";

        private static string Work(string? log)
        {
            var work = Path.Combine(Path.GetTempPath(), "tiadump-open-" + Guid.NewGuid().ToString("N"));
            var logs = Path.Combine(work, "retrieved", "Line3", "Logs");
            Directory.CreateDirectory(logs);
            if (log != null) File.WriteAllText(Path.Combine(logs, "ConversionLog_19.0.0.0_to_21.0.0.0.xml"), log, Encoding.UTF8);
            return work;
        }

        [Fact]
        public void UpgradeMessagesKeepWarningsAndErrorsOnly()
        {
            Assert.Equal(
                new[] { "Warning: Projektelement: '\\PLC_1\\ProgramBlocksFolder\\RUN' - Prüfsummeninkonsistenz für 'CallerMemoryLayout'." },
                OpenReport.UpgradeMessages(Work(Log)));
        }

        [Fact]
        public void LogCopiedIntoTheUpgradedFolderCountsOnce()
        {
            var work = Work(Log);
            var upgraded = Path.Combine(work, "retrieved", "Line3_V21", "Logs");
            Directory.CreateDirectory(upgraded);
            File.WriteAllText(Path.Combine(upgraded, "ConversionLog_19.0.0.0_to_21.0.0.0.xml"), Log, Encoding.UTF8);
            Assert.Single(OpenReport.UpgradeMessages(work));
        }

        [Fact]
        public void UnreadableLogIsReportedNotThrown()
        {
            var messages = OpenReport.UpgradeMessages(Work("<LogFile><MessageCell"));
            Assert.Single(messages);
            Assert.StartsWith("Warning: conversion log ConversionLog_19.0.0.0_to_21.0.0.0.xml unreadable", messages[0]);
        }

        [Fact]
        public void NoLogNoMessages()
        {
            Assert.Empty(OpenReport.UpgradeMessages(Work(null)));
        }

        [Fact]
        public void SavedUpdateFromTechnicalVersion()
        {
            Assert.Equal("Upd3", OpenReport.SavedUpdate(Work(Log), 19));
            Assert.Null(OpenReport.SavedUpdate(Work(Log), 18));
            Assert.Null(OpenReport.SavedUpdate(Work(null), 19));
        }

        [Fact]
        public void BundledInstalledProductCoversItsParts()
        {
            var used = new[] { ("STEP 7 Professional", "V21"), ("WinCC Comfort", "V21"), ("SINAMICS Startdrive Advanced", "V21") };
            var installed = new[] { ("STEP 7 Professional", "V21"), ("WinCC Basic/Comfort/Advanced", "V21"), ("WinCC Unified", "V21") };
            Assert.Equal(new[] { "SINAMICS Startdrive Advanced V21" }, OpenReport.MissingProducts(used, installed));
        }

        [Fact]
        public void OtherVersionIsMissing()
        {
            Assert.Equal(new[] { "WinCC Comfort V20" },
                OpenReport.MissingProducts(new[] { ("WinCC Comfort", "V20") }, new[] { ("WinCC Basic/Comfort/Advanced", "V21") }));
        }
    }
}
