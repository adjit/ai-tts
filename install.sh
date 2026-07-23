#!/usr/bin/env bash
# Portable installer scaffold for macOS / Linux.
# Phase 1+: wires Grok (and optionally Claude) once the Python runtime exists.
set -euo pipefail

TARGET="${1:-Grok}"   # Grok | Claude | Both
VOICE="${VOICE:-carina}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_TTS_HOME="${AI_TTS_HOME:-$HOME/.ai-tts}"

echo "ai-tts install.sh (scaffold)"
echo "  target : $TARGET"
echo "  voice  : $VOICE"
echo "  home   : $AI_TTS_HOME"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 is required on macOS/Linux. Install Python 3.10+ and re-run." >&2
  exit 1
fi

PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "-> python3 $PY_VER"

mkdir -p "$AI_TTS_HOME/bin" "$AI_TTS_HOME/player"

# Config (do not clobber unless FORCE=1)
CFG="$AI_TTS_HOME/config.json"
if [[ ! -f "$CFG" || "${FORCE:-0}" == "1" ]]; then
  cat >"$CFG" <<EOF
{
  "voice": "$VOICE",
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
EOF
  echo "  OK wrote $CFG"
else
  echo "  ! keeping existing $CFG (FORCE=1 to overwrite)"
fi

# Copy docs + packaging sources for reference; runtime arrives in Phase 1
cp -f "$REPO_ROOT/config.example.json" "$AI_TTS_HOME/config.example.json" 2>/dev/null || true
mkdir -p "$AI_TTS_HOME/docs"
cp -f "$REPO_ROOT/docs/platforms.md" "$AI_TTS_HOME/docs/platforms.md" 2>/dev/null || true

# Playback probes (informational)
echo "-> playback probes"
case "$(uname -s)" in
  Darwin)
    if command -v afplay >/dev/null 2>&1; then echo "  OK afplay (macOS)"; else echo "  ! afplay missing"; fi
    ;;
  Linux)
    if command -v ffplay >/dev/null 2>&1; then echo "  OK ffplay"; \
    elif command -v paplay >/dev/null 2>&1; then echo "  OK paplay"; \
    elif command -v aplay >/dev/null 2>&1; then echo "  OK aplay"; \
    else echo "  ! no ffplay/paplay/aplay — install ffmpeg or pulseaudio-utils"; fi
    ;;
  *)
    echo "  ! unsupported uname: $(uname -s) — see docs/platforms.md"
    ;;
esac

echo ""
echo "macOS/Linux runtime is not fully shipped yet (Windows PowerShell path is production)."
echo "Plan: docs/platforms.md  |  next: Python speak core + Grok hooks in install.sh"
echo "Done (scaffold)."
