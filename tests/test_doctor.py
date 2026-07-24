from __future__ import annotations

from pathlib import Path

from ai_tts.__main__ import main
from ai_tts.doctor import (
    Check,
    check_api_key,
    check_players,
    doctor_exit_code,
    format_report,
    run_checks,
)


def test_doctor_exit_code_critical():
    ok = [Check("a", True, "fine")]
    assert doctor_exit_code(ok) == 0
    warn = [Check("a", False, "x", hint="h", critical=False)]
    assert doctor_exit_code(warn) == 0
    bad = [Check("a", False, "x", critical=True)]
    assert doctor_exit_code(bad) == 1


def test_format_report_includes_hints():
    results = [
        Check("api_key", False, "MISSING", hint="export XAI_API_KEY=...", critical=True),
        Check("players", True, "afplay"),
    ]
    text = format_report(results)
    assert "[FAIL] api_key" in text
    assert "export XAI_API_KEY" in text
    assert "[PASS] players" in text
    assert "critical failure" in text


def test_check_api_key_missing(isolated_home, monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setattr("ai_tts.doctor.get_api_key", lambda: None)
    c = check_api_key()
    assert c.ok is False
    assert c.critical is True
    assert "console.x.ai" in c.hint


def test_check_api_key_set(isolated_home, monkeypatch):
    monkeypatch.setattr("ai_tts.doctor.get_api_key", lambda: "xai-test")
    c = check_api_key()
    assert c.ok is True


def test_check_players_none(monkeypatch):
    monkeypatch.setattr("ai_tts.doctor.probe_players", lambda: [])
    c = check_players()
    assert c.ok is False
    assert c.critical is True


def test_doctor_cli_fails_without_key(isolated_home, write_config, monkeypatch, capsys):
    write_config({"voice": "carina"})
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setattr("ai_tts.doctor.get_api_key", lambda: None)
    monkeypatch.setattr("ai_tts.doctor.probe_players", lambda: ["afplay"])
    code = main(["doctor"])
    out = capsys.readouterr().out
    assert code == 1
    assert "api_key" in out
    assert "FAIL" in out


def test_doctor_cli_passes_with_key_and_player(
    isolated_home, write_config, monkeypatch, capsys
):
    write_config({"voice": "carina"})
    # Layout under isolated home
    home = Path(isolated_home)  # user home
    ai = Path(__import__("os").environ["AI_TTS_HOME"])
    (ai / "lib" / "ai_tts").mkdir(parents=True, exist_ok=True)
    (ai / "bin").mkdir(parents=True, exist_ok=True)
    (ai / "bin" / "ai-tts").write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr("ai_tts.doctor.get_api_key", lambda: "k")
    monkeypatch.setattr("ai_tts.doctor.probe_players", lambda: ["afplay"])
    monkeypatch.setattr("ai_tts.doctor.streaming_available", lambda: True)
    # PATH includes bin
    monkeypatch.setenv("PATH", str(ai / "bin") + __import__("os").pathsep + __import__("os").environ.get("PATH", ""))
    # Grok hooks
    grok_hooks = home / ".grok" / "hooks"
    grok_hooks.mkdir(parents=True, exist_ok=True)
    (grok_hooks / "tts.json").write_text(
        '{"hooks":{"Stop":[{"hooks":[{"command":"ai-tts hook-stop --harness grok"}]}]}}',
        encoding="utf-8",
    )
    code = main(["doctor"])
    out = capsys.readouterr().out
    assert code == 0, out
    assert "all checks passed" in out or "OK with" in out


def test_check_grok_hooks_detects_bom(isolated_home, tmp_path, monkeypatch):
    from ai_tts.doctor import check_grok_hooks

    home = Path(isolated_home)
    grok_hooks = home / ".grok" / "hooks"
    grok_hooks.mkdir(parents=True, exist_ok=True)
    body = b'{"hooks":{"Stop":[{"hooks":[{"command":"ai-tts.cmd hook-stop"}]}]}}'
    (grok_hooks / "tts.json").write_bytes(b"\xef\xbb\xbf" + body)
    c = check_grok_hooks()
    assert c.ok is False
    assert "BOM" in c.detail


def test_setup_alias(isolated_home, write_config, monkeypatch, capsys):
    write_config({})
    monkeypatch.setattr("ai_tts.doctor.get_api_key", lambda: None)
    monkeypatch.setattr("ai_tts.doctor.probe_players", lambda: ["x"])
    assert main(["setup"]) == 1
    out = capsys.readouterr().out
    assert "api_key" in out
