# Testing

## What we test

| Layer | How |
|-------|-----|
| Config, markers, WAV, hooks, CLI | Unit tests (no network) |
| REST TTS client | Mocked `urllib` |
| Speak orchestration | Mocked synth + play |
| TCP daemon | Real localhost sockets; synth mocked |
| Live xAI API | Opt-in only (`RUN_LIVE_TTS=1`) |
| Product path (probe / hooks / speak) | `scripts/smoke.sh` / `scripts/smoke.ps1` |
| doctor / config / status / uninstall | Unit tests (`test_doctor`, `test_cli_config_status`, `test_uninstall`) |
| Linux environment | Docker image + compose |
| Full agent `/tts` → `<say>` → audio | **Manual** (Grok/Claude session) |

Tests isolate `HOME` / `AI_TTS_HOME` under a temp directory so they never write your real `~/.grok` markers.

## Quality ladder (definition of done)

Use the **fastest** gate that covers your change. Higher rungs include lower ones.

| Rung | Command | Proves | When required |
|------|---------|--------|----------------|
| **1. Unit** | `./scripts/run-tests.sh` | Logic, CLI, mocks; offline | Any Python / test / hook change |
| **2. Product smoke** | `./scripts/smoke.sh` | probe + hook-state; speak if key set | Install, hooks, speak path, packaging |
| **3. Live pytest** | `RUN_LIVE_TTS=1 ./scripts/run-tests.sh --live` | Real xAI REST + local player | TTS client / voice regressions (optional) |
| **4. Agent E2E** | New session → `/tts` → hear speech | Rules, hooks, detached env | Claims about “works in Grok/Claude” |

**PR default:** rung 1 green. Rung 2 without `XAI_API_KEY` is still useful (probe + hook-state).

## Local unit suite (any OS with Python 3.10+)

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

## Product smoke (no agent harness)

Cross-platform Python path (not the deprecated PowerShell `speak.ps1`):

```bash
chmod +x scripts/smoke.sh
./scripts/smoke.sh                 # probe + hook-state; speak if XAI_API_KEY set
./scripts/smoke.sh --speak         # require speak (fails without key)
SKIP_SPEAK=1 ./scripts/smoke.sh    # never speak
```

```powershell
.\scripts\smoke.ps1
.\scripts\smoke.ps1 -Speak
.\scripts\smoke.ps1 -SkipSpeak
```

`examples/manual-smoke.ps1` is **deprecated** and forwards to `scripts/smoke.ps1`.

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
# or
RUN_LIVE_TTS=1 XAI_API_KEY=... ./scripts/run-tests.sh --live
```

Needs network and a working audio device (may fail in headless CI).

## CI

GitHub Actions (`.github/workflows/test.yml`):

- Matrix: Ubuntu / Windows / macOS × Python 3.11 & 3.12  
- Separate job: Docker Linux build + pytest  
- Live tests are **not** run in CI (no secrets required for the default job)

## Adding tests

- Put files under `tests/test_*.py`
- Use `isolated_home` fixture for config/markers
- Mock `urllib` / `speak_text` / `play_wav_bytes` — do not call xAI in default suite
- Prefer extending unit tests over new live calls
