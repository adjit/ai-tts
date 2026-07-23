#!/usr/bin/env bash
# Install ai-tts (Python portable core) for macOS / Linux.
#
# Usage:
#   ./install.sh                      # interactive (TTY) or Grok default
#   ./install.sh Grok                 # non-interactive
#   ./install.sh Both
#   VOICE=eve FORCE=1 ./install.sh Grok
#   ENABLE_DAEMON=1 ./install.sh
#   AI_TTS_INSTALL_NONINTERACTIVE=1 ./install.sh   # force defaults (CI)
#
# Presentation uses Python Rich when available (auto-installed best-effort).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_TTS_HOME="${AI_TTS_HOME:-$HOME/.ai-tts}"
PYTHON="${PYTHON:-python3}"
export PYTHONPATH="$REPO_ROOT/src/python${PYTHONPATH:+:$PYTHONPATH}"

TARGET="${1:-}"
VOICE="${VOICE:-carina}"
LANGUAGE="${LANGUAGE:-en}"
SPEED="${SPEED:-1.0}"
FORCE="${FORCE:-0}"
ENABLE_DAEMON="${ENABLE_DAEMON:-0}"
AUTO_START_DAEMON="${AUTO_START_DAEMON:-0}"

die() { echo "error: $*" >&2; exit 1; }

command -v "$PYTHON" >/dev/null 2>&1 || die "python3 not found (set PYTHON=...)"

PY_VER="$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
"$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
  || die "Python 3.10+ required (found $PY_VER)"

# Best-effort Rich for pretty UI (offline/CI still works without it)
if ! "$PYTHON" -c 'import rich' 2>/dev/null; then
  "$PYTHON" -m pip install --user -q 'rich>=13.0' 2>/dev/null || true
fi

ui() {
  "$PYTHON" -m ai_tts.install_ui "$@"
}

step() { ui step "$*"; }
ok()   { ui ok "$*"; }
warn() { ui warn "$*"; }
die()  { ui error "$*"; exit 1; }

# Interactive wizard when no target arg, TTY, and not forced non-interactive
if [[ -z "$TARGET" ]]; then
  if [[ -t 0 && -t 1 && "${AI_TTS_INSTALL_NONINTERACTIVE:-0}" != "1" ]]; then
    # shellcheck disable=SC1090
    eval "$(ui wizard --export-shell --default-target Grok --default-voice "$VOICE")"
  else
    TARGET="Grok"
  fi
fi

# Normalize TARGET
case "$TARGET" in
  Grok|grok) TARGET=Grok ;;
  Claude|claude) TARGET=Claude ;;
  Both|both) TARGET=Both ;;
  *) die "unknown target: $TARGET (use Grok|Claude|Both)" ;;
esac

MODE="direct"
if [[ "$ENABLE_DAEMON" == "1" ]]; then
  MODE="daemon"
fi

ui banner \
  --title "ai-tts installer" \
  --target "$TARGET" \
  --voice "$VOICE" \
  --python "$PYTHON ($PY_VER)" \
  --home "$AI_TTS_HOME" \
  --mode "$MODE"

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

# PATH helper: env.sh + optional ~/.local/bin symlink
ENV_SH="$AI_TTS_HOME/env.sh"
cat >"$ENV_SH" <<EOF
# ai-tts PATH fragment — add to ~/.zprofile or ~/.bashrc:
#   source $ENV_SH
export PATH="$AI_TTS_HOME/bin:\$PATH"
EOF
ok "env fragment $ENV_SH"

LOCAL_BIN="${HOME}/.local/bin"
if mkdir -p "$LOCAL_BIN" 2>/dev/null; then
  if ln -sfn "$LAUNCHER" "$LOCAL_BIN/ai-tts" 2>/dev/null; then
    ok "symlink $LOCAL_BIN/ai-tts -> $LAUNCHER"
  else
    warn "could not symlink into $LOCAL_BIN (use: source $ENV_SH)"
  fi
else
  warn "could not create $LOCAL_BIN — source $ENV_SH to put ai-tts on PATH"
fi

# Config
CFG="$AI_TTS_HOME/config.json"
DENABLED="false"
if [[ "$ENABLE_DAEMON" == "1" ]]; then
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

step "Copying docs"
cp -f "$REPO_ROOT/docs/"*.md "$AI_TTS_HOME/docs/" 2>/dev/null || true
ok "docs → $AI_TTS_HOME/docs"

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
  Grok) write_grok_hooks ;;
  Claude) write_claude_hooks ;;
  Both) write_grok_hooks; write_claude_hooks ;;
esac

ui next-steps --launcher "$AI_TTS_BIN" --env-sh "$ENV_SH"
