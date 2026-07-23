#!/usr/bin/env bash
# Install ai-tts (Python portable core) for macOS / Linux.
# Usage:
#   ./install.sh                  # Grok only
#   ./install.sh Both             # Grok + Claude
#   VOICE=eve FORCE=1 ./install.sh Grok
#   ENABLE_DAEMON=1 ./install.sh
set -euo pipefail

TARGET="${1:-Grok}"   # Grok | Claude | Both
VOICE="${VOICE:-carina}"
LANGUAGE="${LANGUAGE:-en}"
SPEED="${SPEED:-1.0}"
FORCE="${FORCE:-0}"
ENABLE_DAEMON="${ENABLE_DAEMON:-0}"
AUTO_START_DAEMON="${AUTO_START_DAEMON:-0}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_TTS_HOME="${AI_TTS_HOME:-$HOME/.ai-tts}"
PYTHON="${PYTHON:-python3}"

die() { echo "error: $*" >&2; exit 1; }
step() { echo "-> $*"; }
ok() { echo "  OK $*"; }
warn() { echo "  ! $*"; }

command -v "$PYTHON" >/dev/null 2>&1 || die "python3 not found (set PYTHON=...)"

PY_VER="$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
"$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
  || die "Python 3.10+ required (found $PY_VER)"

echo "ai-tts install.sh"
echo "  target : $TARGET"
echo "  voice  : $VOICE"
echo "  python : $PYTHON ($PY_VER)"
echo "  home   : $AI_TTS_HOME"
echo ""

# --- shared runtime ---
step "Installing Python package to $AI_TTS_HOME/lib"
mkdir -p "$AI_TTS_HOME/lib" "$AI_TTS_HOME/bin" "$AI_TTS_HOME/docs"
rm -rf "$AI_TTS_HOME/lib/ai_tts"
cp -R "$REPO_ROOT/src/python/ai_tts" "$AI_TTS_HOME/lib/ai_tts"
ok "copied ai_tts package"

# Optional streaming dependency
if "$PYTHON" -c 'import websockets' 2>/dev/null; then
  ok "websockets already installed"
else
  step "Installing optional websockets (streaming TTS)"
  if "$PYTHON" -m pip install --user -q 'websockets>=12.0' 2>/dev/null; then
    ok "websockets installed"
  else
    warn "could not pip install websockets — REST fallback only"
  fi
fi

# Launcher
LAUNCHER="$AI_TTS_HOME/bin/ai-tts"
cat >"$LAUNCHER" <<EOF
#!/usr/bin/env bash
export AI_TTS_HOME="\${AI_TTS_HOME:-$AI_TTS_HOME}"
export PYTHONPATH="\$AI_TTS_HOME/lib\${PYTHONPATH:+:\$PYTHONPATH}"
exec "$PYTHON" -m ai_tts "\$@"
EOF
chmod +x "$LAUNCHER"
ok "launcher $LAUNCHER"

# Config
CFG="$AI_TTS_HOME/config.json"
MODE="direct"
DENABLED="false"
if [[ "$ENABLE_DAEMON" == "1" ]]; then
  MODE="daemon"
  DENABLED="true"
fi
if [[ ! -f "$CFG" || "$FORCE" == "1" ]]; then
  cat >"$CFG" <<EOF
{
  "voice": "$VOICE",
  "language": "$LANGUAGE",
  "speed": $SPEED,
  "mode": "$MODE",
  "daemon": {
    "enabled": $DENABLED,
    "pipeName": "ai-tts",
    "host": "127.0.0.1",
    "port": 18765,
    "autoStart": $([[ "$AUTO_START_DAEMON" == "1" ]] && echo true || echo false),
    "optimizeStreamingLatency": 2,
    "sampleRate": 24000
  }
}
EOF
  ok "wrote config.json (mode=$MODE voice=$VOICE)"
else
  warn "keeping existing config.json (FORCE=1 to overwrite)"
fi

cp -f "$REPO_ROOT/docs/"*.md "$AI_TTS_HOME/docs/" 2>/dev/null || true

# Playback probe
step "Playback probe"
case "$(uname -s)" in
  Darwin)
    command -v afplay >/dev/null && ok "afplay" || warn "afplay missing"
    ;;
  Linux)
    if command -v ffplay >/dev/null; then ok "ffplay"
    elif command -v paplay >/dev/null; then ok "paplay"
    elif command -v aplay >/dev/null; then ok "aplay"
    else warn "install ffmpeg (ffplay) or paplay/aplay"
    fi
    ;;
esac

AI_TTS_BIN="$LAUNCHER"

write_grok_hooks() {
  local grok_home="$HOME/.grok"
  step "Installing Grok Build integration into $grok_home"
  mkdir -p "$grok_home/hooks" "$grok_home/skills/tts" "$grok_home/rules" "$grok_home/.tts-dirs"

  cat >"$grok_home/hooks/tts.json" <<EOF
{
  "description": "ai-tts (Python): SessionStart + Stop for xAI voice output",
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$AI_TTS_BIN hook-state --harness grok",
            "timeout": 10
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$AI_TTS_BIN hook-stop --harness grok",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
EOF
  ok "hooks/tts.json"

  cat >"$grok_home/skills/tts/SKILL.md" <<'SKILL'
---
name: tts
description: Toggle xAI voice output on or off for the CURRENT directory. Use when the user runs /tts.
disable-model-invocation: true
user-invocable: true
---

Toggle voice for the current working directory. Run this exact command with the shell tool:

```
"$HOME/.ai-tts/bin/ai-tts" toggle --harness grok
```

Then report ON/OFF in one short line.
- **TTS ON**: end each response with `<say>1-2 spoken sentences</say>` (plain language, no code/paths).
- **TTS OFF**: do not emit `<say>` markers.

Voice is OFF by default per directory. State: `~/.grok/.tts-dirs/`.
SKILL
  ok "skill /tts"

  cp -f "$REPO_ROOT/grok/rules/voice-tts.md" "$grok_home/rules/voice-tts.md"
  # Point rules at portable runtime
  cat >"$grok_home/rules/voice-tts.md" <<'RULE'
# Voice Output (TTS)

Voice output is delivered by a **Stop hook** that speaks a `<say>` line asynchronously via xAI — you do **NOT** call speak tools yourself.

**How it works:**
- Voice is **per-directory and OFF by default.** SessionStart reports ON/OFF. Toggle with `/tts` (`ai-tts toggle --harness grok`).
- **When ON:** end every response with a single `<say>...</say>` line (1-2 sentences, plain spoken language).
- **When OFF:** do not emit `<say>` markers.

**Writing the `<say>` line:**
- Plain spoken language only — no code, file paths, markdown, or long identifiers.
- Place it as the final line of your response.
RULE
  ok "rules/voice-tts.md"
}

write_claude_hooks() {
  local claude_home="$HOME/.claude"
  step "Installing Claude Code files into $claude_home"
  mkdir -p "$claude_home/hooks" "$claude_home/skills/tts" "$claude_home/rules" "$claude_home/.tts-dirs"

  cat >"$claude_home/skills/tts/SKILL.md" <<'SKILL'
---
name: tts
description: Toggle xAI voice output on or off for the CURRENT directory.
disable-model-invocation: true
---

Run:

```
"$HOME/.ai-tts/bin/ai-tts" toggle --harness claude
```

Report ON/OFF. When ON, end replies with `<say>...</say>`. When OFF, do not.
SKILL

  cp -f "$REPO_ROOT/claude/rules/voice-tts.md" "$claude_home/rules/voice-tts.md" 2>/dev/null || true

  SNIPPET="$AI_TTS_HOME/claude-settings.hooks.snippet.json"
  cat >"$SNIPPET" <<EOF
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "$AI_TTS_BIN hook-state --harness claude"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "$AI_TTS_BIN hook-stop --harness claude"
          }
        ]
      }
    ]
  }
}
EOF
  warn "Merge hooks into ~/.claude/settings.json from: $SNIPPET"
  ok "Claude skill + hook snippet"
}

case "$TARGET" in
  Grok|grok) write_grok_hooks ;;
  Claude|claude) write_claude_hooks ;;
  Both|both) write_grok_hooks; write_claude_hooks ;;
  *) die "unknown target: $TARGET (use Grok|Claude|Both)" ;;
esac

echo ""
echo "Next steps:"
echo "  1. export XAI_API_KEY=...  (login shell / profile)"
echo "  2. Smoke:  $AI_TTS_BIN probe"
echo "             $AI_TTS_BIN speak \"Hello from Carina\""
echo "  3. Optional daemon:  $AI_TTS_BIN daemon --enable-config &"
echo "  4. New Grok session, then /tts in a project"
echo "Done."
