<#
.SYNOPSIS
  Speak text via xAI TTS (Grok voices), with Windows System.Speech fallback.

.DESCRIPTION
  One-shot speaker used by the direct (non-daemon) path. Prefer the optional
  daemon for lower latency between turns.
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
