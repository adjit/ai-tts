# DEPRECATED — use the Python product smoke instead:
#
#   .\scripts\smoke.ps1
#   .\scripts\smoke.ps1 -Speak          # requires XAI_API_KEY
#
# Or on macOS/Linux:
#
#   ./scripts/smoke.sh
#   ./scripts/smoke.sh --speak
#
# This file previously called deprecated speak.ps1 / PowerShell hooks.
# Kept as a pointer so old links do not break silently.

$ErrorActionPreference = 'Stop'
$smoke = Join-Path $PSScriptRoot '..\scripts\smoke.ps1'
if (-not (Test-Path -LiteralPath $smoke)) {
    throw "Missing $smoke — run from the ai-tts repo checkout."
}
Write-Host 'examples/manual-smoke.ps1 is deprecated; forwarding to scripts/smoke.ps1' -ForegroundColor Yellow
& $smoke @args
exit $LASTEXITCODE
