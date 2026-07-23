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
┌─────────────┐  extract last <say>   ┌──────────────────┐
│ ai-tts      │ ───────────────────►  │ Python speak /   │
│ hook-stop   │  (detached)           │ optional daemon  │
└─────────────┘                       └──────────────────┘
```

> PowerShell `tts-stop.ps1` / `speak.ps1` are **deprecated**. See [DEPRECATED_POWERSHELL.md](DEPRECATED_POWERSHELL.md).

## Why hooks, not tools?

| Approach | Problem |
|----------|---------|
| Agent calls speak mid-turn | Blocks the turn, pollutes tool traces, wastes tokens |
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

| Path | Role |
|------|------|
| `bin/ai-tts` / `ai-tts.cmd` | CLI launcher (**supported**) |
| `lib/ai_tts/` | Python package (**supported**) |
| `config.json` | `voice`, `mode`, `daemon.*` (prefer `ai-tts config`) |
| `env.sh` | PATH fragment (Unix install) |
| `speak.ps1`, `daemon.ps1`, … | **Deprecated** Windows PowerShell fallback |

## CLI surface (day-to-day)

| Command | Role |
|---------|------|
| `ai-tts doctor` / `setup` | Post-install health checks + fix hints |
| `ai-tts status` | TTS on/off for cwd, voice, daemon up/down |
| `ai-tts config` / `config set …` | Show / update voice, language, speed, mode |
| `ai-tts voices` | Known voice ids |
| `ai-tts toggle` | Same as `/tts` (per-directory marker) |
| `ai-tts speak` | One-shot synthesis + play |
| `ai-tts daemon*` | Optional warm TCP server |
| `ai-tts uninstall` | Remove install artifacts |

Hooks (`hook-state`, `hook-stop`) are for the agent harness, not interactive use.  
Full list: [README.md](../README.md) · platforms: [platforms.md](platforms.md).

## Modes

```text
                    config.mode
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
         direct                     daemon
            │                         │
   ai-tts speak (one-shot)     TCP 127.0.0.1:18765
            │                         │
            └──────────┬──────────────┘
                       ▼
         stream WS (optional) else REST
                       ▼
                    play WAV
```

Daemon is **optional**. If enabled but not running (and `autoStart` is false), speak falls back to direct. See [daemon.md](daemon.md).

## Multi-OS

Python is the supported path on Windows, macOS, and Linux. PowerShell is deprecated. See [platforms.md](platforms.md) and [DEPRECATED_POWERSHELL.md](DEPRECATED_POWERSHELL.md).

## Security notes

- Hooks run with your user privileges. Only install from a trusted clone.
- `XAI_API_KEY` must be available to detached processes (User/login env).
- Install never commits secrets; `config.json` holds only voice preferences.
