# Multi-OS support

**Status:** Python portable core is implemented (Phase 1 + Phase 2).  
Windows PowerShell runtime is **DEPRECATED** (fallback only) — [DEPRECATED_POWERSHELL.md](DEPRECATED_POWERSHELL.md).

---

## What you get

| Feature | Windows | macOS | Linux |
|---------|---------|-------|-------|
| One-shot speak | Yes | Yes | Yes |
| Optional TCP daemon | Yes | Yes | Yes |
| Grok hooks | Yes | Yes | Yes |
| Claude hooks | Yes | Yes | Yes |
| Playback | winsound / ffplay | afplay | ffplay / paplay / aplay |
| Streaming TTS | if `websockets` installed | same | same |

---

## Install

### Windows

```powershell
cd ai-tts
.\install.ps1 -Target Grok -Voice carina -Force
# Python hooks by default
# DEPRECATED: .\install.ps1 -LegacyPowerShellHooks
```

### macOS / Linux

```bash
cd ai-tts
chmod +x install.sh
./install.sh Grok
# VOICE=eve FORCE=1 ENABLE_DAEMON=1 ./install.sh Both
```

Requires **Python 3.10+**. Optional: `pip install --user 'websockets>=12.0'`.

---

## Runtime layout (`~/.ai-tts`)

```text
~/.ai-tts/
  bin/ai-tts[.cmd]     # launcher
  lib/ai_tts/          # Python package
  config.json
  docs/
  (Windows also keeps speak.ps1 / common.ps1 fallbacks)
```

---

## Usage

```bash
ai-tts probe
ai-tts speak "Hello from Carina"
ai-tts toggle --harness grok      # same as /tts
ai-tts daemon --enable-config     # optional low-latency server
ai-tts daemon-ping
ai-tts daemon-stop
```

Config (`mode: direct | daemon`):

```json
{
  "voice": "carina",
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

Daemon protocol (TCP JSON lines) — same as the design doc:

```text
-> {"text":"...","voice":"carina","language":"en","speed":1.0}
<- {"ok":true,"ms":420,"transport":"stream"}
```

---

## Architecture

```text
Stop hook -> ai-tts hook-stop
                |
         detach: ai-tts speak
                |
         mode=daemon? --yes--> TCP 127.0.0.1:18765
                | no
         stream WS (optional) else REST
                |
         play WAV (OS player)
```

---

## Linux notes

Install one of:

- `ffmpeg` (provides `ffplay`) — recommended  
- `pulseaudio-utils` (`paplay`)  
- `alsa-utils` (`aplay`)

---

## Phases completed

| Phase | Status |
|-------|--------|
| 0 Plan | Done |
| 1 Portable one-shot | Done (`speak`, players, installers) |
| 2 TCP daemon | Done (`daemon` / client) |
| 3 CI / stream-while-play | Future |

---

## Security

- Daemon binds **localhost only** by default.  
- Hooks run as your user.  
- Never commit `XAI_API_KEY`.
