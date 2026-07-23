from __future__ import annotations

from ai_tts.__main__ import main


def test_help_exits_zero():
    assert main(["--help"]) == 0
    assert main([]) == 0


def test_speak_missing_text():
    assert main(["speak"]) == 2


def test_probe(isolated_home, write_config, monkeypatch, capsys):
    write_config({"voice": "carina"})
    monkeypatch.setenv("XAI_API_KEY", "k")
    assert main(["probe"]) == 0
    out = capsys.readouterr().out
    assert "config:" in out
    assert "players:" in out
    assert "XAI_API_KEY: set" in out


def test_toggle_cli(isolated_home, monkeypatch, capsys):
    proj = isolated_home / "cli-proj"
    proj.mkdir()
    monkeypatch.chdir(proj)
    assert main(["toggle", "--harness", "grok"]) == 0
    assert "TTS ON" in capsys.readouterr().out
    assert main(["toggle", "--harness", "grok"]) == 0
    assert "TTS OFF" in capsys.readouterr().out


def test_speak_cli_uses_speak_module(monkeypatch, isolated_home, write_config, capsys):
    write_config({"mode": "direct"})
    monkeypatch.setenv("XAI_API_KEY", "k")
    calls: list[str] = []

    def fake_speak(text, **kwargs):
        calls.append(text)
        return {
            "ok": True,
            "transport": "rest",
            "voice": "carina",
            "ms": 5,
            "synth_ms": 4,
            "play_ms": 1,
            "bytes": 9,
        }

    monkeypatch.setattr("ai_tts.speak.speak_text", fake_speak)
    assert main(["speak", "cli-hello"]) == 0
    assert calls == ["cli-hello"]
    assert "ok" in capsys.readouterr().out
