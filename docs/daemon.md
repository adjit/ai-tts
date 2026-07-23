# Optional low-latency daemon

By default **ai-tts** uses **direct mode**: each Stop hook spawns a new PowerShell process, calls xAI TTS, plays audio, exits. That is simple and requires no background process.

For lower latency after each turn, enable the **optional daemon**:

1. One warm PowerShell process (no ~1s cold start per turn)
2. Streaming WebSocket TTS (`wss://api.x.ai/v1/tts`) with `optimize_streaming_latency`
3. Reused WebSocket across utterances when possible

Direct mode remains the default. Daemon is opt-in via config (and you must start it).

---

## Configure

`%USERPROFILE%\.ai-tts\config.json`:

```json
{
  "voice": "carina",
  "language": "en",
  "speed": 1.0,
  "mode": "daemon",
  "daemon": {
    "enabled": true,
    "pipeName": "ai-tts",
    "autoStart": false,
    "optimizeStreamingLatency": 2,
    "sampleRate": 24000
  }
}
```

| Field | Default | Meaning |
|-------|---------|---------|
| `mode` | `direct` | `direct` = spawn `speak.ps1`; `daemon` = named pipe |
| `daemon.enabled` | `false` | Same as `mode: daemon` when true |
| `daemon.pipeName` | `ai-tts` | Windows named pipe `\\.\pipe\<name>` |
| `daemon.autoStart` | `false` | If true and pipe missing, Stop hook tries to start the daemon once |
| `daemon.optimizeStreamingLatency` | `2` | xAI streaming latency tip (`0` quality … `2` fastest first audio) |
| `daemon.sampleRate` | `24000` | PCM sample rate for streaming |

Install with daemon preference pre-set (still start the process yourself unless `autoStart`):

```powershell
.\install.ps1 -Target Grok -EnableDaemon
.\install.ps1 -Target Grok -EnableDaemon -AutoStartDaemon
```

---

## Start / stop

```powershell
# Background
powershell -File $env:USERPROFILE\.ai-tts\scripts\daemon-start.ps1

# Foreground (debug logs on console)
powershell -File $env:USERPROFILE\.ai-tts\scripts\daemon-start.ps1 -Foreground

# Stop and set mode back to direct
powershell -File $env:USERPROFILE\.ai-tts\scripts\daemon-stop.ps1

# Stop but keep mode=daemon in config
powershell -File $env:USERPROFILE\.ai-tts\scripts\daemon-stop.ps1 -KeepDaemonMode
```

Logs: `%USERPROFILE%\.ai-tts\daemon.log`  
PID file: `%USERPROFILE%\.ai-tts\daemon.pid`

---

## Fallback behavior

When `mode` is `daemon` / `enabled` is true:

1. Stop hook sends JSON to the named pipe (fast path).
2. If the pipe is down and `autoStart` is true → try start daemon, retry once.
3. Otherwise → **fall back to direct** `speak.ps1` (same as default mode).

You never lose speech if the daemon is misconfigured; you only lose the latency win.

---

## Protocol (for integrators)

Named pipe, one line request, one line response (UTF-8 JSON):

```text
-> {"text":"Hello","voice":"carina","language":"en","speed":1.0}
<- {"ok":true,"ms":850,"voice":"carina"}

-> {"cmd":"ping"}
<- {"ok":true,"pong":true,"pid":12345}

-> {"cmd":"shutdown"}
<- {"ok":true,"shutdown":true}
```

---

## When to use which mode

| | Direct | Daemon |
|--|--------|--------|
| Setup | Install only | Install + start daemon |
| Background process | No | Yes |
| Latency after Stop | Higher (spawn + REST/stream) | Lower (warm process + stream) |
| Best for | Occasional voice | Frequent `/tts` use |

Direct mode also uses **streaming WebSocket when possible**, with REST fallback — so one-shot `speak.ps1` is improved even without the daemon. The daemon’s main win is avoiding process spawn and keeping the socket warm.
