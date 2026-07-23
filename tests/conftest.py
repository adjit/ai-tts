"""Shared fixtures for ai-tts tests."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# Ensure src/python is importable without install
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "python"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def repo_root() -> Path:
    return ROOT


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point home + AI_TTS_HOME at a temp dir so tests never touch the real home."""
    home = tmp_path / "home"
    home.mkdir()
    ai = home / ".ai-tts"
    ai.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))  # Windows
    monkeypatch.setenv("AI_TTS_HOME", str(ai))
    # Clear API key unless a test sets it
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    return home


@pytest.fixture
def write_config(isolated_home: Path):
    def _write(data: dict) -> Path:
        path = Path(os.environ["AI_TTS_HOME"]) / "config.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path

    return _write


@pytest.fixture
def sample_wav_bytes() -> bytes:
    """Minimal valid silent WAV (very short)."""
    from ai_tts.wavutil import pcm_to_wav_bytes

    # 100 samples of silence, 16-bit mono
    return pcm_to_wav_bytes(b"\x00\x00" * 100, sample_rate=24000)
