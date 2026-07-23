# Python runtime (`ai_tts`)

Portable core for **Windows, macOS, and Linux**.

## Commands

```bash
# After install (recommended)
~/.ai-tts/bin/ai-tts probe
~/.ai-tts/bin/ai-tts speak "Hello from Carina"
~/.ai-tts/bin/ai-tts toggle --harness grok
~/.ai-tts/bin/ai-tts daemon --enable-config
~/.ai-tts/bin/ai-tts daemon-stop

# From a repo checkout
export PYTHONPATH=src/python   # Windows: set PYTHONPATH=src\python
python -m ai_tts speak "Hello"
python -m ai_tts hook-stop --harness grok   # reads Stop JSON on stdin
```

## Layout

| Module | Role |
|--------|------|
| `config.py` | `~/.ai-tts/config.json` |
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

See [docs/platforms.md](../../docs/platforms.md).
