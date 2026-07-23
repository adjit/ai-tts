from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_tts.__main__ import main
from ai_tts.cli_config import set_config_value
from ai_tts.config import load_config
from ai_tts.markers import set_enabled
from ai_tts.voices import KNOWN_VOICES, list_known_voices


def test_config_show(isolated_home, write_config, capsys):
    write_config({"voice": "eve", "mode": "direct", "speed": 1.2})
    assert main(["config"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["voice"] == "eve"
    assert data["speed"] == 1.2


def test_config_set_voice(isolated_home, write_config, capsys):
    write_config({"voice": "carina"})
    assert main(["config", "set", "voice", "leo"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["voice"] == "leo"
    assert load_config().voice == "leo"


def test_config_set_speed_and_mode(isolated_home, write_config):
    write_config({"mode": "direct"})
    set_config_value("speed", "1.25")
    assert load_config().speed == 1.25
    set_config_value("mode", "daemon")
    cfg = load_config()
    assert cfg.mode == "daemon"
    assert cfg.daemon_enabled is True
    set_config_value("mode", "direct")
    cfg = load_config()
    assert cfg.mode == "direct"
    assert cfg.daemon_enabled is False


def test_config_set_bad_key(isolated_home, write_config, capsys):
    write_config({})
    assert main(["config", "set", "nope", "x"]) == 2
    assert "unknown key" in capsys.readouterr().err


def test_config_set_missing_value(isolated_home, capsys):
    assert main(["config", "set", "voice"]) == 2


def test_voices_cli(capsys):
    assert main(["voices"]) == 0
    out = capsys.readouterr().out
    assert "carina" in out
    assert "leo" in out
    assert len(list_known_voices()) == len(KNOWN_VOICES)


def test_status_off(isolated_home, write_config, monkeypatch, capsys):
    write_config({"voice": "ara"})
    proj = isolated_home / "proj-a"
    proj.mkdir()
    monkeypatch.chdir(proj)
    assert main(["status", "--harness", "grok"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["tts"] == "off"
    assert data["voice"] == "ara"
    assert data["daemon"] in {"up", "down"}


def test_status_on(isolated_home, write_config, monkeypatch, capsys):
    write_config({"voice": "carina"})
    proj = isolated_home / "proj-b"
    proj.mkdir()
    set_enabled(str(proj), True, "grok")
    monkeypatch.chdir(proj)
    assert main(["status"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["tts"] == "on"
    assert data["cwd"] == str(proj) or Path(data["cwd"]).resolve() == proj.resolve()
