# install.ps1 — link this skill into Claude Code's user skills folder.
#
# Run from any PowerShell. If the symlink fails (no admin rights, FS doesn't
# support symlinks), it falls back to a directory copy. Re-running will
# refresh the link / copy.
#
# Usage:
#   .\install.ps1            # symlink (recommended)
#   .\install.ps1 -Copy      # copy instead of symlinking

param(
    [switch]$Copy
)

$ErrorActionPreference = 'Stop'

$Source = $PSScriptRoot
$SkillsRoot = Join-Path $env:USERPROFILE ".claude\skills"
$Target = Join-Path $SkillsRoot "deploy-coding-agents"

if (-not (Test-Path $SkillsRoot)) {
    New-Item -ItemType Directory -Path $SkillsRoot -Force | Out-Null
}

if (Test-Path $Target) {
    Write-Host "Removing existing $Target"
    Remove-Item -Recurse -Force $Target
}

if ($Copy) {
    Write-Host "Copying $Source -> $Target"
    Copy-Item -Path $Source -Destination $Target -Recurse
    Write-Host "Done. Note: edits in $Source will NOT auto-propagate to the installed skill. Re-run install.ps1 to refresh."
} else {
    try {
        New-Item -ItemType SymbolicLink -Path $Target -Target $Source -ErrorAction Stop | Out-Null
        Write-Host "Symlinked $Target -> $Source"
        Write-Host "Edits in $Source will be picked up immediately by the next Claude Code session."
    } catch {
        Write-Warning "Symlink failed (admin rights required for non-developer-mode Windows). Falling back to copy."
        Write-Warning "Original error: $_"
        Copy-Item -Path $Source -Destination $Target -Recurse
        Write-Host "Copied $Source -> $Target"
        Write-Host "Note: edits in $Source will NOT auto-propagate. Re-run install.ps1 to refresh, or enable Developer Mode in Windows and re-run for symlink support."
    }
}
