# Optional low-latency daemon

By default **ai-tts** uses **direct mode**: each Stop hook detaches a short-lived
`ai-tts speak` process, synthesizes via xAI, plays audio, exits.

For lower latency after each turn, enable the **optional TCP daemon** (Python):

1. One warm process (no cold start per turn)
2. Streaming WebSocket TTS when `websockets` is installed
3. Protocol over **localhost TCP** (portable across Windows / macOS / Linux)

Direct mode remains the default. Daemon is opt-in.

> **Deprecated:** The Windows **named-pipe** PowerShell daemon (`src/daemon.ps1`)
> is obsolete. Use Python TCP only. See [DEPRECATED_POWERSHELL.md](DEPRECATED_POWERSHELL.md).

---

## Configure

**CLI (preferred):**

```bash
ai-tts config set mode daemon     # sets mode + daemon.enabled
ai-tts daemon --enable-config     # start server and enable in config
ai-tts status                     # shows mode + daemon up/down
ai-tts config set mode direct     # back to one-shot (after daemon-stop)
```

**Config file** (`~/.ai-tts/config.json`) equivalent:

```json
{
  "voice": "carina",
  "language": "en",
  "speed": 1.0,
  "mode": "daemon",
  "daemon": {
    "enabled": true,
    "host": "127.0.0.1",
    "port": 18765,
    "autoStart": false,
    "optimizeStreamingLatency": 2,
    "sampleRate": 24000
  }
}
```

| Field | Default | Meaning |
|-------|---------|---------|
| `mode` | `direct` | `direct` = one-shot `ai-tts speak`; `daemon` = TCP client |
| `daemon.enabled` | `false` | Same as `mode: daemon` when true |
| `daemon.host` / `port` | `127.0.0.1` / `18765` | TCP listen address |
| `daemon.autoStart` | `false` | If true and server missing, try start once |
| `daemon.optimizeStreamingLatency` | `2` | xAI stream tip (`0` quality … `2` fastest) |
| `daemon.sampleRate` | `24000` | PCM sample rate |
| `daemon.pipeName` | `ai-tts` | **Deprecated** Windows named pipe only |

Install with daemon preference (still start the process yourself unless `autoStart`):

```powershell
.\install.ps1 -Target Grok -EnableDaemon
```

```bash
ENABLE_DAEMON=1 ./install.sh Grok
```

---

## Start / stop

```bash
# Any OS
ai-tts daemon --enable-config
ai-tts daemon-ping
ai-tts status                 # "daemon": "up" | "down"
ai-tts daemon-stop            # stop server; sets mode=direct

# Windows launcher
%USERPROFILE%\.ai-tts\bin\ai-tts.cmd daemon --enable-config
```

Windows helper scripts still exist but prefer Python:

```powershell
.\scripts\daemon-start.ps1          # starts Python TCP daemon
.\scripts\daemon-start.ps1 -LegacyNamedPipe   # DEPRECATED
```

Logs: `~/.ai-tts/daemon.log`  
PID file: `~/.ai-tts/daemon.pid`

---

## Fallback behavior

When `mode` is `daemon` / `enabled` is true:

1. Client sends JSON to TCP `host:port`.
2. If down and `autoStart` is true → try start daemon, retry once.
3. Otherwise → **fall back to direct** `ai-tts speak`.

You never lose speech if the daemon is misconfigured; you only lose the latency win.

---

## Protocol

One line request, one line response (UTF-8 JSON) over TCP:

```text
-> {"text":"Hello","voice":"carina","language":"en","speed":1.0}
<- {"ok":true,"ms":850,"voice":"carina","transport":"stream"}

-> {"cmd":"ping"}
<- {"ok":true,"pong":true,"pid":12345}

-> {"cmd":"shutdown"}
<- {"ok":true,"shutdown":true}
```

---

## When to use which mode

| | Direct | Daemon (Python TCP) |
|--|--------|---------------------|
| Setup | Install only | Install + start daemon |
| Background process | No | Yes |
| Latency after Stop | Higher | Lower |
| Best for | Occasional voice | Frequent `/tts` use |
| Switch | `ai-tts config set mode direct` | `ai-tts config set mode daemon` + `daemon --enable-config` |
