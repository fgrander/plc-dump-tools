<#
.SYNOPSIS
    Adds tiadump.exe to the TIA Portal Openness allow list, so it runs without the access dialog.

.DESCRIPTION
    TIA Portal V21 asks once per executable build whether an
    Openness client may access TIA Portal and remembers the answer in
        HKLM\SOFTWARE\Siemens\Automation\Openness\AllowList\<exe name>\Entry[ (n)]
    with the string values
        Path          full path of the executable
        DateModified  LastWriteTime of the file in UTC, "yyyy/MM/dd HH:mm:ss.fff"
        FileHash      SHA-256 of the file, base64
    The entry is bound to the hash, so run this script again after every build.
    Older entries for the same path are replaced. Needs an elevated shell (the key is writable for
    Administrators and SYSTEM only). Writes nothing outside this registry key.

.PARAMETER Exe
    Path of tiadump.exe (default: publish\tiadump.exe next to this script).

.EXAMPLE
    # admin PowerShell, after `dotnet build tiadump -c Release -o tiadump/publish`
    .\tiadump\install-whitelist.ps1
    .\tiadump\install-whitelist.ps1 -Exe D:\tia-host\tiadump\tiadump.exe -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Exe = (Join-Path $PSScriptRoot 'publish\tiadump.exe')
)

$ErrorActionPreference = 'Stop'
$allowList = 'HKLM:\SOFTWARE\Siemens\Automation\Openness\AllowList'

$file = Get-Item -LiteralPath $Exe
if (-not (Test-Path 'HKLM:\SOFTWARE\Siemens\Automation\Openness')) {
    throw 'TIA Portal Openness is not installed on this computer.'
}

$sha = [Security.Cryptography.SHA256]::Create()
try {
    $stream = [IO.File]::OpenRead($file.FullName)
    try { $hash = [Convert]::ToBase64String($sha.ComputeHash($stream)) } finally { $stream.Dispose() }
} finally { $sha.Dispose() }
$modified = $file.LastWriteTimeUtc.ToString('yyyy/MM/dd HH:mm:ss.fff', [Globalization.CultureInfo]::InvariantCulture)

$appKey = Join-Path $allowList $file.Name
Write-Output "Path         $($file.FullName)"
Write-Output "DateModified $modified"
Write-Output "FileHash     $hash"

if (-not $WhatIfPreference) {
    $admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $admin) { throw 'Run this script in an elevated (administrator) PowerShell.' }
}

if (Test-Path $appKey) {
    foreach ($entry in Get-ChildItem $appKey) {
        if ($entry.GetValue('Path') -eq $file.FullName -and $PSCmdlet.ShouldProcess($entry.PSChildName, 'remove old allow-list entry')) {
            Remove-Item -LiteralPath $entry.PSPath -Recurse
        }
    }
}

$names = if (Test-Path $appKey) { @((Get-ChildItem $appKey).PSChildName) } else { @() }
$name = 'Entry'
for ($i = 1; $names -contains $name; $i++) { $name = "Entry ($i)" }
$entryKey = Join-Path $appKey $name

if ($PSCmdlet.ShouldProcess($entryKey, 'write allow-list entry')) {
    New-Item -Path $entryKey -Force | Out-Null
    New-ItemProperty -Path $entryKey -Name Path -Value $file.FullName -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $entryKey -Name DateModified -Value $modified -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $entryKey -Name FileHash -Value $hash -PropertyType String -Force | Out-Null
    Write-Output "allow-listed: $entryKey"
}
