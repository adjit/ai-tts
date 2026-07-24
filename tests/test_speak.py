from __future__ import annotations

import pytest

from ai_tts.speak import speak_text
from ai_tts.tts_rest import TtsError


def test_speak_text_rest(monkeypatch, isolated_home, write_config, sample_wav_bytes):
    write_config({"voice": "carina", "mode": "direct"})
    monkeypatch.setenv("XAI_API_KEY", "test-key")

    monkeypatch.setattr(
        "ai_tts.speak.synthesize_rest",
        lambda *a, **k: sample_wav_bytes,
    )
    played = []

    def capture(data: bytes):
        played.append(data)

    monkeypatch.setattr("ai_tts.speak.play_wav_bytes", capture)
    # Force REST path (skip stream attempt)
    meta = speak_text("hello world", transport="rest")
    assert meta["ok"] is True
    assert meta["transport"] == "rest"
    assert meta["voice"] == "carina"
    assert played and played[0] == sample_wav_bytes
    assert meta["bytes"] == len(sample_wav_bytes)
    assert "ttfa_ms" in meta


def test_speak_text_empty_raises(isolated_home, monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "k")
    with pytest.raises(TtsError, match="empty"):
        speak_text("   ")


def test_speak_text_missing_key(isolated_home, monkeypatch):
    # User may have XAI_API_KEY in Windows registry; force unset for this test.
    monkeypatch.setattr("ai_tts.speak.get_api_key", lambda: None)
    with pytest.raises(TtsError, match="XAI_API_KEY"):
        speak_text("hi", transport="rest")


def test_speak_auto_falls_back_from_stream(
    monkeypatch, isolated_home, write_config, sample_wav_bytes
):
    write_config({"voice": "eve"})
    monkeypatch.setenv("XAI_API_KEY", "k")
    monkeypatch.setattr("ai_tts.speak.streaming_available", lambda: True)

    def boom(*a, **k):
        raise TtsError("stream down")

    monkeypatch.setattr("ai_tts.speak.stream_and_play", boom)
    monkeypatch.setattr(
        "ai_tts.speak.synthesize_rest",
        lambda *a, **k: sample_wav_bytes,
    )
    monkeypatch.setattr("ai_tts.speak.play_wav_bytes", lambda data: None)
    meta = speak_text("hi", transport="auto")
    assert meta["transport"] == "rest-fallback"
    assert meta["voice"] == "eve"


def test_speak_stream_uses_stream_and_play(monkeypatch, isolated_home, write_config):
    write_config({"voice": "carina"})
    monkeypatch.setenv("XAI_API_KEY", "k")
    monkeypatch.setattr("ai_tts.speak.streaming_available", lambda: True)

    def fake_stream_play(*a, **k):
        return {
            "ok": True,
            "transport": "stream-play",
            "voice": "carina",
            "bytes": 4800,
            "play_mode": "stream",
            "ttfa_ms": 120,
            "synth_ms": 800,
            "play_ms": 0,
            "ms": 800,
        }

    monkeypatch.setattr("ai_tts.speak.stream_and_play", fake_stream_play)
    meta = speak_text("hi there", transport="stream")
    assert meta["transport"] == "stream-play"
    assert meta["ttfa_ms"] == 120
    assert meta["voice"] == "carina"
