<#
.SYNOPSIS
  Install ai-tts into Grok Build and/or Claude Code (Windows).

.DESCRIPTION
  Installs the portable Python runtime (primary). PowerShell helpers are
  DEPRECATED and only installed as a Windows fallback / opt-in legacy hooks.

.EXAMPLE
  .\install.ps1
  .\install.ps1 -Target Both -Voice carina -MergeClaudeSettings
  .\install.ps1 -EnableDaemon -Force
  .\install.ps1 -LegacyPowerShellHooks   # DEPRECATED - PS hooks instead of Python
#>
param(
    [ValidateSet('Grok', 'Claude', 'Both')]
    [string]$Target = 'Grok',

    [string]$Voice = 'carina',
    [string]$Language = 'en',
    [double]$Speed = 1.0,

    [switch]$MergeClaudeSettings,
    [switch]$Force,
    [switch]$EnableDaemon,
    [switch]$AutoStartDaemon,

    # DEPRECATED: Windows PowerShell hooks. Prefer Python (default).
    [switch]$LegacyPowerShellHooks,

    [string]$Python = ''
)

$ErrorActionPreference = 'Stop'
$RepoRoot = $PSScriptRoot
$AiTtsHome = Join-Path $env:USERPROFILE '.ai-tts'
$GrokHome = Join-Path $env:USERPROFILE '.grok'
$ClaudeHome = Join-Path $env:USERPROFILE '.claude'

function Write-Step($msg) { Write-Host "-> $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "  OK $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "  ! $msg" -ForegroundColor Yellow }

function Ensure-Dir([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

function Copy-FileForced([string]$src, [string]$dst) {
    Ensure-Dir (Split-Path -Parent $dst)
    Copy-Item -LiteralPath $src -Destination $dst -Force
}

function Resolve-Python {
    if ($Python) { return $Python }
    foreach ($c in @('python', 'py', 'python3')) {
        $cmd = Get-Command $c -ErrorAction SilentlyContinue
        if ($cmd) {
            if ($c -eq 'py') { return 'py -3' }
            return $cmd.Source
        }
    }
    return $null
}

function Invoke-Python([string]$py, [string[]]$pyArgs) {
    if ($py -eq 'py -3') {
        & py -3 @pyArgs
    } else {
        & $py @pyArgs
    }
}

function Install-Shared {
    Write-Step "Installing shared runtime to $AiTtsHome"
    Ensure-Dir $AiTtsHome
    Ensure-Dir (Join-Path $AiTtsHome 'bin')
    Ensure-Dir (Join-Path $AiTtsHome 'lib')
    Ensure-Dir (Join-Path $AiTtsHome 'scripts')
    Ensure-Dir (Join-Path $AiTtsHome 'docs')

    if ($LegacyPowerShellHooks) {
        Write-Warn2 "LegacyPowerShellHooks is DEPRECATED. Prefer default Python hooks (docs/DEPRECATED_POWERSHELL.md)."
    }

    # DEPRECATED PowerShell runtime (fallback only — do not extend)
    Copy-FileForced (Join-Path $RepoRoot 'src\speak.ps1') (Join-Path $AiTtsHome 'speak.ps1')
    Copy-FileForced (Join-Path $RepoRoot 'src\speak-core.ps1') (Join-Path $AiTtsHome 'speak-core.ps1')
    Copy-FileForced (Join-Path $RepoRoot 'src\common.ps1') (Join-Path $AiTtsHome 'common.ps1')
    Copy-FileForced (Join-Path $RepoRoot 'src\daemon.ps1') (Join-Path $AiTtsHome 'daemon.ps1')
    Copy-FileForced (Join-Path $RepoRoot 'scripts\daemon-start.ps1') (Join-Path $AiTtsHome 'scripts\daemon-start.ps1')
    Copy-FileForced (Join-Path $RepoRoot 'scripts\daemon-stop.ps1') (Join-Path $AiTtsHome 'scripts\daemon-stop.ps1')
    Write-Ok "PowerShell fallback scripts installed (DEPRECATED)"

    # Python portable package (supported)
    $libDst = Join-Path $AiTtsHome 'lib\ai_tts'
    if (Test-Path $libDst) { Remove-Item $libDst -Recurse -Force }
    Copy-Item -Path (Join-Path $RepoRoot 'src\python\ai_tts') -Destination $libDst -Recurse -Force
    Write-Ok "Python package -> $libDst"

    $py = Resolve-Python
    $script:PythonExe = $py
    if (-not $py) {
        Write-Warn2 "Python 3.10+ not found. Install Python and re-run for multi-OS core."
        Write-Warn2 "Falling back to PowerShell-only hooks."
        $script:UsePythonHooks = $false
    } else {
        $script:UsePythonHooks = -not $LegacyPowerShellHooks
        Write-Ok "Python: $py"
        try {
            Invoke-Python $py @('-c', 'import sys; assert sys.version_info >= (3,10)')
        } catch {
            Write-Warn2 "Python too old (need 3.10+); using PowerShell hooks"
            $script:UsePythonHooks = $false
        }
        if ($script:UsePythonHooks) {
            try {
                Invoke-Python $py @('-c', 'import websockets') 2>$null
                if ($LASTEXITCODE -ne 0) { throw 'no websockets' }
                Write-Ok "websockets available"
            } catch {
                Write-Step "Installing optional websockets for streaming TTS"
                try {
                    if ($py -eq 'py -3') {
                        py -3 -m pip install --user -q 'websockets>=12.0'
                    } else {
                        & $py -m pip install --user -q 'websockets>=12.0'
                    }
                    Write-Ok "websockets installed"
                } catch {
                    Write-Warn2 "pip install websockets failed - REST fallback only"
                }
            }
        }
    }

    # Launchers (write as array so batch syntax never confuses the PowerShell parser)
    $bin = Join-Path $AiTtsHome 'bin'
    $cmdLines = @(
        '@echo off'
        'set "AI_TTS_HOME=%USERPROFILE%\.ai-tts"'
        'set "PYTHONPATH=%AI_TTS_HOME%\lib;%PYTHONPATH%"'
        'where py >nul 2>&1'
        'if %ERRORLEVEL%==0 ('
        '  py -3 -m ai_tts %*'
        '  exit /b %ERRORLEVEL%'
        ')'
        'python -m ai_tts %*'
    )
    Set-Content -LiteralPath (Join-Path $bin 'ai-tts.cmd') -Value $cmdLines -Encoding ASCII
    Write-Ok "launcher bin\ai-tts.cmd"

    # User PATH: add %USERPROFILE%\.ai-tts\bin if missing (new terminals)
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $parts = @()
    if ($userPath) { $parts = $userPath -split ';' | Where-Object { $_ } }
    $already = $parts | Where-Object { $_.TrimEnd('\') -ieq $bin.TrimEnd('\') }
    if (-not $already) {
        try {
            $newPath = if ($userPath) { $userPath.TrimEnd(';') + ';' + $bin } else { $bin }
            [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
            Write-Ok "added $bin to User PATH (new terminals)"
        } catch {
            Write-Warn2 "could not update User PATH; add $bin manually"
        }
    } else {
        Write-Ok "User PATH already includes $bin"
    }

    Get-ChildItem (Join-Path $RepoRoot 'docs\*.md') -ErrorAction SilentlyContinue |
        ForEach-Object { Copy-Item $_.FullName (Join-Path $AiTtsHome "docs\$($_.Name)") -Force }

    $cfgPath = Join-Path $AiTtsHome 'config.json'
    if ((-not (Test-Path $cfgPath)) -or $Force) {
        $mode = if ($EnableDaemon) { 'daemon' } else { 'direct' }
        $cfg = [ordered]@{
            voice    = $Voice
            language = $Language
            speed    = $Speed
            mode     = $mode
            daemon   = [ordered]@{
                enabled                  = [bool]$EnableDaemon
                pipeName                 = 'ai-tts'
                host                     = '127.0.0.1'
                port                     = 18765
                autoStart                = [bool]$AutoStartDaemon
                optimizeStreamingLatency = 2
                sampleRate               = 24000
            }
        }
        ($cfg | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $cfgPath -Encoding UTF8
        Write-Ok "Wrote config.json (voice=$Voice mode=$mode)"
    } else {
        Write-Warn2 "config.json exists (use -Force to overwrite). Keeping existing."
    }
}

function Get-AiTtsCmd {
    return (Join-Path $AiTtsHome 'bin\ai-tts.cmd')
}

function Install-Grok {
    Write-Step "Installing Grok Build integration into $GrokHome"
    Ensure-Dir $GrokHome
    Ensure-Dir (Join-Path $GrokHome 'hooks')
    Ensure-Dir (Join-Path $GrokHome 'skills\tts')
    Ensure-Dir (Join-Path $GrokHome 'rules')
    Ensure-Dir (Join-Path $GrokHome '.tts-dirs')

    Copy-FileForced (Join-Path $AiTtsHome 'speak.ps1') (Join-Path $GrokHome 'speak.ps1')

    $hooksDst = Join-Path $GrokHome 'hooks'
    $hooksSrc = Join-Path $RepoRoot 'grok\hooks'
    Copy-FileForced (Join-Path $hooksSrc 'tts-state.ps1') (Join-Path $hooksDst 'tts-state.ps1')
    Copy-FileForced (Join-Path $hooksSrc 'tts-stop.ps1') (Join-Path $hooksDst 'tts-stop.ps1')

    if ($script:UsePythonHooks) {
        $ai = (Get-AiTtsCmd) -replace '\\', '/'
        $json = @"
{
  "description": "ai-tts (Python): SessionStart + Stop for xAI voice output",
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$ai hook-state --harness grok",
            "timeout": 10
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$ai hook-stop --harness grok",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
"@
        Set-Content -LiteralPath (Join-Path $hooksDst 'tts.json') -Value $json -Encoding UTF8
        Write-Ok "hooks/tts.json (Python)"

        $skill = @'
---
name: tts
description: Toggle xAI voice output on or off for the CURRENT directory. Use when the user runs /tts.
disable-model-invocation: true
user-invocable: true
---

Toggle voice for the current working directory. Run this exact command with the shell tool:

```
& "$env:USERPROFILE\.ai-tts\bin\ai-tts.cmd" toggle --harness grok
```

Then report ON/OFF in one short line.
- **TTS ON**: end each response with a concise `<say>...</say>` spoken summary (plain language).
- **TTS OFF**: do not emit `<say>` markers.

Voice is OFF by default per directory. State under `~/.grok/.tts-dirs/`.
'@
        Set-Content -LiteralPath (Join-Path $GrokHome 'skills\tts\SKILL.md') -Value $skill -Encoding UTF8
    } else {
        $hooksFwd = ($hooksDst -replace '\\', '/')
        $template = Get-Content -LiteralPath (Join-Path $hooksSrc 'tts.json.template') -Raw
        $json = $template.Replace('__GROK_HOOKS__', $hooksFwd)
        Set-Content -LiteralPath (Join-Path $hooksDst 'tts.json') -Value $json -Encoding UTF8
        Write-Warn2 "Installing DEPRECATED PowerShell hooks (LegacyPowerShellHooks)"
        Write-Ok "hooks/tts.json (PowerShell DEPRECATED)"
        Copy-FileForced (Join-Path $RepoRoot 'grok\skills\tts\SKILL.md') (Join-Path $GrokHome 'skills\tts\SKILL.md')
    }

    Copy-FileForced (Join-Path $RepoRoot 'grok\rules\voice-tts.md') (Join-Path $GrokHome 'rules\voice-tts.md')
    Write-Ok "Skill /tts and rules installed"

    Write-Host ""
    Write-Host "Grok next steps:" -ForegroundColor White
    Write-Host "  1. Set User-level XAI_API_KEY (https://console.x.ai )"
    Write-Host "  2. New terminal so PATH + key apply"
    Write-Host "  3. $AiTtsHome\bin\ai-tts.cmd doctor"
    Write-Host "  4. $AiTtsHome\bin\ai-tts.cmd speak `"Hello from Carina`""
    Write-Host "  5. New Grok session, then /tts in a project"
    Write-Host "  Uninstall: uninstall.ps1 or ai-tts uninstall"
}

function Install-Claude {
    Write-Step "Installing Claude Code integration into $ClaudeHome"
    Ensure-Dir $ClaudeHome
    Ensure-Dir (Join-Path $ClaudeHome 'hooks')
    Ensure-Dir (Join-Path $ClaudeHome 'skills\tts')
    Ensure-Dir (Join-Path $ClaudeHome 'rules')
    Ensure-Dir (Join-Path $ClaudeHome '.tts-dirs')

    Copy-FileForced (Join-Path $AiTtsHome 'speak.ps1') (Join-Path $ClaudeHome 'speak.ps1')
    $hooksSrc = Join-Path $RepoRoot 'claude\hooks'
    Copy-FileForced (Join-Path $hooksSrc 'tts-state.ps1') (Join-Path $ClaudeHome 'hooks\tts-state.ps1')
    Copy-FileForced (Join-Path $hooksSrc 'tts-stop.ps1') (Join-Path $ClaudeHome 'hooks\tts-stop.ps1')
    Copy-FileForced (Join-Path $RepoRoot 'claude\rules\voice-tts.md') (Join-Path $ClaudeHome 'rules\voice-tts.md')

    if ($script:UsePythonHooks) {
        $skill = @'
---
name: tts
description: Toggle xAI voice output on or off for the CURRENT directory.
disable-model-invocation: true
---

Run:

```
& "$env:USERPROFILE\.ai-tts\bin\ai-tts.cmd" toggle --harness claude
```

Report ON/OFF. When ON, end replies with `<say>...</say>`.
'@
        Set-Content -LiteralPath (Join-Path $ClaudeHome 'skills\tts\SKILL.md') -Value $skill -Encoding UTF8
        $ai = (Get-AiTtsCmd) -replace '\\', '/'
        $snippet = @"
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "$ai hook-state --harness claude" }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "$ai hook-stop --harness claude" }
        ]
      }
    ]
  }
}
"@
        Set-Content -LiteralPath (Join-Path $AiTtsHome 'claude-settings.hooks.snippet.json') -Value $snippet -Encoding UTF8
    } else {
        Copy-FileForced (Join-Path $RepoRoot 'claude\skills\tts\SKILL.md') (Join-Path $ClaudeHome 'skills\tts\SKILL.md')
    }

    if ($MergeClaudeSettings -and $script:UsePythonHooks) {
        Write-Warn2 "Merge Claude settings manually from $AiTtsHome\claude-settings.hooks.snippet.json (auto-merge left optional)."
    } elseif ($MergeClaudeSettings) {
        Write-Warn2 "Legacy PS Claude merge not re-run; use Python snippet or prior settings."
    } else {
        Write-Warn2 "Claude hooks snippet: $AiTtsHome\claude-settings.hooks.snippet.json"
    }
    Write-Ok "Claude skill/rules installed"
}

# --- main ---
Write-Host "ai-tts installer (Windows)" -ForegroundColor Magenta
Write-Host "  Target : $Target"
Write-Host "  Voice  : $Voice"
Write-Host ""

$script:UsePythonHooks = $true
Install-Shared

if ($Target -eq 'Grok' -or $Target -eq 'Both') { Install-Grok }
if ($Target -eq 'Claude' -or $Target -eq 'Both') { Install-Claude }

Write-Host ""
Write-Host "Done." -ForegroundColor Green
