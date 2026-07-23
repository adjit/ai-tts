<#
.SYNOPSIS
  Run unit tests locally (Windows) and optionally in Docker.
#>
param(
    [switch]$Docker,
    [switch]$Live,
    [switch]$Coverage
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if ($Docker) {
    Write-Host "-> Docker tests (Linux)"
    docker compose -f docker-compose.test.yml build
    if ($Live) {
        if (-not $env:XAI_API_KEY) { throw "XAI_API_KEY required for -Live" }
        docker compose -f docker-compose.test.yml run --rm `
            -e RUN_LIVE_TTS=1 -e "XAI_API_KEY=$env:XAI_API_KEY" `
            test pytest -q -m live
    } else {
        docker compose -f docker-compose.test.yml run --rm test
    }
    exit $LASTEXITCODE
}

Write-Host "-> Local pytest"
$env:PYTHONPATH = Join-Path $Root 'src\python'
python -m pip install -q -r requirements-dev.txt
$args = @('-q')
if (-not $Live) { $args += '--ignore=tests/test_live_optional.py' }
else { $args += @('-m', 'live') }
if ($Coverage) { $args = @('--cov=ai_tts', '--cov-report=term-missing') + $args }
python -m pytest @args
exit $LASTEXITCODE
