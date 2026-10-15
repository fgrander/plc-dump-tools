// One TIA Portal session per tiadump run.
// Read-only by construction: it only opens the COPY that the caller placed in --work, retrieves
// Archives into --work, and upgrades only that copy. Nothing is ever saved, compiled,
// downloaded or put online (ForbiddenApiTests).
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security;
using System.Text.RegularExpressions;
using Siemens.Engineering;
using Siemens.Engineering.Library;

namespace TiaDump.Openness
{
    public sealed class TiaSession : IDisposable
    {
        private static readonly Regex Suffix = new Regex(@"\.(z?ap|z?al)(\d\d)$", RegexOptions.IgnoreCase);

        private readonly Options _options;
        private TiaPortal? _portal;

        public TiaPortal Portal => _portal ?? throw new InvalidOperationException("TIA Portal not started");

        public Project? Project { get; private set; }
        public UserGlobalLibrary? Library { get; private set; }

        /// <summary>Saved TIA major version of the file (from its suffix), e.g. 19.</summary>
        public int SavedMajor { get; }

        /// <summary>TIA major version used for the export, e.g. 21.</summary>
        public int PortalMajor { get; }

        public bool Upgraded { get; private set; }
        public List<string> Messages { get; } = new List<string>();
        public string MultiuserKind { get; private set; } = "none";
        public List<Dictionary<string, object?>> MissingPackages { get; } = new List<Dictionary<string, object?>>();

        /// <summary>Project.UsedProducts, so that the caller learns what the project needs.</summary>
        public List<(string Name, string Version)> UsedProducts { get; } = new List<(string, string)>();

        public TiaSession(Options options)
        {
            _options = options;
            var m = Suffix.Match(options.File);
            if (!m.Success) throw new ExitException(ExitCodes.Usage, $"not a TIA project or library: {options.File}");
            SavedMajor = int.Parse(m.Groups[2].Value);
            PortalMajor = int.Parse((AssemblyResolver.PortalVersion ?? "V0").TrimStart('V'));
            if (SavedMajor > PortalMajor)
                throw new ExitException(ExitCodes.UpgradeRefused,
                    $"saved with V{SavedMajor}, newer than the installed TIA Portal V{PortalMajor}");
        }

        public bool IsLibrary => Suffix.Match(_options.File).Groups[1].Value.ToLowerInvariant().EndsWith("al", StringComparison.Ordinal);
        public bool IsArchive => Suffix.Match(_options.File).Groups[1].Value.StartsWith("z", StringComparison.OrdinalIgnoreCase);
        public bool NeedsUpgrade => SavedMajor < PortalMajor;

        public void Open()
        {
            var file = new FileInfo(_options.File);
            if (!file.Exists) throw new ExitException(ExitCodes.CannotOpen, $"file not found: {file.FullName}");
            var work = new DirectoryInfo(_options.Work!);
            Directory.CreateDirectory(work.FullName);
            if (!IsInside(file.FullName, work.FullName))
                throw new ExitException(ExitCodes.Usage, "the file must be a copy inside --work");
            var folder = ProjectFolder(work);
            if (folder.Length > MaxProjectPath)
                throw new ExitException(ExitCodes.CannotOpen,
                    $"path too long for TIA Portal: {folder} has {folder.Length} characters, at most {MaxProjectPath} - use a shorter --work");

            try
            {
                // Starting TIA Portal already checks the Openness group (EngineeringSecurityException).
                // --with-ui shows TIA Portal for a person at the host (e.g. to activate a trial
                // license). Then TIA's own dialogs stay with that person: notifications are only
                // recorded and confirmations are not answered by tiadump.
                _portal = new TiaPortal(_options.WithUi ? TiaPortalMode.WithUserInterface : TiaPortalMode.WithoutUserInterface);
                _portal.Notification += (_, e) =>
                {
                    Messages.Add($"notification: {e.Caption}: {e.Text} {e.DetailText}".Trim());
                    e.IsHandled = !_options.WithUi;
                };
                if (!_options.WithUi) _portal.Confirmation += OnConfirmation;
                if (IsLibrary) OpenLibrary(file, work);
                else OpenProject(file, work);
                Upgraded = NeedsUpgrade;
                if (Upgraded)
                {
                    Messages.AddRange(OpenReport.UpgradeMessages(work.FullName));
                    SavedUpdate = OpenReport.SavedUpdate(work.FullName, SavedMajor);
                }
                if (Project != null) ReportMissingProducts();
            }
            catch (EngineeringSecurityException e)
            {
                throw new ExitException(ExitCodes.AccessDenied, $"Openness access denied: {e.Message}");
            }
            catch (EngineeringTargetInvocationException e)
            {
                throw Classify(e);
            }
            catch (EngineeringException e)
            {
                throw Classify(e);
            }
        }

        /// <summary>Saved update level ("Upd3"), known after an upgrade from the conversion log.</summary>
        public string? SavedUpdate { get; private set; }

        // Products the project uses that are not installed did not block the open (otherwise TIA
        // refuses it, exit 2); the parts that need them are missing from the export.
        private void ReportMissingProducts()
        {
            var used = Project!.UsedProducts.Select(u => (u.Name, u.Version)).ToList();
            UsedProducts.AddRange(used);
            var installed = _portal!.GetCurrentProcess().InstalledSoftware.Select(s => (s.Name, s.Version)).ToList();
            foreach (var missing in OpenReport.MissingProducts(used, installed))
                MissingPackages.Add(new Dictionary<string, object?> { ["name"] = missing, ["kind"] = "product" });
        }

        private void OpenProject(FileInfo file, DirectoryInfo work)
        {
            var umac = UmacDelegateOrNull();
            if (IsArchive)
            {
                var target = new DirectoryInfo(Path.Combine(work.FullName, "retrieved"));
                Project = NeedsUpgrade
                    ? (umac == null ? _portal!.Projects.RetrieveWithUpgrade(file, target) : _portal!.Projects.RetrieveWithUpgrade(file, target, umac))
                    : (umac == null ? _portal!.Projects.Retrieve(file, target) : _portal!.Projects.Retrieve(file, target, umac));
            }
            else
            {
                Project = NeedsUpgrade
                    ? (umac == null ? _portal!.Projects.OpenWithUpgrade(file) : _portal!.Projects.OpenWithUpgrade(file, umac))
                    : (umac == null ? _portal!.Projects.Open(file) : _portal!.Projects.Open(file, umac));
            }
        }

        private void OpenLibrary(FileInfo file, DirectoryInfo work)
        {
            if (IsArchive)
            {
                var target = new DirectoryInfo(Path.Combine(work.FullName, "retrieved"));
                Library = NeedsUpgrade
                    ? _portal!.GlobalLibraries.RetrieveWithUpgrade(file, target, OpenMode.ReadOnly)
                    : _portal!.GlobalLibraries.Retrieve(file, target, OpenMode.ReadOnly);
            }
            else
            {
                Library = NeedsUpgrade
                    ? _portal!.GlobalLibraries.OpenWithUpgrade(file)
                    : _portal!.GlobalLibraries.Open(file, OpenMode.ReadOnly);
            }
        }

        private UmacDelegate? UmacDelegateOrNull()
        {
            var userEnv = _options.UmacUserEnv;
            var passwordEnv = _options.UmacPasswordEnv;
            if (userEnv == null || passwordEnv == null) return null;
            var user = Environment.GetEnvironmentVariable(userEnv);
            var password = Environment.GetEnvironmentVariable(passwordEnv);
            if (string.IsNullOrEmpty(user) || password == null)
                throw new ExitException(ExitCodes.AccessDenied, "UMAC credentials missing");
            return credentials =>
            {
                credentials.Type = UmacUserType.Project;
                credentials.Name = user;
                var secure = new SecureString();
                foreach (var c in password) secure.AppendChar(c);
                secure.MakeReadOnly();
                credentials.SetPassword(secure);
            };
        }

        // Confirmations can only appear while opening/upgrading the working copy. They are
        // answered with the least invasive choice that lets the open continue and recorded.
        private void OnConfirmation(object? sender, ConfirmationEventArgs e)
        {
            ConfirmationResult answer;
            if ((e.Choices & ConfirmationChoices.Ok) != 0) answer = ConfirmationResult.Ok;
            else if ((e.Choices & ConfirmationChoices.Yes) != 0) answer = ConfirmationResult.Yes;
            else if ((e.Choices & ConfirmationChoices.Ignore) != 0) answer = ConfirmationResult.Ignore;
            else answer = ConfirmationResult.Cancel;
            Messages.Add($"confirmation: {e.Caption}: {e.Text} -> {answer}".Trim());
            e.Result = answer;
            e.IsHandled = true;
        }

        // TIA's innermost message is in the TIA UI language of the host, so the lock is
        // recognized by the lock file, not by wording. Openness frames every failure with
        // "Error when calling method 'OpenWithUpgrade' ...", which must not count as an upgrade text.
        private ExitException Classify(Exception e)
        {
            var text = Flatten(e);
            var holder = LockFile.Holder(_options.File, text);
            if (holder != null)
                return new ExitException(ExitCodes.Locked, $"locked - retry later: opened by {holder}");
            if (Regex.IsMatch(text, @"\b(locked|in use|already open|being used|another process)\b", RegexOptions.IgnoreCase))
                return new ExitException(ExitCodes.Locked, $"locked - retry later: {text}");
            var detail = Regex.Replace(text, @"Error when calling method '[^']*'", "");
            if (NeedsUpgrade && Regex.IsMatch(detail, @"upgrad", RegexOptions.IgnoreCase))
                return new ExitException(ExitCodes.UpgradeRefused, $"TIA refused upgrade: {text}");
            if (Regex.IsMatch(text, @"(product|package|option|license|not installed|HSP|support package)", RegexOptions.IgnoreCase))
                return new ExitException(ExitCodes.CannotOpen, $"missing software: {text}");
            return new ExitException(ExitCodes.CannotOpen, text);
        }

        /// <summary>TIA Portal V21 refuses project folders longer than this.</summary>
        public const int MaxProjectPath = 143;

        /// <summary>
        /// The longest project folder TIA will use: the retrieve target for archives (TIA checks
        /// <c>retrieved\&lt;archive name&gt;</c>), else the file's folder; an upgrade writes a sibling
        /// folder with the suffix <c>_V&lt;major&gt;</c>.
        /// </summary>
        public string ProjectFolder(DirectoryInfo work)
        {
            var file = new FileInfo(_options.File);
            var folder = IsArchive
                ? Path.Combine(work.FullName, "retrieved", Path.GetFileNameWithoutExtension(file.Name))
                : file.DirectoryName!;
            return NeedsUpgrade ? $"{folder}_V{PortalMajor}" : folder;
        }

        public static string Flatten(Exception e)
        {
            var parts = new List<string>();
            for (Exception? x = e; x != null; x = x.InnerException)
                if (!string.IsNullOrWhiteSpace(x.Message) && !parts.Contains(x.Message)) parts.Add(x.Message.Trim());
            return string.Join(" | ", parts);
        }

        private static bool IsInside(string path, string folder)
        {
            var f = Path.GetFullPath(folder).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            return Path.GetFullPath(path).StartsWith(f, StringComparison.OrdinalIgnoreCase);
        }

        public void Dispose()
        {
            try { Project?.Close(); } catch (Exception e) { Messages.Add($"close: {e.Message}"); }
            try { Library?.Close(); } catch (Exception e) { Messages.Add($"close: {e.Message}"); }
            try { _portal?.Dispose(); } catch (Exception e) { Messages.Add($"dispose: {e.Message}"); }
            Project = null;
            Library = null;
            _portal = null;
        }
    }
}
