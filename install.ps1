<#
.SYNOPSIS
  Install ai-tts into Grok Build and/or Claude Code on Windows.

.EXAMPLE
  .\install.ps1                  # Grok only (default)
  .\install.ps1 -Target Both -Voice carina
  .\install.ps1 -Target Claude -MergeClaudeSettings
#>
param(
    [ValidateSet('Grok', 'Claude', 'Both')]
    [string]$Target = 'Grok',

    [string]$Voice = 'carina',

    [string]$Language = 'en',

    [double]$Speed = 1.0,

    [switch]$MergeClaudeSettings,

    [switch]$Force
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

function Install-Shared {
    Write-Step "Installing shared runtime to $AiTtsHome"
    Ensure-Dir $AiTtsHome
    Ensure-Dir (Join-Path $AiTtsHome 'bin')

    Copy-FileForced (Join-Path $RepoRoot 'src\speak.ps1') (Join-Path $AiTtsHome 'speak.ps1')
    Copy-FileForced (Join-Path $RepoRoot 'src\common.ps1') (Join-Path $AiTtsHome 'common.ps1')

    $cfgPath = Join-Path $AiTtsHome 'config.json'
    if ((-not (Test-Path $cfgPath)) -or $Force) {
        $cfg = @{
            voice    = $Voice
            language = $Language
            speed    = $Speed
        } | ConvertTo-Json
        Set-Content -LiteralPath $cfgPath -Value $cfg -Encoding UTF8
        Write-Ok "Wrote config.json (voice=$Voice)"
    } else {
        Write-Warn2 "config.json already exists (use -Force to overwrite). Keeping existing."
    }
}

function Install-Grok {
    Write-Step "Installing Grok Build integration into $GrokHome"
    Ensure-Dir $GrokHome
    Ensure-Dir (Join-Path $GrokHome 'hooks')
    Ensure-Dir (Join-Path $GrokHome 'skills\tts')
    Ensure-Dir (Join-Path $GrokHome 'rules')
    Ensure-Dir (Join-Path $GrokHome '.tts-dirs')

    # Speak copy for fallback path resolution
    Copy-FileForced (Join-Path $AiTtsHome 'speak.ps1') (Join-Path $GrokHome 'speak.ps1')

    $hooksSrc = Join-Path $RepoRoot 'grok\hooks'
    $hooksDst = Join-Path $GrokHome 'hooks'
    Copy-FileForced (Join-Path $hooksSrc 'tts-state.ps1') (Join-Path $hooksDst 'tts-state.ps1')
    Copy-FileForced (Join-Path $hooksSrc 'tts-stop.ps1') (Join-Path $hooksDst 'tts-stop.ps1')

    $hooksFwd = ($hooksDst -replace '\\', '/')
    $template = Get-Content -LiteralPath (Join-Path $hooksSrc 'tts.json.template') -Raw
    $json = $template.Replace('__GROK_HOOKS__', $hooksFwd)
    Set-Content -LiteralPath (Join-Path $hooksDst 'tts.json') -Value $json -Encoding UTF8
    Write-Ok "Wrote hooks/tts.json"

    Copy-FileForced (Join-Path $RepoRoot 'grok\skills\tts\SKILL.md') (Join-Path $GrokHome 'skills\tts\SKILL.md')
    Copy-FileForced (Join-Path $RepoRoot 'grok\rules\voice-tts.md') (Join-Path $GrokHome 'rules\voice-tts.md')
    Write-Ok "Skill /tts and rules/voice-tts.md installed"

    Write-Host ""
    Write-Host "Grok next steps:" -ForegroundColor White
    Write-Host "  1. Set XAI_API_KEY (User or process env)."
    Write-Host "  2. Start a new Grok session (or /hooks → reload)."
    Write-Host "  3. Run /tts in a project directory to enable voice."
    Write-Host "  4. Optional smoke test:"
    Write-Host "     powershell -File `"$AiTtsHome\speak.ps1`" -Text `"Hello from Carina`" -Voice $Voice"
}

function Merge-ClaudeHooks {
    $settingsPath = Join-Path $ClaudeHome 'settings.json'
    $stateCmd = "powershell -NoProfile -ExecutionPolicy Bypass -File $((Join-Path $ClaudeHome 'hooks\tts-state.ps1') -replace '\\','/')"
    $stopCmd = "powershell -NoProfile -ExecutionPolicy Bypass -File $((Join-Path $ClaudeHome 'hooks\tts-stop.ps1') -replace '\\','/')"

    $settings = @{ permissions = @{}; hooks = @{} }
    if (Test-Path $settingsPath) {
        $backup = "$settingsPath.bak-ai-tts-$(Get-Date -Format 'yyyyMMddHHmmss')"
        Copy-Item -LiteralPath $settingsPath -Destination $backup -Force
        Write-Ok "Backed up settings.json → $backup"
        $settings = Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json
    }

    # Convert to mutable hashtables carefully via JSON round-trip
    $obj = $settings | ConvertTo-Json -Depth 30 | ConvertFrom-Json

    if (-not $obj.hooks) {
        $obj | Add-Member -NotePropertyName hooks -NotePropertyValue ([pscustomobject]@{}) -Force
    }

    function Ensure-HookEvent($root, [string]$event, [string]$command) {
        $hooksObj = $root.hooks
        $list = @()
        if ($hooksObj.PSObject.Properties.Name -contains $event -and $hooksObj.$event) {
            $list = @($hooksObj.$event)
        }

        $already = $false
        foreach ($group in $list) {
            if ($group.hooks) {
                foreach ($h in @($group.hooks)) {
                    if ($h.command -and ($h.command -like '*tts-state.ps1*' -or $h.command -like '*tts-stop.ps1*') -and $h.command -like "*$($command.Split('/')[-1])*") {
                        $already = $true
                    }
                    if ($h.command -eq $command) { $already = $true }
                }
            }
        }

        if (-not $already) {
            $entry = [pscustomobject]@{
                matcher = ''
                hooks   = @([pscustomobject]@{ type = 'command'; command = $command })
            }
            # Prefer appending to an existing empty-matcher group if present
            $appended = $false
            for ($i = 0; $i -lt $list.Count; $i++) {
                $g = $list[$i]
                $m = ''
                if ($g.PSObject.Properties.Name -contains 'matcher') { $m = [string]$g.matcher }
                if ($m -eq '' -or $m -eq $null) {
                    $existing = @($g.hooks)
                    # skip if same tts hook type already in this group
                    $dup = $false
                    foreach ($h in $existing) {
                        if ($h.command -and $h.command -like "*$((Split-Path $command -Leaf))*") { $dup = $true }
                    }
                    if (-not $dup) {
                        $g.hooks = @($existing + [pscustomobject]@{ type = 'command'; command = $command })
                        $list[$i] = $g
                        $appended = $true
                        break
                    } else {
                        $appended = $true
                        break
                    }
                }
            }
            if (-not $appended) {
                $list = @($list + $entry)
            }
        }

        $hooksObj | Add-Member -NotePropertyName $event -NotePropertyValue $list -Force
    }

    # Rebuild hooks as a pure PSCustomObject we can rewrite
    $hookMap = [ordered]@{}
    if ($obj.hooks) {
        foreach ($p in $obj.hooks.PSObject.Properties) {
            $hookMap[$p.Name] = @($p.Value)
        }
    }

    function Add-Cmd([hashtable]$map, [string]$event, [string]$command, [string]$leaf) {
        $list = @()
        if ($map.Contains($event)) { $list = @($map[$event]) }

        $exists = $false
        foreach ($group in $list) {
            if (-not $group.hooks) { continue }
            foreach ($h in @($group.hooks)) {
                if ($h.command -and ($h.command -like "*$leaf*")) { $exists = $true }
            }
        }
        if ($exists) { $map[$event] = $list; return }

        if ($list.Count -gt 0) {
            $g0 = $list[0]
            $hooks = @()
            if ($g0.hooks) { $hooks = @($g0.hooks) }
            $hooks += [pscustomobject]@{ type = 'command'; command = $command }
            $list[0] = [pscustomobject]@{
                matcher = $(if ($g0.PSObject.Properties.Name -contains 'matcher') { $g0.matcher } else { '' })
                hooks   = $hooks
            }
            # preserve rest
            if ($list.Count -gt 1) {
                $list = @($list[0]) + $list[1..($list.Count - 1)]
            }
        } else {
            $list = @(
                [pscustomobject]@{
                    matcher = ''
                    hooks   = @([pscustomobject]@{ type = 'command'; command = $command })
                }
            )
        }
        $map[$event] = $list
    }

    Add-Cmd $hookMap 'SessionStart' $stateCmd 'tts-state.ps1'
    Add-Cmd $hookMap 'Stop' $stopCmd 'tts-stop.ps1'

    $hooksOut = [pscustomobject]@{}
    foreach ($k in $hookMap.Keys) {
        $hooksOut | Add-Member -NotePropertyName $k -NotePropertyValue $hookMap[$k] -Force
    }
    if ($obj.PSObject.Properties.Name -contains 'hooks') {
        $obj.hooks = $hooksOut
    } else {
        $obj | Add-Member -NotePropertyName hooks -NotePropertyValue $hooksOut -Force
    }

    $json = $obj | ConvertTo-Json -Depth 30
    Set-Content -LiteralPath $settingsPath -Value $json -Encoding UTF8
    Write-Ok "Merged TTS hooks into $settingsPath"
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
    $hooksDst = Join-Path $ClaudeHome 'hooks'
    Copy-FileForced (Join-Path $hooksSrc 'tts-state.ps1') (Join-Path $hooksDst 'tts-state.ps1')
    Copy-FileForced (Join-Path $hooksSrc 'tts-stop.ps1') (Join-Path $hooksDst 'tts-stop.ps1')

    Copy-FileForced (Join-Path $RepoRoot 'claude\skills\tts\SKILL.md') (Join-Path $ClaudeHome 'skills\tts\SKILL.md')
    Copy-FileForced (Join-Path $RepoRoot 'claude\rules\voice-tts.md') (Join-Path $ClaudeHome 'rules\voice-tts.md')
    Write-Ok "Skill /tts, hooks, and rules installed"

    if ($MergeClaudeSettings) {
        Merge-ClaudeHooks
    } else {
        $hooksFwd = ((Join-Path $ClaudeHome 'hooks') -replace '\\', '/')
        $snippet = Get-Content -LiteralPath (Join-Path $RepoRoot 'claude\settings.hooks.snippet.json') -Raw
        $snippet = $snippet.Replace('__CLAUDE_HOOKS__', $hooksFwd)
        $outSnippet = Join-Path $AiTtsHome 'claude-settings.hooks.snippet.json'
        Set-Content -LiteralPath $outSnippet -Value $snippet -Encoding UTF8
        Write-Warn2 "Did not modify ~/.claude/settings.json"
        Write-Host "  Merge hooks manually from: $outSnippet"
        Write-Host "  Or re-run: .\install.ps1 -Target Claude -MergeClaudeSettings"
    }

    Write-Host ""
    Write-Host "Claude next steps:" -ForegroundColor White
    Write-Host "  1. Ensure SessionStart + Stop hooks point at tts-state.ps1 / tts-stop.ps1."
    Write-Host "  2. Optionally append claude/rules/voice-tts.md into CLAUDE.md."
    Write-Host "  3. Restart Claude Code, then run /tts in a project."
}

# --- main ---
Write-Host "ai-tts installer" -ForegroundColor Magenta
Write-Host "  Target : $Target"
Write-Host "  Voice  : $Voice"
Write-Host ""

Install-Shared

if ($Target -eq 'Grok' -or $Target -eq 'Both') { Install-Grok }
if ($Target -eq 'Claude' -or $Target -eq 'Both') { Install-Claude }

Write-Host ""
Write-Host "Done." -ForegroundColor Green
