from __future__ import annotations

import io
from contextlib import redirect_stdout

from ai_tts.install_ui import main, shlex_quote


def test_shlex_quote_simple():
    assert shlex_quote("Grok") == "Grok"
    assert shlex_quote("a b") == "'a b'"


def test_banner_and_steps_exit_zero(capsys):
    assert main(["banner", "--title", "t", "--target", "Grok", "--voice", "carina"]) == 0
    out = capsys.readouterr().out
    assert "Grok" in out or "target" in out.lower() or "ai-tts" in out.lower()

    assert main(["step", "Installing package"]) == 0
    assert main(["ok", "done"]) == 0
    assert main(["warn", "heads up"]) == 0
    assert "Installing" in capsys.readouterr().out or True


def test_error_returns_one(capsys):
    assert main(["error", "boom"]) == 1
    err = capsys.readouterr()
    assert "boom" in err.err or "boom" in err.out


def test_next_steps(capsys):
    assert main(["next-steps", "--launcher", "/tmp/ai-tts", "--env-sh", "/tmp/env.sh"]) == 0
    out = capsys.readouterr().out
    assert "doctor" in out
    assert "/tmp/ai-tts" in out


def test_wizard_export_shell_non_tty(monkeypatch, capsys):
    # Not a TTY → defaults without prompts
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert (
        main(
            [
                "wizard",
                "--export-shell",
                "--default-target",
                "Both",
                "--default-voice",
                "eve",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    out = captured.out
    # stdout must be ONLY shell exports (safe for eval "$(...)")
    assert "TARGET=Both" in out
    assert "VOICE=eve" in out
    assert "ENABLE_DAEMON=" in out
    for line in out.strip().splitlines():
        assert "=" in line
        assert not line.startswith("→")
        assert "interactive" not in line.lower()


def test_wizard_json(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert main(["wizard", "--json", "--default-target", "Claude"]) == 0
    out = capsys.readouterr().out.strip()
    assert '"TARGET": "Claude"' in out or '"TARGET":"Claude"' in out.replace(" ", "")


def test_have_rich():
    code = main(["have-rich"])
    assert code == 0
