# Multi-OS support

**Status:** Python portable core is the supported runtime.  
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
| doctor / config / status | Yes | Yes | Yes |

---

## Install

### Windows

```powershell
cd ai-tts
.\install.ps1 -Target Grok -Voice carina -Force
# Adds %USERPROFILE%\.ai-tts\bin to User PATH when possible
# Python hooks by default
# DEPRECATED: .\install.ps1 -LegacyPowerShellHooks
```

### macOS / Linux

```bash
cd ai-tts
chmod +x install.sh uninstall.sh
./install.sh              # interactive Rich UI (target + voice) when run in a TTY
./install.sh Grok         # non-interactive
# VOICE=eve FORCE=1 ENABLE_DAEMON=1 ./install.sh Both
# AI_TTS_INSTALL_NONINTERACTIVE=1 ./install.sh
# Writes ~/.ai-tts/env.sh and tries ~/.local/bin/ai-tts symlink
```

Requires **Python 3.10+**.  
Optional: `pip install --user 'websockets>=12.0'` (streaming), `rich>=13` (pretty install UI; `install.sh` tries to install Rich automatically).

### PATH

| OS | How `ai-tts` gets on PATH |
|----|---------------------------|
| macOS / Linux | `source ~/.ai-tts/env.sh` and/or `~/.local/bin` symlink |
| Windows | Installer adds User PATH entry (new terminals) |

Full path always works: `~/.ai-tts/bin/ai-tts` / `%USERPROFILE%\.ai-tts\bin\ai-tts.cmd`.

### After install

```bash
ai-tts doctor          # health checks + fix hints
ai-tts speak "Hello from Carina"
```

---

## Runtime layout (`~/.ai-tts`)

```text
~/.ai-tts/
  bin/ai-tts[.cmd]     # launcher
  lib/ai_tts/          # Python package
  config.json
  env.sh               # PATH fragment (Unix install)
  docs/
  claude-settings.hooks.snippet.json   # if Claude target installed
  (Windows also keeps speak.ps1 / common.ps1 fallbacks — DEPRECATED)
```

---

## Usage

```bash
ai-tts doctor                         # post-install health + fix hints
ai-tts setup                          # alias for doctor
ai-tts probe                          # compact env dump
ai-tts status                         # TTS on/off for cwd + daemon
ai-tts config                         # show config
ai-tts config set voice eve
ai-tts config set mode daemon
ai-tts voices
ai-tts speak "Hello from Carina"
ai-tts toggle --harness grok          # same as /tts
ai-tts daemon --enable-config         # optional low-latency server
ai-tts daemon-ping
ai-tts daemon-stop
ai-tts uninstall [--remove-config] [--remove-markers]
```

Or via scripts:

```bash
./uninstall.sh Both
./uninstall.sh Both --remove-config --remove-markers
```

```powershell
.\uninstall.ps1 -Target Both -RemoveConfig -RemoveMarkers
```

Config via CLI (preferred) or `~/.ai-tts/config.json`:

```bash
ai-tts config set voice carina
ai-tts config set mode direct
```

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

Daemon protocol (TCP JSON lines):

```text
-> {"text":"...","voice":"carina","language":"en","speed":1.0}
<- {"ok":true,"ms":420,"transport":"stream"}
```

See [daemon.md](daemon.md).

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

Also: [architecture.md](architecture.md) · [testing.md](testing.md) · [voices.md](voices.md)

---

## Linux notes

Install one of:

- `ffmpeg` (provides `ffplay`) — recommended  
- `pulseaudio-utils` (`paplay`)  
- `alsa-utils` (`aplay`)

`ai-tts doctor` will flag missing players.

---

## Phases completed

| Phase | Status |
|-------|--------|
| 0 Plan | Done |
| 1 Portable one-shot | Done (`speak`, players, installers) |
| 2 TCP daemon | Done (`daemon` / client) |
| 3 Tests / doctor / config CLI | Done (unit + smoke + doctor/config/status) |
| Stream-while-play polish | Future |

---

## Security

- Daemon binds **localhost only** by default.  
- Hooks run as your user.  
- Never commit `XAI_API_KEY`.
