// Tiadump CLI (docs/tiadump.md). Never receives a source path: the caller passes a
// Copy in the job's work directory. Exit codes are the contract with the caller (docs/tiadump.md).
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;

namespace TiaDump
{
    public static class ExitCodes
    {
        public const int Ok = 0;              // dump written (may contain errors[])
        public const int CannotOpen = 2;      // damaged, missing product, other open failure
        public const int UpgradeRefused = 3;  // TIA refused the upgrade
        public const int AccessDenied = 4;    // Openness group, whitelist, UMAC
        public const int Locked = 5;          // project opened elsewhere
        public const int Usage = 64;
    }

    public sealed class Options
    {
        public string Command = "";
        public string File = "";
        public string? Work;
        public string? Out;
        public string? Tia;                 // e.g. "V21"; default newest installed
        public string Languages = "all";
        public bool WithUi;                 // --with-ui: show TIA Portal (manual license activation, debugging)
        public string? UmacUserEnv;
        public string? UmacPasswordEnv;
        public string? SpikeName;           // tiadump spike <name> <file> ...

        public static Options Parse(string[] args)
        {
            if (args.Length == 0) throw new UsageException("missing command");
            var o = new Options { Command = args[0] };
            var positional = new List<string>();
            for (var i = 1; i < args.Length; i++)
            {
                var a = args[i];
                string Next() => i + 1 < args.Length ? args[++i] : throw new UsageException($"{a} needs a value");
                switch (a)
                {
                    case "--work": o.Work = Next(); break;
                    case "--out": o.Out = Next(); break;
                    case "--tia": o.Tia = Next(); break;
                    case "--languages": o.Languages = Next(); break;
                    case "--with-ui": o.WithUi = true; break;
                    case "--umac-user-env": o.UmacUserEnv = Next(); break;
                    case "--umac-password-env": o.UmacPasswordEnv = Next(); break;
                    default:
                        if (a.StartsWith("--", StringComparison.Ordinal)) throw new UsageException($"unknown option {a}");
                        positional.Add(a);
                        break;
                }
            }
            if (o.Command == "spike")
            {
                if (positional.Count < 2) throw new UsageException("spike needs <name> <file>");
                o.SpikeName = positional[0];
                o.File = positional[1];
            }
            else if (o.Command != "--version" && o.Command != "installed")
            {
                if (positional.Count != 1) throw new UsageException("expected exactly one <file>");
                o.File = positional[0];
            }
            if (o.Out == null && o.Command != "--version") throw new UsageException("--out is required");
            if ((o.Command == "project" || o.Command == "library" || o.Command == "spike") && o.Work == null)
                throw new UsageException("--work is required");
            return o;
        }
    }

    public sealed class UsageException : Exception
    {
        public UsageException(string message) : base(message) { }
    }

    /// <summary>Thrown inside tiadump to end with a specific exit code and message.</summary>
    public sealed class ExitException : Exception
    {
        public int Code { get; }
        public ExitException(int code, string message) : base(message) { Code = code; }
    }

    public static class Program
    {
        public static string Version =>
            typeof(Program).Assembly.GetName().Version?.ToString(3) ?? "0.0.0";

        [STAThread]
        public static int Main(string[] args)
        {
            Options o;
            try
            {
                o = Options.Parse(args);
            }
            catch (UsageException e)
            {
                Console.Error.WriteLine($"tiadump: {e.Message}");
                Console.Error.WriteLine("usage: tiadump probe|project|library <file> --out <path> [--work <dir>] [--tia V21]");
                Console.Error.WriteLine("       tiadump installed --out <path> [--tia V21]");
                Console.Error.WriteLine("       [--umac-user-env NAME --umac-password-env NAME] [--with-ui] | tiadump --version");
                return ExitCodes.Usage;
            }

            if (o.Command == "--version")
            {
                Console.WriteLine($"tiadump {Version}");
                return ExitCodes.Ok;
            }

            try
            {
                switch (o.Command)
                {
                    case "probe":
                        return Dump.Probe.Run(o);
                    case "project":
                    case "library":
                    case "spike":
                    case "installed":
                        // The Openness commands need the Siemens assemblies; resolve them first.
                        Openness.AssemblyResolver.Install(o.Tia);
                        return RunOpenness(o);
                    default:
                        Console.Error.WriteLine($"tiadump: unknown command {o.Command}");
                        return ExitCodes.Usage;
                }
            }
            catch (ExitException e)
            {
                Console.Error.WriteLine($"tiadump: {e.Message}");
                return e.Code;
            }
        }

        // Kept in its own method so that no Siemens type is touched before AssemblyResolver runs.
        private static int RunOpenness(Options o)
        {
            try
            {
                switch (o.Command)
                {
                    case "project": return Dump.ProjectDumper.Run(o);
                    case "library": return Dump.LibraryDumper.Run(o);
                    case "installed": return Dump.Installed.Run(o);
                    default: return Spikes.SpikeRunner.Run(o);
                }
            }
            catch (Siemens.Engineering.EngineeringException e)
            {
                // e.g. EngineeringObjectDisposedException when TIA Portal stops during a run
                throw new ExitException(ExitCodes.CannotOpen, "TIA Portal failed: " + Openness.TiaSession.Flatten(e));
            }
        }
    }
}
