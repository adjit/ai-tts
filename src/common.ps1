# Shared helpers for ai-tts hooks (dot-sourced by harness-specific scripts).

function Get-AiTtsHome {
    if ($env:AI_TTS_HOME) { return $env:AI_TTS_HOME }
    return (Join-Path $env:USERPROFILE '.ai-tts')
}

function Get-AiTtsConfig {
    $cfgPath = Join-Path (Get-AiTtsHome) 'config.json'
    if (Test-Path -LiteralPath $cfgPath) {
        try { return (Get-Content -LiteralPath $cfgPath -Raw | ConvertFrom-Json) } catch { return $null }
    }
    return $null
}

function Get-AiTtsVoice {
    $cfg = Get-AiTtsConfig
    if ($cfg -and $cfg.voice) { return [string]$cfg.voice }
    return 'carina'
}

function Get-AiTtsLanguage {
    $cfg = Get-AiTtsConfig
    if ($cfg -and $cfg.language) { return [string]$cfg.language }
    return 'en'
}

function Get-AiTtsSpeed {
    $cfg = Get-AiTtsConfig
    if ($cfg -and $cfg.speed) { return [double]$cfg.speed }
    return 1.0
}

function Test-AiTtsDaemonEnabled {
    $cfg = Get-AiTtsConfig
    if (-not $cfg) { return $false }
    if ($cfg.mode -and ([string]$cfg.mode).ToLowerInvariant() -eq 'daemon') { return $true }
    if ($cfg.daemon -and $cfg.daemon.enabled) { return [bool]$cfg.daemon.enabled }
    return $false
}

function Get-AiTtsPipeName {
    $cfg = Get-AiTtsConfig
    if ($cfg -and $cfg.daemon -and $cfg.daemon.pipeName) { return [string]$cfg.daemon.pipeName }
    return 'ai-tts'
}

function Get-AiTtsDaemonHost {
    $cfg = Get-AiTtsConfig
    if ($cfg -and $cfg.daemon -and $cfg.daemon.host) { return [string]$cfg.daemon.host }
    return '127.0.0.1'
}

function Get-AiTtsDaemonPort {
    $cfg = Get-AiTtsConfig
    if ($cfg -and $cfg.daemon -and $null -ne $cfg.daemon.port) { return [int]$cfg.daemon.port }
    return 18765
}

function Test-AiTtsPythonAvailable {
    $cmd = Join-Path (Get-AiTtsHome) 'bin\ai-tts.cmd'
    return (Test-Path -LiteralPath $cmd)
}

function Test-AiTtsDaemonAutoStart {
    $cfg = Get-AiTtsConfig
    if ($cfg -and $cfg.daemon -and $null -ne $cfg.daemon.autoStart) {
        return [bool]$cfg.daemon.autoStart
    }
    return $false
}

function Get-AiTtsSpeakPath {
    $homeSpeak = Join-Path (Get-AiTtsHome) 'speak.ps1'
    if (Test-Path -LiteralPath $homeSpeak) { return $homeSpeak }
    foreach ($p in @(
        (Join-Path $env:USERPROFILE '.grok\speak.ps1'),
        (Join-Path $env:USERPROFILE '.claude\speak.ps1')
    )) {
        if (Test-Path -LiteralPath $p) { return $p }
    }
    return $homeSpeak
}

function Get-AiTtsDaemonPath {
    $p = Join-Path (Get-AiTtsHome) 'daemon.ps1'
    if (Test-Path -LiteralPath $p) { return $p }
    return $p
}

function Get-NormalizedCwd([string]$cwd) {
    if (-not $cwd) { return $null }
    return $cwd.TrimEnd('\', '/').ToLowerInvariant()
}

function Get-DirMarkerKey([string]$cwd) {
    $norm = Get-NormalizedCwd $cwd
    if (-not $norm) { return $null }
    $md5 = [System.Security.Cryptography.MD5]::Create()
    return ([System.BitConverter]::ToString(
        $md5.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($norm))
    )).Replace('-', '').ToLower()
}

function Test-TtsEnabledForDir([string]$cwd, [string]$harness) {
    $key = Get-DirMarkerKey $cwd
    if (-not $key) { return $false }
    $markerRoot = Join-Path $env:USERPROFILE (".$harness\.tts-dirs")
    return (Test-Path -LiteralPath (Join-Path $markerRoot $key))
}

function Get-CwdFromHookInput($data) {
    if (-not $data) { return $null }
    $cwd = $data.cwd
    if (-not $cwd) { $cwd = $data.workspaceRoot }
    if (-not $cwd) { $cwd = $data.workspace_root }
    if (-not $cwd) { $cwd = $env:GROK_WORKSPACE_ROOT }
    if (-not $cwd) { $cwd = $env:CLAUDE_PROJECT_DIR }
    return $cwd
}

function Get-LastAssistantText($data) {
    $text = $data.lastAssistantMessage
    if (-not $text) { $text = $data.last_assistant_message }
    if ($text) { return $text }

    $tp = $data.transcript_path
    if (-not $tp) { $tp = $data.transcriptPath }
    if (-not $tp -or -not (Test-Path -LiteralPath $tp)) { return $null }

    $lines = @(Get-Content -LiteralPath $tp)
    for ($i = $lines.Count - 1; $i -ge 0; $i--) {
        try { $obj = $lines[$i] | ConvertFrom-Json } catch { continue }
        if ($obj.type -eq 'assistant' -and $obj.message.content) {
            $sb = ''
            foreach ($blk in $obj.message.content) {
                if ($blk.type -eq 'text') { $sb += $blk.text }
            }
            if ($sb) { return $sb }
        }
    }
    return $null
}

function Get-LastSayBlock([string]$text) {
    if (-not $text) { return $null }
    $found = [regex]::Matches($text, '(?s)<say>(.*?)</say>')
    if ($found.Count -eq 0) { return $null }
    $say = $found[$found.Count - 1].Groups[1].Value.Trim()
    if (-not $say) { return $null }
    return $say
}

function Start-DetachedSpeak([string]$say) {
    $tmp = Join-Path $env:TEMP ("ai-tts-say-{0}.txt" -f [guid]::NewGuid().ToString('N'))
    [System.IO.File]::WriteAllText($tmp, $say, (New-Object System.Text.UTF8Encoding($false)))
    $speak = Get-AiTtsSpeakPath
    $voice = Get-AiTtsVoice
    # -File is faster/cleaner than -Command string rebuild
    $arg = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', $speak,
        '-Text', $say,
        '-Voice', $voice
    )
    # Prefer -File with text arg; if path issues, fall back to temp file loader
    try {
        Start-Process -FilePath 'powershell.exe' -WindowStyle Hidden -ArgumentList $arg | Out-Null
    } catch {
        $cmd = "`$t=[System.IO.File]::ReadAllText('$tmp',[System.Text.Encoding]::UTF8); Remove-Item '$tmp' -ErrorAction SilentlyContinue; & '$speak' -Text `$t -Voice '$voice'"
        Start-Process -FilePath 'powershell.exe' -WindowStyle Hidden `
            -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $cmd | Out-Null
        return
    }
    # cleanup temp if unused
    Remove-Item $tmp -ErrorAction SilentlyContinue
}

function Send-AiTtsTcpDaemonSpeak([string]$say) {
    $hostName = Get-AiTtsDaemonHost
    $port = Get-AiTtsDaemonPort
    $payload = (@{
        text     = $say
        voice    = Get-AiTtsVoice
        language = Get-AiTtsLanguage
        speed    = Get-AiTtsSpeed
    } | ConvertTo-Json -Compress) + "`n"
    $bytes = [Text.Encoding]::UTF8.GetBytes($payload)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $iar = $client.BeginConnect($hostName, $port, $null, $null)
        if (-not $iar.AsyncWaitHandle.WaitOne(800)) { throw 'tcp connect timeout' }
        $client.EndConnect($iar)
        $stream = $client.GetStream()
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush()
        $reader = New-Object System.IO.StreamReader($stream, [Text.Encoding]::UTF8)
        $respLine = $reader.ReadLine()
        if (-not $respLine) { throw 'daemon empty response' }
        $resp = $respLine | ConvertFrom-Json
        if (-not $resp.ok) { throw "daemon error: $($resp.error)" }
        return $true
    }
    finally {
        try { $client.Close() } catch {}
    }
}

function Send-AiTtsNamedPipeSpeak([string]$say) {
    $pipeName = Get-AiTtsPipeName
    $payload = @{
        text     = $say
        voice    = Get-AiTtsVoice
        language = Get-AiTtsLanguage
        speed    = Get-AiTtsSpeed
    } | ConvertTo-Json -Compress

    $client = $null
    try {
        $client = New-Object System.IO.Pipes.NamedPipeClientStream(
            '.', $pipeName, [System.IO.Pipes.PipeDirection]::InOut,
            [System.IO.Pipes.PipeOptions]::None
        )
        $client.Connect(400)
        $writer = New-Object System.IO.StreamWriter($client, [Text.Encoding]::UTF8, 1024, $true)
        $reader = New-Object System.IO.StreamReader($client, [Text.Encoding]::UTF8, $false, 1024, $true)
        $writer.AutoFlush = $true
        $writer.WriteLine($payload)
        $respLine = $reader.ReadLine()
        if (-not $respLine) { throw 'daemon empty response' }
        $resp = $respLine | ConvertFrom-Json
        if (-not $resp.ok) { throw "daemon error: $($resp.error)" }
        return $true
    }
    finally {
        if ($client) { try { $client.Dispose() } catch {} }
    }
}

function Send-AiTtsDaemonSpeak([string]$say) {
    # Prefer portable TCP daemon (Python); fall back to legacy Windows named pipe.
    try {
        return (Send-AiTtsTcpDaemonSpeak $say)
    } catch {
        return (Send-AiTtsNamedPipeSpeak $say)
    }
}

function Start-AiTtsDaemonProcess {
    $daemon = Get-AiTtsDaemonPath
    if (-not (Test-Path -LiteralPath $daemon)) { return $false }
    Start-Process -FilePath 'powershell.exe' -WindowStyle Hidden `
        -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $daemon) | Out-Null
    # Wait briefly for the pipe to appear
    $pipeName = Get-AiTtsPipeName
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 150
        try {
            $c = New-Object System.IO.Pipes.NamedPipeClientStream('.', $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
            $c.Connect(100)
            $w = New-Object System.IO.StreamWriter($c, [Text.Encoding]::UTF8, 1024, $true)
            $r = New-Object System.IO.StreamReader($c, [Text.Encoding]::UTF8, $false, 1024, $true)
            $w.AutoFlush = $true
            $w.WriteLine('{"cmd":"ping"}')
            $line = $r.ReadLine()
            $c.Dispose()
            if ($line -and $line -match 'pong|ok') { return $true }
        } catch {}
    }
    return $false
}

function Invoke-AiTtsSpeakRequest([string]$say) {
    if (-not $say) { return }

    # Prefer Python launcher when installed (handles daemon + direct internally).
    $pyCmd = Join-Path (Get-AiTtsHome) 'bin\ai-tts.cmd'
    if (Test-Path -LiteralPath $pyCmd) {
        try {
            Start-Process -FilePath $pyCmd -WindowStyle Hidden -ArgumentList @('speak', '--', $say) | Out-Null
            return
        } catch {}
    }

    if (Test-AiTtsDaemonEnabled) {
        try {
            [void](Send-AiTtsDaemonSpeak $say)
            return
        } catch {
            if (Test-AiTtsDaemonAutoStart) {
                try {
                    if (Start-AiTtsDaemonProcess) {
                        [void](Send-AiTtsDaemonSpeak $say)
                        return
                    }
                } catch {}
            }
        }
    }

    Start-DetachedSpeak $say
}
