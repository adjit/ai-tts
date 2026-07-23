# ai-tts

**Spoken agent summaries** for [Grok Build](https://grok.x.ai/) (primary) and [Claude Code](https://docs.anthropic.com/en/docs/claude-code), powered by **xAI text-to-speech**.

When voice is on for a project directory, the agent ends each reply with a short `<say>...</say>` line. A **Stop hook** speaks it asynchronously (default voice: **Carina**) so the model never blocks on audio.

Works on **Windows, macOS, and Linux** via a portable **Python 3.10+** runtime.

> **PowerShell scripts are deprecated.** They ship only as a Windows fallback. Prefer `ai-tts` / `python -m ai_tts`. See [docs/DEPRECATED_POWERSHELL.md](docs/DEPRECATED_POWERSHELL.md).

```text
You:  fix the flaky test
Grok: [does the work, prints a normal reply]
      <say>Fixed the race by awaiting the mock reset before each case.</say>
      🔊 Carina speaks that line
```

---

## Why this exists

| Built-in | This project |
|----------|----------------|
| Grok **voice mode** = dictation (you → text) | **TTS output** (agent → speech) |
| Reading long replies aloud is noisy | Short 1–2 sentence summaries only |
| Calling TTS from tools wastes context | Hooks run **after** the turn, detached |

---

## Requirements

| | |
|--|--|
| **OS** | Windows, macOS, or Linux |
| **Python** | **3.10+** (primary runtime) |
| **API key** | `XAI_API_KEY` in the environment (User/login profile so detached hooks can see it) |
| **Agent** | Grok Build and/or Claude Code |
| **Optional** | `pip install --user 'websockets>=12.0'` for streaming TTS |
| **Playback** | Windows: `winsound` (built-in). macOS: `afplay`. Linux: `ffplay` (ffmpeg), `paplay`, or `aplay` |

---

## Quick start

1. Get an API key from [console.x.ai](https://console.x.ai) → set `XAI_API_KEY` (login / User env so hooks see it).
2. Install, health-check, speak:

**macOS / Linux**

```bash
git clone <this-repo-url> ai-tts && cd ai-tts
chmod +x install.sh uninstall.sh

# Interactive (TTY): pick target + voice with a Rich UI
./install.sh

# Or non-interactive / CI:
# ./install.sh Grok
# VOICE=eve FORCE=1 ./install.sh Both
# AI_TTS_INSTALL_NONINTERACTIVE=1 ./install.sh

# PATH: source ~/.ai-tts/env.sh   # or use ~/.local/bin/ai-tts symlink
ai-tts doctor
ai-tts speak "Hello from Carina"
```

**Windows**

```powershell
git clone <this-repo-url> ai-tts; cd ai-tts
.\install.ps1 -Target Grok -Voice carina -Force
# New terminal so User PATH picks up %USERPROFILE%\.ai-tts\bin
ai-tts doctor
ai-tts speak "Hello from Carina"
```

3. **New agent session** → open a project → **`/tts`** → ask something; you should hear the `<say>` line.

Toggle off with `/tts` again (per directory).  
Full path still works if PATH is not set: `~/.ai-tts/bin/ai-tts` or `%USERPROFILE%\.ai-tts\bin\ai-tts.cmd`.

More detail: [docs/platforms.md](docs/platforms.md) · [docs/architecture.md](docs/architecture.md) · [docs/voices.md](docs/voices.md) · [docs/testing.md](docs/testing.md)

---

## CLI reference

```text
ai-tts doctor                         # post-install health + fix hints
ai-tts setup                          # alias for doctor
ai-tts probe                          # compact players / config / key
ai-tts status                         # TTS on/off for cwd + daemon
ai-tts config                         # show config.json
ai-tts config set voice eve           # voice | language | speed | mode
ai-tts voices                         # known voice ids
ai-tts speak "Hello"                  # one-shot TTS + play
ai-tts speak --transport rest "..."   # force REST (no WebSocket)
ai-tts toggle --harness grok          # same as /tts for Grok
ai-tts toggle --harness claude        # Claude marker root
ai-tts daemon --enable-config         # optional low-latency TCP server
ai-tts daemon-ping
ai-tts daemon-stop
ai-tts uninstall [--remove-config] [--remove-markers]
ai-tts hook-state --harness grok      # used by SessionStart
ai-tts hook-stop --harness grok       # used by Stop
```

From a repo checkout without installing:

```bash
export PYTHONPATH=src/python   # Windows: set PYTHONPATH=src\python
python -m ai_tts doctor
```

---

## What install drops

### Shared (`~/.ai-tts`)

| Path | Purpose |
|------|---------|
| `bin/ai-tts` / `bin/ai-tts.cmd` | CLI launcher |
| `lib/ai_tts/` | Python package (speak, daemon, hooks, doctor, …) |
| `config.json` | Voice, mode (`direct`/`daemon`), daemon host/port — prefer `ai-tts config` |
| `env.sh` | PATH fragment (Unix); `source ~/.ai-tts/env.sh` |
| `docs/` | Copied reference docs |
| `claude-settings.hooks.snippet.json` | Claude hook merge helper (if Claude installed) |
| `speak.ps1`, `common.ps1`, … | **Deprecated** PowerShell fallback (Windows only) |

### Grok (`~/.grok`)

| Path | Purpose |
|------|---------|
| `hooks/tts.json` | SessionStart + Stop → `ai-tts hook-*` |
| `skills/tts/SKILL.md` | `/tts` skill (`ai-tts toggle`) |
| `rules/voice-tts.md` | Standing `<say>` instructions |
| `.tts-dirs/` | Per-directory on/off markers |

### Claude (`~/.claude`)

Same idea with `--harness claude`. Hook command snippet is written to  
`~/.ai-tts/claude-settings.hooks.snippet.json` for merging into `settings.json`.

Claude markers (`~/.claude/.tts-dirs/`) are **independent** of Grok’s toggle.

---

## Claude Code (optional)

**Windows**

```powershell
.\install.ps1 -Target Claude -Voice carina
# or both:
.\install.ps1 -Target Both -Voice carina
```

**macOS / Linux**

```bash
./install.sh Claude
# or
./install.sh Both
```

Merge the generated hook snippet into `~/.claude/settings.json` (SessionStart + Stop).  
Restart Claude Code, then `/tts` in a project.

---

## How it works

1. **`/tts`** (or `ai-tts toggle`) creates/deletes a marker under `~/.{grok\|claude}/.tts-dirs/`.
2. **SessionStart** tells the model whether TTS is on for this directory.
3. **When on**, the model ends every response with:

   ```text
   <say>One or two plain spoken sentences.</say>
   ```

4. **Stop** extracts that block and runs `ai-tts speak` **detached** (no tool call, no blocked turn).

```text
Stop hook → ai-tts hook-stop → detach speak
                                    │
                         mode=daemon? ──yes──► TCP 127.0.0.1:18765
                                    │ no
                         WebSocket stream (if websockets) else REST
                                    │
                         play WAV (OS player)
```

### `<say>` guidelines

- 1–2 sentences, conversational  
- No code, paths, markdown, or long identifiers  
- Final line of the response only  
- **Never** call TTS from the agent yourself — the hook does it  

---

## Configuration

**Prefer the CLI** (writes `~/.ai-tts/config.json`):

```bash
ai-tts config                         # show effective settings
ai-tts config set voice eve
ai-tts config set language en
ai-tts config set speed 1.1
ai-tts config set mode direct         # or: daemon
ai-tts voices                         # known voice ids
ai-tts status                         # cwd on/off + daemon
```

Equivalent file (`~/.ai-tts/config.json` or `$AI_TTS_HOME/config.json`):

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
    "pipeName": "ai-tts",
    "autoStart": false,
    "optimizeStreamingLatency": 2,
    "sampleRate": 24000
  }
}
```

| Field | Meaning |
|-------|---------|
| `mode` | `direct` (default) or `daemon` — also `ai-tts config set mode …` |
| `daemon.host` / `port` | TCP endpoint for the portable daemon |
| `daemon.pipeName` | Legacy Windows named-pipe daemon only |
| `daemon.autoStart` | If daemon is down, try to start it once |
| `optimizeStreamingLatency` | `0`–`2` (higher = faster first audio, slight quality tradeoff) |

Voices: [docs/voices.md](docs/voices.md) · daemon: [docs/daemon.md](docs/daemon.md).

Re-install defaults:

```powershell
.\install.ps1 -Target Grok -Voice eve -Force
```

```bash
VOICE=eve FORCE=1 ./install.sh Grok
```

---

## Optional low-latency daemon

**Direct mode** (default): short-lived process per turn — simple, no background worker.

**Daemon mode**: warm Python process on localhost TCP; better for frequent `/tts` use.

```bash
# Enable + start (or: ai-tts config set mode daemon && ai-tts daemon)
ai-tts daemon --enable-config

ai-tts daemon-ping
ai-tts status         # "daemon": "up" | "down"
ai-tts daemon-stop    # stops server and sets mode=direct
```

Windows convenience wrappers still exist (`scripts/daemon-start.ps1` prefers the Python TCP daemon).

If daemon mode is configured but the server is not running (and `autoStart` is false), speak **falls back to direct** automatically.

Details: [docs/daemon.md](docs/daemon.md) · [docs/platforms.md](docs/platforms.md)

---

## Repository layout

```text
ai-tts/
├── README.md
├── install.ps1                 # Windows installer (Python hooks)
├── install.sh                  # macOS/Linux installer
├── uninstall.ps1
├── pyproject.toml
├── requirements.txt            # optional: websockets
├── config.example.json
├── src/
│   ├── python/ai_tts/          # portable core (SUPPORTED)
│   ├── speak.ps1               # DEPRECATED Windows PS
│   ├── speak-core.ps1          # DEPRECATED
│   ├── common.ps1              # DEPRECATED
│   └── daemon.ps1              # DEPRECATED named-pipe daemon
├── scripts/
│   ├── run-tests.sh / .ps1     # unit suite (+ Docker / live)
│   ├── smoke.sh / smoke.ps1    # product probe + hooks (+ optional speak)
│   ├── daemon-start.ps1        # prefers Python; -LegacyNamedPipe DEPRECATED
│   └── daemon-stop.ps1
├── grok/                       # packaging (skills/rules; PS hooks DEPRECATED)
├── claude/
├── docs/
│   ├── architecture.md
│   ├── daemon.md
│   ├── platforms.md
│   ├── testing.md              # quality ladder + how to run tests
│   ├── DEPRECATED_POWERSHELL.md
│   └── voices.md
└── examples/
    └── manual-smoke.ps1        # DEPRECATED → scripts/smoke.ps1
```

---

## Tests

Unit tests mock the xAI API and never touch your real home directory.  
Details and **definition of done**: [docs/testing.md](docs/testing.md).

```powershell
# Windows local
.\scripts\run-tests.ps1

# Linux container (independent of host OS)
.\scripts\run-tests.ps1 -Docker

# Product smoke (probe + hook-state; speak if XAI_API_KEY set)
.\scripts\smoke.ps1
```

```bash
# macOS / Linux local
chmod +x scripts/run-tests.sh scripts/smoke.sh
./scripts/run-tests.sh

# Linux container
./scripts/run-tests.sh --docker

# Product smoke
./scripts/smoke.sh
```

```bash
# Optional live call (real API + speakers)
RUN_LIVE_TTS=1 XAI_API_KEY=... ./scripts/run-tests.sh --live
```

CI: `.github/workflows/test.yml` runs unit tests on Ubuntu, Windows, and macOS, plus a Docker Linux job.

---

## Porting checklist (another machine)

- [ ] Clone this repo  
- [ ] Install **Python 3.10+**  
- [ ] Set `XAI_API_KEY` (User/login env)  
- [ ] `.\install.ps1 -Target Grok` **or** `./install.sh Grok`  
- [ ] `ai-tts doctor` then `ai-tts speak "Hello"`  
- [ ] New Grok/Claude session → `/tts` → hear speech  
- [ ] Optional: `ai-tts daemon --enable-config` for lower latency  
- [ ] Optional: `pip install --user 'websockets>=12.0'` for streaming  

### Linux playback

Install one of: `ffmpeg` (`ffplay`), `paplay`, or `aplay`.

---

## Uninstall

```powershell
.\uninstall.ps1 -Target Both
.\uninstall.ps1 -Target Both -RemoveConfig -RemoveMarkers
# or: ai-tts uninstall --remove-config --remove-markers
```

```bash
./uninstall.sh Both
./uninstall.sh Both --remove-config --remove-markers
# or: ai-tts uninstall --remove-config --remove-markers
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| No speech | `ai-tts doctor` — fix key/players/hooks; try `ai-tts speak "test"` |
| `command not found: ai-tts` | `source ~/.ai-tts/env.sh` or full path `~/.ai-tts/bin/ai-tts`; re-run installer |
| Slow after `<say>` appears | Turn end + process start. Use **daemon mode**; install `websockets` for streaming |
| Daemon configured but silent | `ai-tts daemon-ping`; start with `ai-tts daemon --enable-config`; check `~/.ai-tts/daemon.log` |
| Model never emits `<say>` | `/tts` must be ON; new session so SessionStart + rules load |
| Hooks not firing | Grok: `/hooks`, confirm `tts.json`; reload or new session |
| Linux no audio | Install `ffplay`, `paplay`, or `aplay` |
| Claude silent | Merge hook snippet into `settings.json`; confirm Stop runs |
| Wrong voice | Edit `~/.ai-tts/config.json` → `voice` |
| Dictation vs TTS | `/voice` is **input**; this project is **output** |

---

## Deprecated PowerShell path

Do not extend `src/*.ps1` or PowerShell hooks. Use Python. Details and removal plan: **[docs/DEPRECATED_POWERSHELL.md](docs/DEPRECATED_POWERSHELL.md)**.

---

## Security

- Hooks and the daemon run as your user.  
- Daemon binds **localhost only** by default.  
- Install only from a source you trust.  
- No API keys are stored in this repo.

---

## License

MIT — see [LICENSE](LICENSE).
