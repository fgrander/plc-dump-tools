namespace S7Dump;

/// <summary>Finds the .s7p/.s7l file for a path that is a project file or a project folder.</summary>
public static class ProjectLocator
{
    public static string Find(string path)
    {
        if (File.Exists(path))
        {
            var ext = Path.GetExtension(path).ToLowerInvariant();
            if (ext is ".s7p" or ".s7l") return path;
            throw new InvalidOperationException($"not a STEP 7 project file: {path}");
        }
        if (!Directory.Exists(path)) throw new FileNotFoundException(path);
        var candidates = Directory.EnumerateFiles(path, "*.*", SearchOption.TopDirectoryOnly)
            .Where(f => f.EndsWith(".s7p", StringComparison.OrdinalIgnoreCase)
                     || f.EndsWith(".s7l", StringComparison.OrdinalIgnoreCase))
            .OrderBy(f => f, StringComparer.Ordinal)
            .ToList();
        if (candidates.Count == 0) throw new InvalidOperationException($"no .s7p/.s7l in {path}");
        return candidates[0];
    }
}
