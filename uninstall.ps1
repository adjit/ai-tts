<#
.SYNOPSIS
  Remove ai-tts files from Grok Build and/or Claude Code.
  Does not rewrite Claude settings.json (hooks must be removed manually if merged).
#>
param(
    [ValidateSet('Grok', 'Claude', 'Both', 'Shared')]
    [string]$Target = 'Both',

    [switch]$RemoveConfig,
    [switch]$RemoveMarkers
)

$ErrorActionPreference = 'Stop'

function Remove-IfExists([string]$path) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Force -Recurse -ErrorAction SilentlyContinue
        Write-Host "  removed $path"
    }
}

if ($Target -eq 'Grok' -or $Target -eq 'Both') {
    Write-Host "Removing Grok files..."
    Remove-IfExists (Join-Path $env:USERPROFILE '.grok\hooks\tts.json')
    Remove-IfExists (Join-Path $env:USERPROFILE '.grok\hooks\tts-state.ps1')
    Remove-IfExists (Join-Path $env:USERPROFILE '.grok\hooks\tts-stop.ps1')
    Remove-IfExists (Join-Path $env:USERPROFILE '.grok\skills\tts')
    Remove-IfExists (Join-Path $env:USERPROFILE '.grok\rules\voice-tts.md')
    Remove-IfExists (Join-Path $env:USERPROFILE '.grok\speak.ps1')
    if ($RemoveMarkers) { Remove-IfExists (Join-Path $env:USERPROFILE '.grok\.tts-dirs') }
}

if ($Target -eq 'Claude' -or $Target -eq 'Both') {
    Write-Host "Removing Claude files..."
    Remove-IfExists (Join-Path $env:USERPROFILE '.claude\hooks\tts-state.ps1')
    Remove-IfExists (Join-Path $env:USERPROFILE '.claude\hooks\tts-stop.ps1')
    Remove-IfExists (Join-Path $env:USERPROFILE '.claude\skills\tts')
    Remove-IfExists (Join-Path $env:USERPROFILE '.claude\rules\voice-tts.md')
    Remove-IfExists (Join-Path $env:USERPROFILE '.claude\speak.ps1')
    if ($RemoveMarkers) { Remove-IfExists (Join-Path $env:USERPROFILE '.claude\.tts-dirs') }
    Write-Host "  Note: remove TTS entries from ~/.claude/settings.json manually if you merged them."
}

# Stop daemon if running
try {
    $stopScript = Join-Path $env:USERPROFILE '.ai-tts\scripts\daemon-stop.ps1'
    if (Test-Path $stopScript) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $stopScript -KeepDaemonMode 2>$null
    }
} catch {}

if ($Target -eq 'Shared' -or $Target -eq 'Both' -or $RemoveConfig) {
    Write-Host "Removing shared ~/.ai-tts ..."
    if ($RemoveConfig) {
        Remove-IfExists (Join-Path $env:USERPROFILE '.ai-tts')
    } else {
        Remove-IfExists (Join-Path $env:USERPROFILE '.ai-tts\speak.ps1')
        Remove-IfExists (Join-Path $env:USERPROFILE '.ai-tts\speak-core.ps1')
        Remove-IfExists (Join-Path $env:USERPROFILE '.ai-tts\common.ps1')
        Remove-IfExists (Join-Path $env:USERPROFILE '.ai-tts\daemon.ps1')
        Remove-IfExists (Join-Path $env:USERPROFILE '.ai-tts\scripts')
        Remove-IfExists (Join-Path $env:USERPROFILE '.ai-tts\daemon.pid')
        Remove-IfExists (Join-Path $env:USERPROFILE '.ai-tts\daemon.log')
        Remove-IfExists (Join-Path $env:USERPROFILE '.ai-tts\claude-settings.hooks.snippet.json')
        Write-Host "  kept config.json (pass -RemoveConfig to delete ~/.ai-tts entirely)"
    }
}

Write-Host "Done."
