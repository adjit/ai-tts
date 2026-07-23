"""Optional live tests against xAI (skipped unless RUN_LIVE_TTS=1 and key set)."""

from __future__ import annotations

import os

import pytest

from ai_tts.speak import speak_text

pytestmark = pytest.mark.live


def _live_enabled() -> bool:
    return os.environ.get("RUN_LIVE_TTS", "").strip() in {"1", "true", "yes"}


@pytest.mark.skipif(not _live_enabled(), reason="set RUN_LIVE_TTS=1 to run live TTS")
@pytest.mark.skipif(not os.environ.get("XAI_API_KEY"), reason="XAI_API_KEY not set")
def test_live_speak_rest(isolated_home, write_config):
    write_config({"voice": "carina", "mode": "direct"})
    # Real network + real audio device — may fail headless without speakers
    meta = speak_text("ai-tts live test.", transport="rest")
    assert meta["ok"] is True
    assert meta["bytes"] > 0
