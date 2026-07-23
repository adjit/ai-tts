<#
.SYNOPSIS
  Start the optional ai-tts daemon in the background (Windows).
#>
param(
    [switch]$Foreground
)

$ErrorActionPreference = 'Stop'
$homeDir = if ($env:AI_TTS_HOME) { $env:AI_TTS_HOME } else { Join-Path $env:USERPROFILE '.ai-tts' }
$daemon = Join-Path $homeDir 'daemon.ps1'
if (-not (Test-Path $daemon)) {
    $daemon = Join-Path $PSScriptRoot '..\src\daemon.ps1'
}
if (-not (Test-Path $daemon)) { throw "daemon.ps1 not found. Run install.ps1 first." }

# Ensure config prefers daemon mode (do not force if user set enabled false explicitly with mode direct only — we enable on start)
$cfgPath = Join-Path $homeDir 'config.json'
if (Test-Path $cfgPath) {
    try {
        $cfg = Get-Content -LiteralPath $cfgPath -Raw | ConvertFrom-Json
        if (-not $cfg.daemon) { $cfg | Add-Member -NotePropertyName daemon -NotePropertyValue ([pscustomobject]@{}) -Force }
        # Reflect that user started the daemon; enable flag true
        $cfg.mode = 'daemon'
        $d = @{
            enabled                   = $true
            pipeName                  = if ($cfg.daemon.pipeName) { $cfg.daemon.pipeName } else { 'ai-tts' }
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

$pidFile = Join-Path $homeDir 'daemon.pid'
if (Test-Path $pidFile) {
    $old = 0
    try { $old = [int](Get-Content $pidFile -Raw).Trim() } catch {}
    if ($old -and (Get-Process -Id $old -ErrorAction SilentlyContinue)) {
        Write-Host "Daemon already running (pid=$old)"
        exit 0
    }
}

if ($Foreground) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $daemon -Foreground
    exit $LASTEXITCODE
}

$p = Start-Process -FilePath 'powershell.exe' -WindowStyle Hidden -PassThru `
    -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $daemon)
Start-Sleep -Milliseconds 400
Write-Host "Started ai-tts daemon pid=$($p.Id)"
Write-Host "  config: mode=daemon (warm pipe + streaming TTS)"
Write-Host "  stop:   .\scripts\daemon-stop.ps1"
