# ai-tts

**Spoken agent summaries** for [Grok Build](https://grok.x.ai/) (primary) and [Claude Code](https://docs.anthropic.com/en/docs/claude-code), powered by **xAI text-to-speech**.

When voice is on for a project directory, the agent ends each reply with a short `<say>...</say>` line. A **Stop hook** speaks it asynchronously (default voice: **Carina**) so the model never blocks on audio.

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

- **Windows (supported today):** PowerShell + winmm / System.Speech playback  
- **macOS / Linux:** planned — see [docs/platforms.md](docs/platforms.md); `install.sh` is a scaffold only  
- **`XAI_API_KEY`** set as a **User**/login environment variable (so detached hook processes can see it)  
- **Grok Build** and/or **Claude Code**

---

## Quick start

### Windows

```powershell
git clone <this-repo-url> ai-tts
cd ai-tts
.\install.ps1 -Target Grok -Voice carina -Force

# Smoke-test (Python portable core)
& "$env:USERPROFILE\.ai-tts\bin\ai-tts.cmd" probe
& "$env:USERPROFILE\.ai-tts\bin\ai-tts.cmd" speak "Hello from Carina"
```

### macOS / Linux

```bash
git clone <this-repo-url> ai-tts
cd ai-tts
chmod +x install.sh
./install.sh Grok

~/.ai-tts/bin/ai-tts probe
~/.ai-tts/bin/ai-tts speak "Hello from Carina"
```

Requires **Python 3.10+**. Optional streaming: `pip install --user 'websockets>=12.0'`.

Then in Grok:

1. **New session** (or `/hooks` → reload) so hooks load.
2. Open a project directory.
3. Run **`/tts`** → should report `TTS ON`.
4. Ask anything; the reply should end with `<say>...</say>` and you should hear Carina.

Toggle off with `/tts` again. State is **per directory** and persists across sessions.

Full multi-OS notes: [docs/platforms.md](docs/platforms.md).

### What Grok install drops

| Path | Purpose |
|------|---------|
| `~/.ai-tts/speak.ps1` | One-shot xAI TTS player (direct mode) |
| `~/.ai-tts/speak-core.ps1` | Streaming WebSocket + REST + playback |
| `~/.ai-tts/common.ps1` | Shared hook helpers + mode dispatch |
| `~/.ai-tts/daemon.ps1` | Optional warm worker |
| `~/.ai-tts/scripts/daemon-*.ps1` | Start/stop helpers |
| `~/.ai-tts/config.json` | Voice, mode (`direct`/`daemon`), daemon options |
| `~/.grok/hooks/tts.json` | Registers SessionStart + Stop |
| `~/.grok/hooks/tts-state.ps1` | Injects ON/OFF into the model |
| `~/.grok/hooks/tts-stop.ps1` | Speaks the last `<say>` block |
| `~/.grok/skills/tts/SKILL.md` | `/tts` slash skill |
| `~/.grok/rules/voice-tts.md` | Standing instructions for `<say>` lines |
| `~/.grok/.tts-dirs/` | Per-directory on/off markers |

---

## Claude Code (optional)

```powershell
.\install.ps1 -Target Claude -Voice carina -MergeClaudeSettings
# or both harnesses:
.\install.ps1 -Target Both -Voice carina -MergeClaudeSettings
```

`-MergeClaudeSettings` merges SessionStart/Stop hook entries into `~/.claude/settings.json` (creates a timestamped `.bak-ai-tts-*` first).

Without the switch, install still copies scripts and writes a ready-to-paste snippet to:

`%USERPROFILE%\.ai-tts\claude-settings.hooks.snippet.json`

Also ensure the agent sees the rule text (`claude/rules/voice-tts.md` is copied to `~/.claude/rules/`).

Claude markers live under `~/.claude/.tts-dirs/` — **independent** of Grok’s toggle.

---

## How it works

1. **`/tts`** creates or deletes a marker file for the current working directory.
2. **SessionStart** tells the model whether TTS is on for this directory.
3. **When on**, the model ends every response with:

   ```text
   <say>One or two plain spoken sentences.</say>
   ```

4. **Stop** extracts that block and launches `speak.ps1` **detached** (no turn block, no tool call).

Details: [docs/architecture.md](docs/architecture.md).

### `<say>` guidelines (for agents / rules)

- 1–2 sentences, conversational
- No code, paths, markdown, or long identifiers
- Final line of the response only
- **Never** call `speak.ps1` from the agent — the hook does it

---

## Configuration

Edit `~/.ai-tts/config.json`:

```json
{
  "voice": "carina",
  "language": "en",
  "speed": 1.0,
  "mode": "direct",
  "daemon": {
    "enabled": false,
    "pipeName": "ai-tts",
    "autoStart": false,
    "optimizeStreamingLatency": 2,
    "sampleRate": 24000
  }
}
```

See [docs/voices.md](docs/voices.md) for voice IDs (`carina`, `eve`, `leo`, `ara`, …).

Re-install with a new default:

```powershell
.\install.ps1 -Target Grok -Voice eve -Force
```

---

## Optional low-latency daemon

Default **direct** mode runs a short-lived speak process per turn (simple, no background process).

For faster speech, enable the **optional TCP daemon** (warm Python process + streaming TTS when `websockets` is installed):

```bash
# Any OS — start daemon and set mode=daemon
ai-tts daemon --enable-config
# Windows: start in another window, or:
# Start-Process ... ai-tts.cmd daemon --enable-config

ai-tts daemon-ping
ai-tts daemon-stop    # also sets mode=direct
```

| Setting | Effect |
|---------|--------|
| `"mode": "direct"` (default) | One-shot speak per turn |
| `"mode": "daemon"` + daemon running | TCP `127.0.0.1:18765` → warm worker |
| `daemon.autoStart: true` | If server is down, Stop path tries to start it once |

If daemon mode is on but the process is not running (and autoStart is off), speak **falls back to direct** automatically.

Windows also still ships a legacy named-pipe PowerShell daemon (`scripts/daemon-start.ps1`); prefer the Python TCP daemon.

---

## Repository layout

```text
ai-tts/
├── README.md                 <- you are here
├── install.ps1               <- Windows installer (production)
├── install.sh                <- macOS/Linux installer scaffold
├── uninstall.ps1
├── config.example.json
├── src/
│   ├── speak.ps1             <- one-shot player (direct mode, Windows)
│   ├── speak-core.ps1        <- REST + streaming WebSocket
│   ├── common.ps1            <- hooks: markers + daemon/direct dispatch
│   ├── daemon.ps1            <- optional warm named-pipe worker (Windows)
│   └── python/               <- portable core scaffold (Phase 1+)
├── scripts/
│   ├── daemon-start.ps1
│   └── daemon-stop.ps1
├── grok/                     <- Grok Build packaging (primary)
│   ├── hooks/
│   ├── skills/tts/
│   └── rules/
├── claude/                   <- Claude Code packaging
│   ├── hooks/
│   ├── skills/tts/
│   ├── rules/
│   └── settings.hooks.snippet.json
├── docs/
│   ├── architecture.md
│   ├── daemon.md
│   ├── platforms.md          <- multi-OS plan (Python + TCP daemon)
│   └── voices.md
└── examples/
    └── manual-smoke.ps1
```

### Cross-platform direction

| Priority | Approach |
|----------|----------|
| 1 | **Python 3** portable speak/daemon core |
| 2 | Daemon over **localhost TCP** (not named pipes as primary) |
| 3 | Playback: **afplay** (macOS), **ffplay/paplay** (Linux), winmm (Windows) |
| 4 | Dual installers: `install.ps1` + `install.sh` |

Details and phases: **[docs/platforms.md](docs/platforms.md)**.

---

## Porting checklist (another machine)

- [ ] Clone this repo  
- [ ] Set **User** env `XAI_API_KEY`  
- [ ] `.\install.ps1 -Target Grok` (or `Both`)  
- [ ] Smoke: `.\examples\manual-smoke.ps1`  
- [ ] New Grok session → `/tts` → ask a question → hear speech  
- [ ] Optional: change voice in `~/.ai-tts/config.json`  

### Manual install (no installer)

1. Copy `src/speak.ps1` + `src/common.ps1` → `~/.ai-tts/`  
2. Copy `config.example.json` → `~/.ai-tts/config.json` and set `voice`  
3. Copy `grok/hooks/*.ps1` → `~/.grok/hooks/`  
4. Render `grok/hooks/tts.json.template` → `tts.json`, replacing `__GROK_HOOKS__` with your hooks directory using forward slashes  
5. Copy skill + rules into `~/.grok/skills/tts/` and `~/.grok/rules/`  
6. Restart Grok  

---

## Uninstall

```powershell
.\uninstall.ps1 -Target Both
# also wipe config + markers:
.\uninstall.ps1 -Target Both -RemoveConfig -RemoveMarkers
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| No speech | Confirm User-level `XAI_API_KEY`; test `speak.ps1` alone |
| Slow after `<say>` appears | Expected in direct mode (turn end + spawn). Use **daemon mode** ([docs/daemon.md](docs/daemon.md)) |
| Daemon configured but still slow | Ensure process is running (`daemon-start.ps1`); check `daemon.log` |
| Model never emits `<say>` | Run `/tts` (must be ON); new session so SessionStart + rules load |
| Hooks not firing | Grok: `/hooks` and confirm `tts.json` enabled; reload or restart |
| Claude silent | Check `settings.json` Stop/SessionStart include tts hooks; transcript path present |
| Wrong voice | Edit `~/.ai-tts/config.json` → `voice` |
| Dictation vs TTS | `/voice` / Ctrl+Space is **input**; this skill is **output** |

---

## Security

- Hooks execute local PowerShell with your user permissions.  
- Install only from a source you trust.  
- No API keys are stored in this repo.

---

## License

MIT — see [LICENSE](LICENSE).
