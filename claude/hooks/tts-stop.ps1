# Stop: when TTS is on for this directory, speak the last <say>...</say> (Claude Code).
# Reads transcript_path from the Stop hook payload.

$ErrorActionPreference = 'SilentlyContinue'

$common = Join-Path $env:USERPROFILE '.ai-tts\common.ps1'
if (-not (Test-Path $common)) {
    $common = Join-Path $PSScriptRoot '..\..\src\common.ps1'
}
if (Test-Path $common) { . $common }

$raw = [Console]::In.ReadToEnd()
if (-not $raw) { exit 0 }
try { $data = $raw | ConvertFrom-Json } catch { exit 0 }

$cwd = $data.cwd
if (-not $cwd) { $cwd = $env:CLAUDE_PROJECT_DIR }
if (-not $cwd) { exit 0 }

$enabled = $false
if (Get-Command Test-TtsEnabledForDir -ErrorAction SilentlyContinue) {
    $enabled = Test-TtsEnabledForDir $cwd 'claude'
} else {
    $norm = $cwd.TrimEnd('\', '/').ToLowerInvariant()
    $md5 = [System.Security.Cryptography.MD5]::Create()
    $key = ([System.BitConverter]::ToString($md5.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($norm)))).Replace('-', '').ToLower()
    $enabled = Test-Path (Join-Path $env:USERPROFILE (".claude\.tts-dirs\" + $key))
}
if (-not $enabled) { exit 0 }

$text = $null
if (Get-Command Get-LastAssistantText -ErrorAction SilentlyContinue) {
    $text = Get-LastAssistantText $data
} else {
    $tp = $data.transcript_path
    if ($tp -and (Test-Path -LiteralPath $tp)) {
        $lines = @(Get-Content -LiteralPath $tp)
        for ($i = $lines.Count - 1; $i -ge 0; $i--) {
            try { $obj = $lines[$i] | ConvertFrom-Json } catch { continue }
            if ($obj.type -eq 'assistant' -and $obj.message.content) {
                $sb = ''
                foreach ($blk in $obj.message.content) {
                    if ($blk.type -eq 'text') { $sb += $blk.text }
                }
                if ($sb) { $text = $sb; break }
            }
        }
    }
}
if (-not $text) { exit 0 }

$say = $null
if (Get-Command Get-LastSayBlock -ErrorAction SilentlyContinue) {
    $say = Get-LastSayBlock $text
} else {
    $found = [regex]::Matches($text, '(?s)<say>(.*?)</say>')
    if ($found.Count -gt 0) { $say = $found[$found.Count - 1].Groups[1].Value.Trim() }
}
if (-not $say) { exit 0 }

if (Get-Command Start-DetachedSpeak -ErrorAction SilentlyContinue) {
    Start-DetachedSpeak $say
} else {
    $tmp = Join-Path $env:TEMP ("ai-tts-say-{0}.txt" -f [guid]::NewGuid().ToString('N'))
    [System.IO.File]::WriteAllText($tmp, $say, (New-Object System.Text.UTF8Encoding($false)))
    $speak = Join-Path $env:USERPROFILE '.claude\speak.ps1'
    $cmd = "`$t=[System.IO.File]::ReadAllText('$tmp',[System.Text.Encoding]::UTF8); Remove-Item '$tmp' -ErrorAction SilentlyContinue; & '$speak' -Text `$t"
    Start-Process -FilePath 'powershell.exe' -WindowStyle Hidden `
        -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $cmd | Out-Null
}
exit 0
