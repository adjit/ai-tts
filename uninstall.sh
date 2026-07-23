#!/usr/bin/env bash
# Uninstall ai-tts on macOS / Linux (parity with uninstall.ps1).
# Usage:
#   ./uninstall.sh                 # Grok+Claude hooks + shared runtime (keep config)
#   ./uninstall.sh Both --remove-config --remove-markers
#   TARGET=Grok ./uninstall.sh
set -euo pipefail

TARGET="${1:-Both}"
shift || true
REMOVE_CONFIG=0
REMOVE_MARKERS=0
for a in "$@"; do
  case "$a" in
    --remove-config|-RemoveConfig) REMOVE_CONFIG=1 ;;
    --remove-markers|-RemoveMarkers) REMOVE_MARKERS=1 ;;
    *)
      echo "unknown arg: $a" >&2
      exit 2
      ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
AI_TTS_HOME="${AI_TTS_HOME:-$HOME/.ai-tts}"

t_lower="$(echo "$TARGET" | tr '[:upper:]' '[:lower:]')"
case "$t_lower" in
  grok|claude|both|shared) ;;
  *)
    echo "usage: $0 [Grok|Claude|Both|Shared] [--remove-config] [--remove-markers]" >&2
    exit 2
    ;;
esac

ARGS=(uninstall --target "$t_lower")
[[ "$REMOVE_CONFIG" == "1" ]] && ARGS+=(--remove-config)
[[ "$REMOVE_MARKERS" == "1" ]] && ARGS+=(--remove-markers)

if [[ -x "$AI_TTS_HOME/bin/ai-tts" ]]; then
  exec "$AI_TTS_HOME/bin/ai-tts" "${ARGS[@]}"
fi

export PYTHONPATH="${REPO_ROOT}/src/python${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON" -m ai_tts "${ARGS[@]}"
