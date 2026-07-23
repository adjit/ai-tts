# Testing

## What we test

| Layer | How |
|-------|-----|
| Config, markers, WAV, hooks, CLI | Unit tests (no network) |
| REST TTS client | Mocked `urllib` |
| Speak orchestration | Mocked synth + play |
| TCP daemon | Real localhost sockets; synth mocked |
| Live xAI API | Opt-in only (`RUN_LIVE_TTS=1`) |
| Linux environment | Docker image + compose |

Tests isolate `HOME` / `AI_TTS_HOME` under a temp directory so they never write your real `~/.grok` markers.

## Local (any OS with Python 3.10+)

```bash
pip install -r requirements-dev.txt
export PYTHONPATH=src/python   # Windows: set PYTHONPATH=src\python
pytest -q --ignore=tests/test_live_optional.py
```

Helpers:

```powershell
.\scripts\run-tests.ps1
.\scripts\run-tests.ps1 -Coverage
```

```bash
./scripts/run-tests.sh
./scripts/run-tests.sh --coverage
```

## Docker (Linux, independent of host)

Requires Docker Desktop (or engine) **running**.

```powershell
.\scripts\run-tests.ps1 -Docker
```

```bash
./scripts/run-tests.sh --docker
# or
docker compose -f docker-compose.test.yml build
docker compose -f docker-compose.test.yml run --rm test
```

Image: `python:3.12-slim` + `ffmpeg` (for `ffplay` player probe).

## Live API (optional)

```bash
RUN_LIVE_TTS=1 XAI_API_KEY=... pytest -q -m live
```

Needs network and a working audio device (may fail in headless CI).

## CI

GitHub Actions (`.github/workflows/test.yml`):

- Matrix: Ubuntu / Windows / macOS × Python 3.11 & 3.12  
- Separate job: Docker Linux build + pytest  

## Adding tests

- Put files under `tests/test_*.py`
- Use `isolated_home` fixture for config/markers
- Mock `urllib` / `speak_text` / `play_wav_bytes` — do not call xAI in default suite
