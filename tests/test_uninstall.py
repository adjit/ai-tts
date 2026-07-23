from __future__ import annotations

from pathlib import Path

from ai_tts.__main__ import main
from ai_tts.uninstall import uninstall


def test_uninstall_removes_hooks_and_keeps_config(isolated_home, monkeypatch):
    home = isolated_home
    ai = Path(__import__("os").environ["AI_TTS_HOME"])
    (ai / "bin").mkdir(parents=True)
    (ai / "lib" / "ai_tts").mkdir(parents=True)
    (ai / "config.json").write_text('{"voice":"carina"}', encoding="utf-8")
    (ai / "env.sh").write_text("export PATH=...\n", encoding="utf-8")

    grok_hooks = home / ".grok" / "hooks"
    grok_hooks.mkdir(parents=True)
    (grok_hooks / "tts.json").write_text("{}", encoding="utf-8")
    skill = home / ".grok" / "skills" / "tts"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("x", encoding="utf-8")
    (home / ".grok" / "rules").mkdir(parents=True)
    (home / ".grok" / "rules" / "voice-tts.md").write_text("r", encoding="utf-8")
    markers = home / ".grok" / ".tts-dirs"
    markers.mkdir(parents=True)
    (markers / "abc").write_text("on", encoding="utf-8")

    local_bin = home / ".local" / "bin"
    local_bin.mkdir(parents=True)
    link = local_bin / "ai-tts"
    link.symlink_to(ai / "bin" / "ai-tts") if hasattr(link, "symlink_to") else link.write_text(
        "x", encoding="utf-8"
    )
    # ensure target exists for resolve
    (ai / "bin" / "ai-tts").write_text("#!/bin/sh\n", encoding="utf-8")
    if link.is_file() and not link.is_symlink():
        pass
    else:
        try:
            link.unlink()
        except OSError:
            pass
        link.symlink_to(ai / "bin" / "ai-tts")

    removed = uninstall(target="both", remove_config=False, remove_markers=False)
    assert any("tts.json" in p for p in removed)
    assert (ai / "config.json").is_file()
    assert not (grok_hooks / "tts.json").exists()
    assert markers.is_dir()  # markers kept

    removed2 = uninstall(target="grok", remove_config=False, remove_markers=True)
    assert not markers.exists() or any(".tts-dirs" in p for p in removed2)


def test_uninstall_remove_config(isolated_home):
    ai = Path(__import__("os").environ["AI_TTS_HOME"])
    (ai / "config.json").write_text("{}", encoding="utf-8")
    uninstall(target="shared", remove_config=True)
    assert not ai.exists()


def test_uninstall_cli(isolated_home, capsys):
    ai = Path(__import__("os").environ["AI_TTS_HOME"])
    (ai / "docs").mkdir(parents=True)
    (ai / "docs" / "x.md").write_text("d", encoding="utf-8")
    assert main(["uninstall", "--target", "shared"]) == 0
    out = capsys.readouterr().out
    assert "uninstall" in out.lower()
