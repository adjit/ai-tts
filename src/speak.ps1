<#
.SYNOPSIS
  Speak text via xAI TTS (Grok voices), with Windows System.Speech fallback.

.DESCRIPTION
  Used by Stop hooks for Grok Build and Claude Code. Do not call from the
  agent turn itself — hooks launch this detached so speech never blocks the model.

.PARAMETER Text
  Text to speak (plain language; avoid code and paths).

.PARAMETER Voice
  xAI voice_id. Default: carina (or config.json "voice").

.PARAMETER Language
  Language code (default en).

.PARAMETER Speed
  Playback speed 0.7–1.5 (default 1.0).
#>
param(
    [Parameter(Mandatory = $true, ValueFromPipeline = $true)]
    [string]$Text,

    [string]$Voice = '',

    [string]$Language = '',

    [double]$Speed = 0
)

$ErrorActionPreference = 'Stop'

function Get-AiTtsConfig {
    $candidates = @(
        (Join-Path $env:USERPROFILE '.ai-tts\config.json'),
        (Join-Path $PSScriptRoot '..\config.json'),
        (Join-Path $PSScriptRoot 'config.json')
    )
    foreach ($p in $candidates) {
        if ($p -and (Test-Path -LiteralPath $p)) {
            try {
                return (Get-Content -LiteralPath $p -Raw | ConvertFrom-Json)
            } catch {
                # ignore bad config
            }
        }
    }
    return $null
}

$cfg = Get-AiTtsConfig
if (-not $Voice) {
    if ($cfg -and $cfg.voice) { $Voice = [string]$cfg.voice } else { $Voice = 'carina' }
}
if (-not $Language) {
    if ($cfg -and $cfg.language) { $Language = [string]$cfg.language } else { $Language = 'en' }
}
if ($Speed -le 0) {
    if ($cfg -and $cfg.speed) { $Speed = [double]$cfg.speed } else { $Speed = 1.0 }
}

# winmm playback — SoundPlayer.PlaySync is often silent when launched from
# agent harnesses; mciSendString routes reliably to the audio device.
if (-not ('Native.WinMM' -as [type])) {
    Add-Type -Name WinMM -Namespace Native -MemberDefinition @'
[DllImport("winmm.dll", CharSet = CharSet.Auto)]
public static extern int mciSendString(string command, System.Text.StringBuilder buffer, int bufferSize, System.IntPtr hwndCallback);
'@
}

function Play-Wav([string]$path) {
    $alias = "aitts$PID"
    [void][Native.WinMM]::mciSendString("open `"$path`" type waveaudio alias $alias", $null, 0, [IntPtr]::Zero)
    [void][Native.WinMM]::mciSendString("play $alias wait", $null, 0, [IntPtr]::Zero)
    [void][Native.WinMM]::mciSendString("close $alias", $null, 0, [IntPtr]::Zero)
}

function Invoke-Fallback([string]$t) {
    Add-Type -AssemblyName System.Speech
    $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $s.Rate = 1
    $s.Volume = 100
    $s.Speak($t)
}

$key = $env:XAI_API_KEY
if (-not $key) { $key = [System.Environment]::GetEnvironmentVariable('XAI_API_KEY', 'User') }
if (-not $key) {
    Write-Warning 'XAI_API_KEY not set; using built-in System.Speech.'
    Invoke-Fallback $Text
    return
}

$wav = [System.IO.Path]::Combine($env:TEMP, "ai-tts-$PID.wav")
try {
    $body = @{
        text          = $Text
        voice_id      = $Voice
        language      = $Language
        speed         = $Speed
        output_format = @{ codec = 'wav' }
    } | ConvertTo-Json -Depth 5

    Invoke-WebRequest -Uri 'https://api.x.ai/v1/tts' `
        -Method Post `
        -Headers @{ Authorization = "Bearer $key" } `
        -ContentType 'application/json' `
        -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
        -OutFile $wav `
        -UseBasicParsing | Out-Null

    if (-not (Test-Path $wav) -or (Get-Item $wav).Length -eq 0) {
        throw 'xAI returned no audio.'
    }

    Play-Wav $wav
}
catch {
    Write-Warning "xAI TTS failed ($($_.Exception.Message)); using built-in System.Speech."
    Invoke-Fallback $Text
}
finally {
    Remove-Item $wav -ErrorAction SilentlyContinue
}
