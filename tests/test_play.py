from __future__ import annotations

import platform
from pathlib import Path

import pytest

from ai_tts.play import (
    PlaybackError,
    open_pcm_player,
    play_wav_bytes,
    play_wav_file,
    probe_players,
    stream_play_available,
)


def test_probe_players_returns_list():
    players = probe_players()
    assert isinstance(players, list)
    # At least one backend is expected on normal CI images; allow empty on exotic hosts
    # but function must not raise.
    system = platform.system()
    if system == "Windows":
        assert "winsound" in players
    elif system == "Darwin":
        assert "afplay" in players or "ffplay" in players
    # Linux docker may only have nothing without alsa — still a list


def test_play_wav_file_missing(tmp_path):
    with pytest.raises(PlaybackError):
        play_wav_file(tmp_path / "nope.wav")


def test_play_wav_bytes_empty():
    with pytest.raises(PlaybackError):
        play_wav_bytes(b"")


def test_play_wav_bytes_invokes_player(monkeypatch, sample_wav_bytes):
    called = []

    def fake_file(path):
        called.append(Path(path).read_bytes())

    monkeypatch.setattr("ai_tts.play.play_wav_file", fake_file)
    play_wav_bytes(sample_wav_bytes)
    assert called and called[0] == sample_wav_bytes


def test_open_pcm_player_buffer_fallback(monkeypatch):
    """When no stream backend is forced unavailable, buffer player still works."""
    monkeypatch.setattr("ai_tts.play.shutil.which", lambda name: None)
    monkeypatch.setattr("ai_tts.play._winmm_available", lambda: False)
    monkeypatch.setattr("ai_tts.play.platform.system", lambda: "Linux")

    player = open_pcm_player(24000)
    assert player.mode == "buffer"
    played = []
    monkeypatch.setattr(
        "ai_tts.play.play_wav_bytes",
        lambda data: played.append(data),
    )
    player.write(b"\x00\x00" * 50)
    player.close()
    assert played and played[0][:4] == b"RIFF"


def test_stream_play_available_is_bool():
    assert isinstance(stream_play_available(), bool)
