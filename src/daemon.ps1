<#
.SYNOPSIS
  Optional warm TTS daemon for ai-tts (named pipe + streaming WebSocket).

.DESCRIPTION
  Keeps a PowerShell process alive so Stop hooks avoid cold-start cost.
  Reuses a WebSocket to xAI when possible for lower per-turn latency.

  Enable in ~/.ai-tts/config.json:
    "mode": "daemon"
    or "daemon": { "enabled": true }

  Start:
    powershell -NoProfile -ExecutionPolicy Bypass -File $env:USERPROFILE\.ai-tts\daemon.ps1

  Or:
    .\scripts\daemon-start.ps1

.NOTES
  Protocol (named pipe, one JSON line request / one JSON line response):
    -> {"text":"...","voice":"carina","language":"en","speed":1.0}
    <- {"ok":true,"ms":123}
#>
param(
    [string]$PipeName = '',
    [switch]$Foreground
)

$ErrorActionPreference = 'Stop'
$AiTtsHome = if ($env:AI_TTS_HOME) { $env:AI_TTS_HOME } else { Join-Path $env:USERPROFILE '.ai-tts' }

$core = Join-Path $AiTtsHome 'speak-core.ps1'
if (-not (Test-Path $core)) { $core = Join-Path $PSScriptRoot 'speak-core.ps1' }
. $core

function Read-Config {
    $p = Join-Path $AiTtsHome 'config.json'
    if (Test-Path $p) {
        try { return Get-Content -LiteralPath $p -Raw | ConvertFrom-Json } catch { return $null }
    }
    return $null
}

$cfg = Read-Config
if (-not $PipeName) {
    if ($cfg -and $cfg.daemon -and $cfg.daemon.pipeName) { $PipeName = [string]$cfg.daemon.pipeName }
    else { $PipeName = 'ai-tts' }
}

$defaultVoice = if ($cfg -and $cfg.voice) { [string]$cfg.voice } else { 'carina' }
$defaultLang = if ($cfg -and $cfg.language) { [string]$cfg.language } else { 'en' }
$defaultSpeed = if ($cfg -and $cfg.speed) { [double]$cfg.speed } else { 1.0 }
$optLat = 2
$sampleRate = 24000
if ($cfg -and $cfg.daemon) {
    if ($null -ne $cfg.daemon.optimizeStreamingLatency) { $optLat = [int]$cfg.daemon.optimizeStreamingLatency }
    if ($null -ne $cfg.daemon.sampleRate) { $sampleRate = [int]$cfg.daemon.sampleRate }
}

$pidFile = Join-Path $AiTtsHome 'daemon.pid'
$logFile = Join-Path $AiTtsHome 'daemon.log'

function Write-Log([string]$msg) {
    $line = "{0:o} {1}" -f (Get-Date).ToUniversalTime(), $msg
    Add-Content -LiteralPath $logFile -Value $line -ErrorAction SilentlyContinue
    if ($Foreground) { Write-Host $line }
}

# Single-instance guard via pid file (best-effort)
if (Test-Path $pidFile) {
    try {
        $oldPid = [int](Get-Content -LiteralPath $pidFile -Raw).Trim()
        $proc = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Log "Daemon already running (pid=$oldPid). Exiting."
            exit 0
        }
    } catch {}
}
Set-Content -LiteralPath $pidFile -Value $PID -Encoding ascii

$script:WarmSocket = $null

function Close-WarmSocket {
    if ($script:WarmSocket) {
        try {
            if ($script:WarmSocket.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
                $script:WarmSocket.CloseAsync(
                    [System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure,
                    'shutdown',
                    [Threading.CancellationToken]::None
                ).GetAwaiter().GetResult() | Out-Null
            }
        } catch {}
        try { $script:WarmSocket.Dispose() } catch {}
        $script:WarmSocket = $null
    }
}

function Handle-SpeakRequest($req) {
    $text = [string]$req.text
    if (-not $text) { throw 'missing text' }
    $voice = if ($req.voice) { [string]$req.voice } else { $defaultVoice }
    $lang = if ($req.language) { [string]$req.language } else { $defaultLang }
    $speed = if ($null -ne $req.speed -and [double]$req.speed -gt 0) { [double]$req.speed } else { $defaultSpeed }

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $script:WarmSocket = Invoke-AiTtsSpeak `
        -Text $text -Voice $voice -Language $lang -Speed $speed `
        -OptimizeStreamingLatency $optLat -SampleRate $sampleRate `
        -Transport auto `
        -ExistingSocket $script:WarmSocket `
        -KeepSocketOpen
    $sw.Stop()
    return @{ ok = $true; ms = $sw.ElapsedMilliseconds; voice = $voice }
}

Write-Log "ai-tts daemon starting pipe=\\.\pipe\$PipeName pid=$PID voice=$defaultVoice"

try {
    while ($true) {
        $server = New-Object System.IO.Pipes.NamedPipeServerStream(
            $PipeName,
            [System.IO.Pipes.PipeDirection]::InOut,
            1,
            [System.IO.Pipes.PipeTransmissionMode]::Byte,
            [System.IO.Pipes.PipeOptions]::Asynchronous
        )
        try {
            $server.WaitForConnection()
            $reader = New-Object System.IO.StreamReader($server, [Text.Encoding]::UTF8, $false, 1024, $true)
            $writer = New-Object System.IO.StreamWriter($server, [Text.Encoding]::UTF8, 1024, $true)
            $writer.AutoFlush = $true

            $line = $reader.ReadLine()
            if (-not $line) {
                $writer.WriteLine((@{ ok = $false; error = 'empty request' } | ConvertTo-Json -Compress))
                continue
            }

            if ($line.Trim() -eq '{"cmd":"ping"}' -or $line.Trim() -eq 'ping') {
                $writer.WriteLine((@{ ok = $true; pong = $true; pid = $PID } | ConvertTo-Json -Compress))
                continue
            }
            if ($line.Trim() -eq '{"cmd":"shutdown"}') {
                $writer.WriteLine((@{ ok = $true; shutdown = $true } | ConvertTo-Json -Compress))
                Write-Log 'Shutdown requested'
                break
            }

            try {
                $req = $line | ConvertFrom-Json
                $result = Handle-SpeakRequest $req
                $writer.WriteLine(($result | ConvertTo-Json -Compress))
                Write-Log ("spoke ms={0} chars={1}" -f $result.ms, $req.text.Length)
            }
            catch {
                Write-Log "error: $($_.Exception.Message)"
                Close-WarmSocket
                $writer.WriteLine((@{ ok = $false; error = $_.Exception.Message } | ConvertTo-Json -Compress))
            }
        }
        finally {
            try { $server.Disconnect() } catch {}
            $server.Dispose()
        }
    }
}
finally {
    Close-WarmSocket
    Remove-Item $pidFile -ErrorAction SilentlyContinue
    Write-Log 'ai-tts daemon stopped'
}
