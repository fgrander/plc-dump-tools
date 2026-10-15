// S7dump: reads a STEP 7 V5.x project with DotNetSiemensPLCToolBoxLibrary and writes one JSON
// Document (docs/s7dump-json.md). Read-only: it never writes anything except
// The --out file. Exit codes: 0 = JSON written (may contain "errors"), 2 = project not openable.
using System.Text;
using S7Dump;

Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);

string? project = null, outFile = null, mnemonic = "en", encodingName = null;
bool sources = true;
for (var i = 0; i < args.Length; i++)
{
    switch (args[i])
    {
        case "--out": outFile = args[++i]; break;
        case "--mnemonic": mnemonic = args[++i]; break;
        case "--no-sources": sources = false; break;
        case "--encoding": encodingName = args[++i]; break;
        case "--help" or "-h":
            Console.WriteLine("usage: s7dump <project.s7p|project.s7l|folder> --out <dump.json> [--mnemonic en|de] [--no-sources] [--encoding windows-1252]");
            return 0;
        default: project ??= args[i]; break;
    }
}
if (project is null || outFile is null || (mnemonic != "en" && mnemonic != "de"))
{
    Console.Error.WriteLine("usage: s7dump <project.s7p|project.s7l|folder> --out <dump.json> [--mnemonic en|de] [--no-sources]");
    return 64;
}

string? projectFile;
try
{
    projectFile = ProjectLocator.Find(project);
}
catch (Exception e)
{
    Console.Error.WriteLine($"cannot open project: {e.Message}");
    return 2;
}

Dumper dumper;
try
{
    var forced = encodingName is null ? null : Encoding.GetEncoding(encodingName);
    dumper = new Dumper(projectFile, mnemonic == "en", sources, forced);
}
catch (Exception e)
{
    Console.Error.WriteLine($"cannot open project: {e.GetType().Name}: {e.Message}");
    return 2;
}
using (dumper)
{
    var json = dumper.Dump();
    File.WriteAllText(outFile, json, new UTF8Encoding(false));
}
return 0;
