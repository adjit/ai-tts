# Architecture

## Goal

Let coding agents **speak a short spoken summary** of each completed turn using **xAI TTS** (Grok voices), without blocking the model or burning context on audio APIs.

## Flow

```
┌─────────────┐     /tts toggle      ┌──────────────────────┐
│ User / agent│ ──────────────────►  │ ~/.{grok|claude}/    │
│             │                      │   .tts-dirs/<hash>   │
└──────┬──────┘                      └──────────────────────┘
       │ SessionStart                         ▲
       │ (is marker present?)                 │
       ▼                                      │
┌─────────────┐  additionalContext     ON/OFF │
│ Agent model │ ◄─────────────────────────────┘
│             │  when ON → end with <say>...</say>
└──────┬──────┘
       │ Stop (turn complete)
       ▼
┌─────────────┐  extract last <say>   ┌──────────────┐
│ tts-stop.ps1│ ───────────────────►  │ speak.ps1    │
│ (detached)  │                       │ xAI /v1/tts  │
└─────────────┘                       └──────────────┘
```

## Why hooks, not tools?

| Approach | Problem |
|----------|---------|
| Agent calls `speak.ps1` mid-turn | Blocks the turn, pollutes tool traces, wastes tokens |
| Agent streams full reply to TTS | Too long, noisy, expensive |
| **Stop hook + short `<say>`** | Async, cheap, model already finished |

## Per-directory state

- Default: **OFF** everywhere.
- `/tts` creates or deletes a marker file:  
  `~/.grok/.tts-dirs/<md5(normalized-cwd)>` (or `~/.claude/...`).
- Grok and Claude keep **separate** marker roots so toggles never cross accidentally.

## Harness differences

| | Grok Build | Claude Code |
|--|------------|-------------|
| Hook registration | `~/.grok/hooks/tts.json` | `~/.claude/settings.json` → `hooks` |
| SessionStart context | JSON `hookSpecificOutput.additionalContext` | Plain stdout text |
| Assistant text on Stop | `lastAssistantMessage` (preferred) | `transcript_path` JSONL |
| Skill path | `~/.grok/skills/tts/SKILL.md` | `~/.claude/skills/tts/SKILL.md` |
| Always-on rules | `~/.grok/rules/voice-tts.md` | `~/.claude/rules/` or `CLAUDE.md` |

## Shared runtime (`~/.ai-tts`)

| File | Role |
|------|------|
| `speak.ps1` | One-shot speaker (direct mode) |
| `speak-core.ps1` | REST + streaming WebSocket + playback |
| `common.ps1` | Markers, say extraction, daemon/direct dispatch |
| `daemon.ps1` | Optional warm named-pipe worker |
| `scripts/daemon-start.ps1` / `daemon-stop.ps1` | Lifecycle helpers |
| `config.json` | `voice`, `mode`, `daemon.*` |

## Modes

```text
                    config.mode
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
         direct                     daemon
            │                         │
   Start-Process speak.ps1     Named pipe -> warm daemon
            │                         │
            └──────────┬──────────────┘
                       ▼
              speak-core (stream WS, REST fallback)
                       ▼
                    play audio
```

Daemon is **optional**. If enabled but not running (and `autoStart` is false), hooks fall back to direct mode. See [daemon.md](daemon.md).

## Security notes

- Hooks run with your user privileges. Only install from a trusted clone.
- `XAI_API_KEY` must be available to detached PowerShell processes (User-level env is reliable on Windows).
- Install never commits secrets; `config.json` holds only voice preferences.
