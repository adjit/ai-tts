# Manual smoke tests (no agent harness required).
# Usage: .\examples\manual-smoke.ps1

$ErrorActionPreference = 'Stop'
$speak = Join-Path $env:USERPROFILE '.ai-tts\speak.ps1'
if (-not (Test-Path $speak)) {
    $speak = Join-Path $PSScriptRoot '..\src\speak.ps1'
}

Write-Host "1) Direct speak..." -ForegroundColor Cyan
& $speak -Text 'ai-tts smoke test. If you can hear this, the player works.' -Voice carina

Write-Host "2) SessionStart payload (Grok)..." -ForegroundColor Cyan
$state = Join-Path $env:USERPROFILE '.grok\hooks\tts-state.ps1'
if (Test-Path $state) {
    '{"cwd":"C:\\temp\\demo","sessionId":"smoke"}' | & powershell -NoProfile -ExecutionPolicy Bypass -File $state
    Write-Host ""
} else {
    Write-Host "  (Grok hooks not installed)"
}

Write-Host "Done." -ForegroundColor Green
