<#
.SYNOPSIS
  Start the optional ai-tts daemon in the background (Windows).

  Default: portable Python TCP daemon (recommended).
  -LegacyNamedPipe: [DEPRECATED] Windows named-pipe PowerShell daemon.
  See docs/DEPRECATED_POWERSHELL.md
#>
param(
    [switch]$Foreground,
    [switch]$LegacyNamedPipe
)

$ErrorActionPreference = 'Stop'
$homeDir = if ($env:AI_TTS_HOME) { $env:AI_TTS_HOME } else { Join-Path $env:USERPROFILE '.ai-tts' }
$pyCmd = Join-Path $homeDir 'bin\ai-tts.cmd'

if ($LegacyNamedPipe) {
    Write-Warning '[ai-tts] -LegacyNamedPipe is DEPRECATED. Prefer Python: ai-tts daemon --enable-config'
}

# Prefer Python TCP daemon
if (-not $LegacyNamedPipe -and (Test-Path -LiteralPath $pyCmd)) {
    if ($Foreground) {
        & $pyCmd daemon --enable-config
        exit $LASTEXITCODE
    }
    $p = Start-Process -FilePath $pyCmd -WindowStyle Hidden -PassThru `
        -ArgumentList @('daemon', '--enable-config')
    Start-Sleep -Milliseconds 500
    Write-Host "Started Python TCP daemon pid=$($p.Id) (127.0.0.1:18765)"
    Write-Host "  stop:  $pyCmd daemon-stop"
    exit 0
}

$daemon = Join-Path $homeDir 'daemon.ps1'
if (-not (Test-Path $daemon)) {
    $daemon = Join-Path $PSScriptRoot '..\src\daemon.ps1'
}
if (-not (Test-Path $daemon)) { throw "No Python launcher or daemon.ps1. Run install.ps1 first." }

$cfgPath = Join-Path $homeDir 'config.json'
if (Test-Path $cfgPath) {
    try {
        $cfg = Get-Content -LiteralPath $cfgPath -Raw | ConvertFrom-Json
        $cfg.mode = 'daemon'
        $d = @{
            enabled                   = $true
            pipeName                  = if ($cfg.daemon.pipeName) { $cfg.daemon.pipeName } else { 'ai-tts' }
            host                      = if ($cfg.daemon.host) { $cfg.daemon.host } else { '127.0.0.1' }
            port                      = if ($null -ne $cfg.daemon.port) { [int]$cfg.daemon.port } else { 18765 }
            autoStart                 = if ($null -ne $cfg.daemon.autoStart) { [bool]$cfg.daemon.autoStart } else { $false }
            optimizeStreamingLatency  = if ($null -ne $cfg.daemon.optimizeStreamingLatency) { [int]$cfg.daemon.optimizeStreamingLatency } else { 2 }
            sampleRate                = if ($null -ne $cfg.daemon.sampleRate) { [int]$cfg.daemon.sampleRate } else { 24000 }
        }
        $cfg.daemon = [pscustomobject]$d
        ($cfg | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $cfgPath -Encoding UTF8
    } catch {
        Write-Warning "Could not update config.json: $($_.Exception.Message)"
    }
}

if ($Foreground) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $daemon -Foreground
    exit $LASTEXITCODE
}

$p = Start-Process -FilePath 'powershell.exe' -WindowStyle Hidden -PassThru `
    -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $daemon)
Start-Sleep -Milliseconds 400
Write-Host "Started legacy named-pipe daemon pid=$($p.Id)"
Write-Host "  stop:   .\scripts\daemon-stop.ps1 - or prefer Python: ai-tts daemon-stop"
