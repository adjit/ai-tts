#!/usr/bin/env bash
# Run unit tests locally or in Docker (Linux).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DOCKER=0
LIVE=0
COVERAGE=0
for a in "$@"; do
  case "$a" in
    --docker) DOCKER=1 ;;
    --live) LIVE=1 ;;
    --coverage) COVERAGE=1 ;;
  esac
done

if [[ "$DOCKER" == "1" ]]; then
  echo "-> Docker tests (Linux)"
  docker compose -f docker-compose.test.yml build
  if [[ "$LIVE" == "1" ]]; then
    : "${XAI_API_KEY:?XAI_API_KEY required for --live}"
    docker compose -f docker-compose.test.yml run --rm \
      -e RUN_LIVE_TTS=1 -e "XAI_API_KEY=$XAI_API_KEY" \
      test pytest -q -m live
  else
    docker compose -f docker-compose.test.yml run --rm test
  fi
  exit 0
fi

echo "-> Local pytest"
export PYTHONPATH="$ROOT/src/python${PYTHONPATH:+:$PYTHONPATH}"
python3 -m pip install -q -r requirements-dev.txt
args=(-q)
if [[ "$LIVE" != "1" ]]; then
  args+=(--ignore=tests/test_live_optional.py)
else
  args+=(-m live)
fi
if [[ "$COVERAGE" == "1" ]]; then
  args=(--cov=ai_tts --cov-report=term-missing "${args[@]}")
fi
python3 -m pytest "${args[@]}"
