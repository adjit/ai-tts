<#
.SYNOPSIS
  Stop the ai-tts daemon and switch config back to direct mode (optional).
#>
param(
    [switch]$KeepDaemonMode
)

$ErrorActionPreference = 'SilentlyContinue'
$homeDir = if ($env:AI_TTS_HOME) { $env:AI_TTS_HOME } else { Join-Path $env:USERPROFILE '.ai-tts' }
$pipeName = 'ai-tts'
$cfgPath = Join-Path $homeDir 'config.json'
if (Test-Path $cfgPath) {
    try {
        $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
        if ($cfg.daemon -and $cfg.daemon.pipeName) { $pipeName = [string]$cfg.daemon.pipeName }
    } catch {}
}

# Prefer graceful shutdown over the pipe
try {
    $client = New-Object System.IO.Pipes.NamedPipeClientStream('.', $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
    $client.Connect(500)
    $w = New-Object System.IO.StreamWriter($client, [Text.Encoding]::UTF8, 1024, $true)
    $r = New-Object System.IO.StreamReader($client, [Text.Encoding]::UTF8, $false, 1024, $true)
    $w.AutoFlush = $true
    $w.WriteLine('{"cmd":"shutdown"}')
    [void]$r.ReadLine()
    $client.Dispose()
    Write-Host 'Sent shutdown to daemon.'
} catch {
    $pidFile = Join-Path $homeDir 'daemon.pid'
    if (Test-Path $pidFile) {
        $old = 0
        try { $old = [int](Get-Content $pidFile -Raw).Trim() } catch {}
        if ($old) {
            Stop-Process -Id $old -Force -ErrorAction SilentlyContinue
            Write-Host "Killed daemon pid=$old"
        }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host 'Daemon not running (or pipe busy).'
    }
}

if (-not $KeepDaemonMode -and (Test-Path $cfgPath)) {
    try {
        $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
        $cfg.mode = 'direct'
        if ($cfg.daemon) {
            $cfg.daemon = [pscustomobject]@{
                enabled                   = $false
                pipeName                  = if ($cfg.daemon.pipeName) { $cfg.daemon.pipeName } else { 'ai-tts' }
                autoStart                 = [bool]$cfg.daemon.autoStart
                optimizeStreamingLatency  = if ($null -ne $cfg.daemon.optimizeStreamingLatency) { [int]$cfg.daemon.optimizeStreamingLatency } else { 2 }
                sampleRate                = if ($null -ne $cfg.daemon.sampleRate) { [int]$cfg.daemon.sampleRate } else { 24000 }
            }
        }
        ($cfg | ConvertTo-Json -Depth 6) | Set-Content $cfgPath -Encoding UTF8
        Write-Host 'Config set to mode=direct (daemon disabled).'
    } catch {}
}
