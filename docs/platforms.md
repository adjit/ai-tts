# Multi-OS expansion plan

**Status today:** Windows-first (PowerShell 5.1+, winmm playback, named-pipe daemon).  
**Goal:** Same skill UX on **Windows, macOS, and Linux** for Grok Build and Claude Code.

This document is the recommended path — not all of it is implemented yet.

---

## What is already portable

| Layer | Portable? | Notes |
|-------|-----------|--------|
| xAI REST TTS | Yes | HTTPS; no OS dependency |
| xAI streaming WebSocket | Yes | `wss://api.x.ai/v1/tts` |
| Grok / Claude hooks model | Yes | JSON hooks + shell command |
| `/tts` skill idea | Yes | Marker files under `~/.{grok,claude}/.tts-dirs` |
| Rules (`voice-tts.md`) | Yes | Markdown only |

## What is Windows-only today

| Piece | Why |
|-------|-----|
| `winmm` / MCI playback | Win32 API |
| `System.Speech` fallback | .NET Framework Windows |
| Named pipe daemon `\\.\pipe\ai-tts` | Works on Windows; Unix needs different IPC |
| `install.ps1` / `Start-Process powershell.exe` | Windows process model |
| Hook command lines hardcoding `powershell -File ...` | macOS/Linux prefer `pwsh` or a language runtime |

---

## Recommendation (short version)

1. **Keep harness packaging (skills, rules, hook *logic*) OS-agnostic.**  
2. **Move the runtime (TTS + playback + optional daemon) to a small portable core** — prefer **Python 3.10+**.  
3. **Use localhost TCP for the daemon**, not named pipes — one protocol on every OS.  
4. **Thin per-OS playback adapters** (`afplay`, `ffplay`/`paplay`, winmm).  
5. **Ship `install.ps1` + `install.sh`**; both write the right hook command for the host.  
6. **Do not require PowerShell on Mac/Linux** for the happy path (optional `pwsh` is fine, not required).

### Why Python for the core (not “more PowerShell”)

| Option | Pros | Cons |
|--------|------|------|
| **Python** (recommended) | WebSockets, audio libs, one codebase; easy on Mac/Linux/Win; great for a long-lived daemon | Extra runtime dependency |
| PowerShell 7 (`pwsh`) everywhere | Reuse current scripts | Playback still OS-specific; weaker streaming ergonomics; less common on locked-down Linux |
| Node.js | Good WS support | Heavier for a tiny daemon; another toolchain |
| Pure bash + curl | Zero deps for REST | No good streaming daemon; fragile |

Python wins for **optional daemon + streaming + multi-OS** with the least long-term glue.

---

## Target architecture

```text
                    Grok / Claude Stop hook
                              |
                    host command (sh or ps1)
                              |
              +---------------v----------------+
              |     ai-tts client (python)     |
              |  - if mode=daemon: TCP 127.0.0.1|
              |  - else: one-shot speak        |
              +---------------+----------------+
                              |
              +---------------v----------------+
              |  speak core (python)           |
              |  - WebSocket stream (preferred)|
              |  - REST fallback               |
              +---------------+----------------+
                              |
         +--------------------+--------------------+
         v                    v                    v
   player/windows        player/macos         player/linux
   (winmm / playsound)   (afplay)             (ffplay|paplay|aplay)
```

### Daemon transport: localhost TCP

Prefer:

```text
127.0.0.1:18765   (configurable)
```

JSON lines (same as today):

```text
-> {"text":"...","voice":"carina","language":"en","speed":1.0}
<- {"ok":true,"ms":420}
```

**Why not keep named pipes as primary?**  
They work on Windows but force a second code path on Unix (UDS). TCP localhost is boring and universal; firewalls almost never block loopback.

Keep Windows named pipes only as a thin alias if needed for compatibility; new code should use TCP.

### Playback matrix

| OS | Primary | Fallback |
|----|---------|----------|
| Windows | winmm WAV (current) | `System.Speech`, or `ffplay` if present |
| macOS | `afplay` (built-in) | `ffplay` |
| Linux | `ffplay -nodisp -autoexit` (ffmpeg) | `paplay` (Pulse), `aplay` (ALSA) |

Ship WAV/PCM from the API so players stay simple. Avoid MP3-only on Linux without ffmpeg.

### Hook command generation

Installer detects OS and writes:

**Windows**

```text
powershell -NoProfile -ExecutionPolicy Bypass -File .../tts-stop.ps1
```

**macOS / Linux**

```text
python3 "$HOME/.ai-tts/bin/hook_stop.py"
# or: "$HOME/.ai-tts/bin/ai-tts" stop-hook
```

SessionStart is the same idea (`hook_state.py` / `tts-state` equivalent).

Skills that toggle markers stay as small shell/PowerShell snippets **or** a single `ai-tts toggle` CLI so `/tts` is one command on every OS.

---

## Phased rollout

### Phase 0 — Documented (this file)

- Agree on Python core + TCP daemon + dual installers.

### Phase 1 — Portable one-shot (no daemon)

- `python -m ai_tts speak "text"` using REST (or stream-to-temp-file).
- Players: Windows (keep PS or call Python), macOS `afplay`, Linux `ffplay`.
- `install.sh` for Grok hooks on Mac/Linux.
- Windows keeps working; installer can prefer Python if available.

**Exit criteria:** macOS user hears Carina without PowerShell.

### Phase 2 — Portable optional daemon

- `ai-tts daemon` listens on `127.0.0.1:18765`.
- Client in Stop hook: connect → JSON line → return.
- Config stays `mode: direct | daemon` (already in config shape).
- Deprecate Windows-only named pipe (or wrap it to the same protocol).

**Exit criteria:** daemon mode works on Win/Mac/Linux with one config schema.

### Phase 3 — Polish

- Streaming playback (play PCM before full utterance ends) where OS APIs allow.
- `brew` / `pipx` / release binaries (PyInstaller) optional.
- CI matrix: lint + dry-run install on ubuntu-latest, macos-latest, windows-latest.

---

## Dependency policy

**Required for portable core**

- Python 3.10+
- stdlib first; add `websockets` (or use stdlib where enough) for streaming

**Optional**

- `ffmpeg` / `ffplay` on Linux (document; don’t bundle)
- Windows: no extra deps if we keep winmm via a tiny helper or pure Python `winsound` for WAV

**Avoid**

- Hard dependency on PowerShell Core on Mac/Linux
- Shipping large native audio engines

---

## Config (unchanged shape, portable fields)

```json
{
  "voice": "carina",
  "language": "en",
  "speed": 1.0,
  "mode": "direct",
  "daemon": {
    "enabled": false,
    "host": "127.0.0.1",
    "port": 18765,
    "autoStart": false,
    "optimizeStreamingLatency": 2,
    "sampleRate": 24000
  }
}
```

`pipeName` remains for Windows legacy; new installs prefer `host`/`port`.

---

## Testing checklist per OS

- [ ] `ai-tts speak "hello"` with `XAI_API_KEY`
- [ ] Install Grok hooks; SessionStart reports ON/OFF
- [ ] `/tts` toggle marker under `~/.grok/.tts-dirs`
- [ ] Stop speaks `<say>` in direct mode
- [ ] Daemon start/stop; second utterance reuses connection
- [ ] Fallback: daemon configured but down → direct still works

---

## Non-goals (for now)

- iOS / Android agents
- Browser-only playback
- Replacing Grok’s built-in **dictation** (`/voice`) — this project is **output** TTS only

---

## Decision summary

| Decision | Choice |
|----------|--------|
| Shared runtime language | **Python 3** |
| Optional daemon IPC | **localhost TCP** (not named pipes as primary) |
| Playback | **OS tools** (`afplay` / `ffplay` / winmm) |
| Installers | **`install.ps1` + `install.sh`** |
| Default mode | **direct** (daemon stays optional) |
| Windows compatibility | Keep working; gradually call into Python core |

Next implementation step when ready: **Phase 1** (`src/python` package + `install.sh` + macOS/Linux players) while leaving Windows PowerShell as a working backend until the Python path is proven.
