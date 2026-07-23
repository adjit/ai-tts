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

function Get-AiTtsSpeakPath {
    $homeSpeak = Join-Path (Get-AiTtsHome) 'speak.ps1'
    if (Test-Path -LiteralPath $homeSpeak) { return $homeSpeak }
    # Fallbacks after install into harness dirs
    foreach ($p in @(
        (Join-Path $env:USERPROFILE '.grok\speak.ps1'),
        (Join-Path $env:USERPROFILE '.claude\speak.ps1')
    )) {
        if (Test-Path -LiteralPath $p) { return $p }
    }
    return $homeSpeak
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
    $cmd = "`$t=[System.IO.File]::ReadAllText('$tmp',[System.Text.Encoding]::UTF8); Remove-Item '$tmp' -ErrorAction SilentlyContinue; & '$speak' -Text `$t -Voice '$voice'"
    Start-Process -FilePath 'powershell.exe' -WindowStyle Hidden `
        -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $cmd | Out-Null
}
