from __future__ import annotations

from pathlib import Path

from ai_tts.markers import (
    dir_key,
    is_enabled,
    normalize_cwd,
    resolve_cwd_from_env_and_payload,
    set_enabled,
    toggle,
)


def test_normalize_cwd_slashes_and_case():
    assert normalize_cwd(r"C:\Users\Foo\Project\\") == "c:/users/foo/project"
    assert normalize_cwd("/home/me/proj/") == "/home/me/proj"
    assert normalize_cwd(None) is None
    assert normalize_cwd("") is None


def test_dir_key_stable_across_slash_styles():
    a = dir_key(r"C:\Work\Repo")
    b = dir_key("C:/Work/Repo/")
    c = dir_key("c:/work/repo")
    assert a == b == c
    assert len(a) == 32  # md5 hex


def test_toggle_and_enable(isolated_home: Path):
    cwd = str(isolated_home / "proj")
    Path(cwd).mkdir()
    assert not is_enabled(cwd, "grok")
    set_enabled(cwd, True, "grok")
    assert is_enabled(cwd, "grok")
    # Claude harness is independent
    assert not is_enabled(cwd, "claude")
    on, got = toggle(cwd, "grok")
    assert on is False
    assert got == cwd
    assert not is_enabled(cwd, "grok")


def test_resolve_cwd_prefers_payload(monkeypatch, isolated_home: Path):
    monkeypatch.setenv("PWD", str(isolated_home / "from-pwd"))
    assert resolve_cwd_from_env_and_payload({"cwd": "/from/payload"}) == "/from/payload"
    assert (
        resolve_cwd_from_env_and_payload({"workspaceRoot": "/ws"}) == "/ws"
    )
    assert resolve_cwd_from_env_and_payload({}) == str(isolated_home / "from-pwd")
