# Project Instructions for AI Agents

## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking when `.beads/` is present.

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress
bd close <id>         # Complete work
```

Conservative git policy: do not commit or push unless the user asks.

## Build & Test

Python package: `src/python/ai_tts`. Tests isolate `HOME` / `AI_TTS_HOME` (see `tests/conftest.py`).

```bash
pip install -r requirements-dev.txt
export PYTHONPATH=src/python

# Rung 1 — offline unit suite (required for code changes)
./scripts/run-tests.sh
# or: pytest -q --ignore=tests/test_live_optional.py

# Rung 2 — product smoke (probe + hook-state; speak if key set)
./scripts/smoke.sh

# Rung 3 — live API (optional)
# RUN_LIVE_TTS=1 XAI_API_KEY=... ./scripts/run-tests.sh --live
```

Full ladder and DoD: [docs/testing.md](docs/testing.md).

## Architecture

Stop-hook TTS for Grok Build / Claude Code via xAI. Portable core under `src/python/ai_tts`.  
See [docs/architecture.md](docs/architecture.md).

## Conventions

- Prefer Python over deprecated PowerShell (`docs/DEPRECATED_POWERSHELL.md`).
- Do not call real xAI from default unit tests — mock transport/play.
- Never commit `XAI_API_KEY` or write secrets into the repo.
