# Deprecated: PowerShell runtime (Windows-only)

> **Status: DEPRECATED**  
> Do not build new features on these scripts. They remain only as a short-term Windows fallback.

## Preferred path

| Layer | Use this |
|-------|----------|
| Runtime | Python package `ai_tts` (`src/python/ai_tts/`) |
| CLI | `~/.ai-tts/bin/ai-tts` / `ai-tts.cmd` |
| Hooks | `ai-tts hook-state` / `ai-tts hook-stop` |
| Daemon | `ai-tts daemon` (TCP `127.0.0.1:18765`) |
| Install | `install.ps1` (Python hooks) or `install.sh` |

See [platforms.md](platforms.md) and the main [README](../README.md).

## What is deprecated

| Path | Role (legacy) |
|------|----------------|
| `src/speak.ps1` | One-shot TTS + play |
| `src/speak-core.ps1` | REST / stream helpers for PS |
| `src/common.ps1` | Marker + daemon dispatch for PS hooks |
| `src/daemon.ps1` | Named-pipe warm worker |
| `scripts/daemon-start.ps1` | Prefer Python; PS path is legacy (`-LegacyNamedPipe`) |
| `scripts/daemon-stop.ps1` | Prefer `ai-tts daemon-stop` |
| `grok/hooks/tts-state.ps1` | Prefer Python SessionStart |
| `grok/hooks/tts-stop.ps1` | Prefer Python Stop |
| `grok/hooks/tts.json.template` | PS hook command template |
| `claude/hooks/tts-*.ps1` | Prefer Python hooks |

## How to stay on the legacy path (not recommended)

```powershell
.\install.ps1 -Target Grok -LegacyPowerShellHooks -Force
```

```powershell
.\scripts\daemon-start.ps1 -LegacyNamedPipe
```

## Removal plan

1. **Now** — Python is default; PS files emit deprecation notices; docs mark them deprecated.  
2. **Next** — Stop installing PS scripts by default (`-IncludeLegacyPowerShell` opt-in).  
3. **Later** — Delete the PS runtime once no known users rely on it.

If you still need a behavior that only exists in PowerShell, open an issue and port it to Python instead of extending the PS code.
