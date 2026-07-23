# [DEPRECATED] SessionStart for Claude Code (PowerShell).
# Prefer: ai-tts hook-state --harness claude
# See docs/DEPRECATED_POWERSHELL.md
# Marker: ~/.claude/.tts-dirs/<md5(cwd)>

$ErrorActionPreference = 'SilentlyContinue'

$common = Join-Path $env:USERPROFILE '.ai-tts\common.ps1'
if (-not (Test-Path $common)) {
    $common = Join-Path $PSScriptRoot '..\..\src\common.ps1'
}
if (Test-Path $common) { . $common }

$raw = [Console]::In.ReadToEnd()
$data = $null
if ($raw) { try { $data = $raw | ConvertFrom-Json } catch {} }

$cwd = $null
if ($data) { $cwd = $data.cwd }
if (-not $cwd) { $cwd = $env:CLAUDE_PROJECT_DIR }

$voice = 'carina'
if (Get-Command Get-AiTtsVoice -ErrorAction SilentlyContinue) { $voice = Get-AiTtsVoice }

$on = $false
if ($cwd -and (Get-Command Test-TtsEnabledForDir -ErrorAction SilentlyContinue)) {
    $on = Test-TtsEnabledForDir $cwd 'claude'
} elseif ($cwd) {
    $norm = $cwd.TrimEnd('\', '/').ToLowerInvariant()
    $md5 = [System.Security.Cryptography.MD5]::Create()
    $key = ([System.BitConverter]::ToString($md5.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($norm)))).Replace('-', '').ToLower()
    $on = Test-Path (Join-Path $env:USERPROFILE (".claude\.tts-dirs\" + $key))
}

if ($on) {
    Write-Output "[tts] Voice output is ON for this directory (voice: $voice). End each response with a concise <say>one to two sentence spoken summary</say> line - plain spoken language only (no code, paths, markdown). A Stop hook speaks it asynchronously via xAI; do NOT call speak.ps1 yourself. Run /tts to turn it off for this directory."
} else {
    Write-Output "[tts] Voice output is OFF (default) for this directory. Do not emit <say> markers. Run /tts to enable voice for this directory."
}
