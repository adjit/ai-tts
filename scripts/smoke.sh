#!/usr/bin/env bash
# Product smoke: probe + hook-state + optional speak (live API).
# Does not require an agent harness. Safe to run from a repo checkout.
#
# Usage:
#   ./scripts/smoke.sh
#   ./scripts/smoke.sh --speak          # force speak attempt (fails if no key)
#   SKIP_SPEAK=1 ./scripts/smoke.sh     # never call speak
#
# Exit: 0 if local checks pass (speak skipped without key is OK unless --speak).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

FORCE_SPEAK=0
SKIP_SPEAK="${SKIP_SPEAK:-0}"
for a in "$@"; do
  case "$a" in
    --speak) FORCE_SPEAK=1 ;;
    --help|-h)
      sed -n '2,12p' "$0"
      exit 0
      ;;
  esac
done

PY=()
if command -v python3 >/dev/null 2>&1; then
  PY=(python3)
elif command -v python >/dev/null 2>&1; then
  PY=(python)
else
  echo "error: python3/python not found" >&2
  exit 1
fi

# Prefer installed launcher; fall back to repo checkout module.
if [[ -n "${AI_TTS_BIN:-}" && -x "${AI_TTS_BIN}" ]]; then
  run() { "${AI_TTS_BIN}" "$@"; }
  LAUNCHER="$AI_TTS_BIN"
elif [[ -x "${HOME}/.ai-tts/bin/ai-tts" ]]; then
  run() { "${HOME}/.ai-tts/bin/ai-tts" "$@"; }
  LAUNCHER="${HOME}/.ai-tts/bin/ai-tts"
elif command -v ai-tts >/dev/null 2>&1; then
  run() { ai-tts "$@"; }
  LAUNCHER="$(command -v ai-tts)"
else
  export PYTHONPATH="${ROOT}/src/python${PYTHONPATH:+:$PYTHONPATH}"
  run() { "${PY[@]}" -m ai_tts "$@"; }
  LAUNCHER="${PY[*]} -m ai_tts"
fi

echo "==> ai-tts product smoke"
echo "    launcher: $LAUNCHER"
echo ""

echo "-> probe"
if ! run probe; then
  echo "FAIL: probe" >&2
  exit 1
fi
echo ""

CWD_JSON="$("${PY[@]}" -c 'import json, os; print(json.dumps(os.getcwd()))')"
echo "-> hook-state (cwd=$PWD, harness=grok)"
if ! echo "{\"cwd\":${CWD_JSON},\"sessionId\":\"smoke\"}" | run hook-state --harness grok; then
  echo "FAIL: hook-state" >&2
  exit 1
fi
echo ""

if [[ "$SKIP_SPEAK" == "1" ]]; then
  echo "-> speak: skipped (SKIP_SPEAK=1)"
elif [[ -n "${XAI_API_KEY:-}" ]]; then
  echo "-> speak (REST)"
  if ! run speak --transport rest "ai-tts smoke. If you can hear this, playback works."; then
    echo "FAIL: speak" >&2
    exit 1
  fi
elif [[ "$FORCE_SPEAK" -eq 1 ]]; then
  echo "error: --speak requires XAI_API_KEY" >&2
  exit 1
else
  echo "-> speak: skipped (XAI_API_KEY not set; export it or pass --speak to require)"
fi

echo ""
echo "OK smoke complete."
echo "Next: live agent E2E is still manual — /tts in a project, then confirm <say> audio."
