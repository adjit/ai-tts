from __future__ import annotations

import platform
from pathlib import Path

import pytest

from ai_tts.play import PlaybackError, play_wav_bytes, play_wav_file, probe_players


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
