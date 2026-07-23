# Python runtime (`ai_tts`)

Portable core for **Windows, macOS, and Linux**.

## Commands

```bash
# After install (recommended) — put ~/.ai-tts/bin on PATH or use full path
ai-tts doctor                         # health checks + fix hints
ai-tts setup                          # alias for doctor
ai-tts probe                          # compact players / config / key
ai-tts status                         # TTS on/off for cwd + daemon
ai-tts config                         # show config.json
ai-tts config set voice eve
ai-tts config set speed 1.1
ai-tts config set mode daemon
ai-tts voices
ai-tts speak "Hello from Carina"
ai-tts speak --transport rest "..."
ai-tts toggle --harness grok          # same as /tts
ai-tts daemon --enable-config
ai-tts daemon-ping
ai-tts daemon-stop
ai-tts uninstall [--remove-config] [--remove-markers]

# From a repo checkout
export PYTHONPATH=src/python   # Windows: set PYTHONPATH=src\python
python -m ai_tts doctor
python -m ai_tts speak "Hello"
python -m ai_tts hook-stop --harness grok   # reads Stop JSON on stdin
```

## Layout

| Module | Role |
|--------|------|
| `config.py` | `~/.ai-tts/config.json` load/save |
| `cli_config.py` | `config` / `config set` helpers |
| `doctor.py` | `doctor` / `setup` health checks |
| `voices.py` | Known voice catalog |
| `uninstall.py` | `uninstall` cleanup |
| `tts_rest.py` | Unary WAV TTS |
| `tts_stream.py` | WebSocket PCM stream (`websockets` optional) |
| `play.py` | `winsound` / `afplay` / `ffplay`/`paplay`/`aplay` |
| `speak.py` | Orchestration |
| `client.py` / `daemon_server.py` | Optional TCP daemon (`127.0.0.1:18765`) |
| `markers.py` | `/tts` per-dir markers |
| `hooks.py` | SessionStart / Stop |
| `__main__.py` | CLI |

## Dependencies

- **Required:** Python 3.10+
- **Optional:** `pip install websockets` for streaming (else REST)
- **Dev:** `pip install -r requirements-dev.txt` then `./scripts/run-tests.sh`

See [docs/platforms.md](../../docs/platforms.md) · [docs/testing.md](../../docs/testing.md) · [docs/voices.md](../../docs/voices.md).

PowerShell runtime is **deprecated** — [docs/DEPRECATED_POWERSHELL.md](../../docs/DEPRECATED_POWERSHELL.md).
