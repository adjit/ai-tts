<#
.SYNOPSIS
  [DEPRECATED] Speak text via xAI TTS (Windows PowerShell).

.DESCRIPTION
  DEPRECATED — use the portable Python CLI instead:

    ai-tts speak "text"
    # or:  python -m ai_tts speak "text"

  This script is a Windows-only fallback. See docs/DEPRECATED_POWERSHELL.md.
  One-shot speaker used by the legacy direct (non-daemon) path.
#>
param(
    [Parameter(Mandatory = $true, ValueFromPipeline = $true)]
    [string]$Text,

    [string]$Voice = '',

    [string]$Language = '',

    [double]$Speed = 0,

    [ValidateSet('auto', 'stream', 'rest')]
    [string]$Transport = 'auto'
)

$ErrorActionPreference = 'Stop'
Write-Warning '[ai-tts] speak.ps1 is DEPRECATED. Prefer: ai-tts speak "..."  (see docs/DEPRECATED_POWERSHELL.md)'

$core = Join-Path $PSScriptRoot 'speak-core.ps1'
if (-not (Test-Path -LiteralPath $core)) {
    $core = Join-Path $env:USERPROFILE '.ai-tts\speak-core.ps1'
}
. $core

function Get-LocalConfig {
    $candidates = @(
        (Join-Path $env:USERPROFILE '.ai-tts\config.json'),
        (Join-Path $PSScriptRoot '..\config.json'),
        (Join-Path $PSScriptRoot 'config.json')
    )
    foreach ($p in $candidates) {
        if ($p -and (Test-Path -LiteralPath $p)) {
            try { return (Get-Content -LiteralPath $p -Raw | ConvertFrom-Json) } catch {}
        }
    }
    return $null
}

$cfg = Get-LocalConfig
if (-not $Voice) {
    if ($cfg -and $cfg.voice) { $Voice = [string]$cfg.voice } else { $Voice = 'carina' }
}
if (-not $Language) {
    if ($cfg -and $cfg.language) { $Language = [string]$cfg.language } else { $Language = 'en' }
}
if ($Speed -le 0) {
    if ($cfg -and $cfg.speed) { $Speed = [double]$cfg.speed } else { $Speed = 1.0 }
}

$opt = 2
$sr = 24000
if ($cfg -and $cfg.daemon) {
    if ($null -ne $cfg.daemon.optimizeStreamingLatency) { $opt = [int]$cfg.daemon.optimizeStreamingLatency }
    if ($null -ne $cfg.daemon.sampleRate) { $sr = [int]$cfg.daemon.sampleRate }
}

[void](Invoke-AiTtsSpeak -Text $Text -Voice $Voice -Language $Language -Speed $Speed `
    -OptimizeStreamingLatency $opt -SampleRate $sr -Transport $Transport)
