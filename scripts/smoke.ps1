<#
.SYNOPSIS
  Product smoke: probe + hook-state + optional speak (Python runtime).
.DESCRIPTION
  Replaces examples/manual-smoke.ps1 (deprecated PowerShell speak path).
.PARAMETER Speak
  Require a live speak call (fails if XAI_API_KEY is missing).
.PARAMETER SkipSpeak
  Never call speak.
#>
param(
    [switch]$Speak,
    [switch]$SkipSpeak
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Resolve-AiTts {
    if ($env:AI_TTS_BIN -and (Test-Path -LiteralPath $env:AI_TTS_BIN)) {
        return @{ Kind = 'exe'; Path = $env:AI_TTS_BIN }
    }
    $installed = Join-Path $env:USERPROFILE '.ai-tts\bin\ai-tts.cmd'
    if (Test-Path -LiteralPath $installed) {
        return @{ Kind = 'exe'; Path = $installed }
    }
    $cmd = Get-Command ai-tts -ErrorAction SilentlyContinue
    if ($cmd) {
        return @{ Kind = 'exe'; Path = $cmd.Source }
    }
    $env:PYTHONPATH = (Join-Path $Root 'src\python') + $(if ($env:PYTHONPATH) { ";$env:PYTHONPATH" } else { '' })
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
    if (-not $py) { throw 'ai-tts not found (install or set AI_TTS_BIN / PYTHONPATH)' }
    return @{ Kind = 'module'; Python = $py.Source }
}

function Invoke-AiTts {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $r = Resolve-AiTts
    if ($r.Kind -eq 'exe') {
        & $r.Path @Args
    } else {
        & $r.Python -m ai_tts @Args
    }
    if ($LASTEXITCODE -ne 0) { throw "ai-tts $($Args -join ' ') failed (exit $LASTEXITCODE)" }
}

Write-Host '==> ai-tts product smoke' -ForegroundColor Cyan
Write-Host ''

Write-Host '-> probe'
Invoke-AiTts probe
Write-Host ''

Write-Host "-> hook-state (cwd=$PWD, harness=grok)"
$payload = (@{ cwd = (Get-Location).Path; sessionId = 'smoke' } | ConvertTo-Json -Compress)
$payload | Invoke-AiTts hook-state --harness grok
Write-Host ''

$keySet = [bool]$env:XAI_API_KEY
if ($SkipSpeak) {
    Write-Host '-> speak: skipped (-SkipSpeak)'
} elseif ($keySet) {
    Write-Host '-> speak (REST)'
    Invoke-AiTts speak --transport rest 'ai-tts smoke. If you can hear this, playback works.'
} elseif ($Speak) {
    throw '--Speak requires XAI_API_KEY'
} else {
    Write-Host '-> speak: skipped (XAI_API_KEY not set; set it or pass -Speak to require)'
}

Write-Host ''
Write-Host 'OK smoke complete.' -ForegroundColor Green
Write-Host 'Next: live agent E2E is still manual — /tts in a project, then confirm <say> audio.'
