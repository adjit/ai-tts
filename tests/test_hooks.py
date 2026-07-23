from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_tts.hooks import (
    extract_assistant_text,
    hook_state,
    hook_stop,
    last_say_block,
)
from ai_tts.markers import set_enabled


def test_last_say_block_picks_last():
    text = "hello <say>first</say> mid <say>second line</say>"
    assert last_say_block(text) == "second line"
    assert last_say_block("no tags") is None
    assert last_say_block(None) is None
    assert last_say_block("<say>  spaced  </say>") == "spaced"


def test_extract_from_last_assistant_message():
    payload = {"lastAssistantMessage": "Done.\n\n<say>All good.</say>"}
    assert "All good" in (extract_assistant_text(payload) or "")


def test_extract_from_transcript_jsonl(tmp_path: Path):
    tp = tmp_path / "transcript.jsonl"
    lines = [
        json.dumps({"type": "user", "message": {"content": "hi"}}),
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Working..."},
                        {"type": "tool_use", "id": "1"},
                    ]
                },
            }
        ),
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "Final\n<say>Spoken.</say>"}]
                },
            }
        ),
    ]
    tp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    text = extract_assistant_text({"transcript_path": str(tp)})
    assert text is not None
    assert "Spoken" in text
    assert last_say_block(text) == "Spoken."


def test_hook_state_emits_json(isolated_home, monkeypatch, capsys):
    cwd = str(isolated_home / "p")
    Path(cwd).mkdir()
    set_enabled(cwd, True, "grok")
    monkeypatch.setattr(
        "ai_tts.hooks.read_stdin_json",
        lambda: {"cwd": cwd},
    )
    code = hook_state("grok")
    assert code == 0
    out = capsys.readouterr().out
    assert "Voice output is ON" in out
    # JSON object present
    assert '"additionalContext"' in out or "additionalContext" in out


def test_hook_state_off(isolated_home, monkeypatch, capsys):
    cwd = str(isolated_home / "p2")
    Path(cwd).mkdir()
    monkeypatch.setattr(
        "ai_tts.hooks.read_stdin_json",
        lambda: {"cwd": cwd},
    )
    hook_state("grok")
    assert "OFF" in capsys.readouterr().out


def test_hook_stop_skips_when_disabled(isolated_home, monkeypatch):
    cwd = str(isolated_home / "off")
    Path(cwd).mkdir()
    monkeypatch.setattr(
        "ai_tts.hooks.read_stdin_json",
        lambda: {
            "reason": "end_turn",
            "cwd": cwd,
            "lastAssistantMessage": "<say>Should not speak</say>",
        },
    )
    called = []

    def boom(*a, **k):
        called.append(1)
        raise AssertionError("should not spawn")

    monkeypatch.setattr("ai_tts.hooks.subprocess.Popen", boom)
    assert hook_stop("grok") == 0
    assert called == []


def test_hook_stop_skips_non_end_turn(isolated_home, monkeypatch):
    cwd = str(isolated_home / "on")
    Path(cwd).mkdir()
    set_enabled(cwd, True, "grok")
    monkeypatch.setattr(
        "ai_tts.hooks.read_stdin_json",
        lambda: {
            "reason": "shutdown",
            "cwd": cwd,
            "lastAssistantMessage": "<say>x</say>",
        },
    )
    monkeypatch.setattr(
        "ai_tts.hooks.subprocess.Popen",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no")),
    )
    assert hook_stop("grok") == 0


def test_hook_stop_detaches_speak(isolated_home, monkeypatch):
    cwd = str(isolated_home / "on2")
    Path(cwd).mkdir()
    set_enabled(cwd, True, "grok")
    monkeypatch.setattr(
        "ai_tts.hooks.read_stdin_json",
        lambda: {
            "reason": "end_turn",
            "cwd": cwd,
            "lastAssistantMessage": "ok\n<say>Hello voice.</say>",
        },
    )
    pops = []

    class FakeProc:
        pass

    def fake_popen(args=None, **kwargs):
        pops.append((args, kwargs))
        return FakeProc()

    monkeypatch.setattr("ai_tts.hooks.subprocess.Popen", fake_popen)
    assert hook_stop("grok") == 0
    assert len(pops) == 1
    args = pops[0][0]
    assert "speak" in args
    assert any("Hello voice" in str(a) for a in args)
