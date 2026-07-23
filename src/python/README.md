# Python runtime (planned)

This directory will hold the **portable TTS core** described in [docs/platforms.md](../../docs/platforms.md).

## Planned layout

```text
src/python/
  ai_tts/
    __init__.py
    __main__.py      # python -m ai_tts speak|daemon|toggle|hook-stop|hook-state
    config.py
    client.py        # TCP localhost client (daemon mode)
    daemon.py        # optional warm server
    tts_rest.py
    tts_stream.py    # wss://api.x.ai/v1/tts
    play.py          # dispatch to player backends
    markers.py       # ~/.grok|.claude/.tts-dirs
  players/
    macos.py         # afplay
    linux.py         # ffplay | paplay | aplay
    windows.py       # winsound / subprocess to legacy helper
```

## Design rules

1. **stdlib-first**; add `websockets` only if needed for streaming.
2. Daemon listens on **`127.0.0.1:18765`** by default (not named pipes).
3. `mode: direct | daemon` matches existing `config.json`.
4. Hook entrypoints must exit quickly on success; speech may block only inside the daemon or one-shot process, never inside a Stop *gate* longer than needed.
5. Windows PowerShell remains supported until this package reaches feature parity.

## Status

Scaffold only — no package installed yet. Implementation = platforms.md Phase 1+.
