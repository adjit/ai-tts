"""Per-directory TTS on/off markers for Grok and Claude."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


def normalize_cwd(cwd: str | None) -> str | None:
    if not cwd:
        return None
    return cwd.replace("\\", "/").rstrip("/").lower()


def dir_key(cwd: str) -> str:
    norm = normalize_cwd(cwd) or ""
    return hashlib.md5(norm.encode("utf-8")).hexdigest()


def marker_path(cwd: str, harness: str) -> Path:
    """harness: 'grok' | 'claude'"""
    root = Path.home() / f".{harness}" / ".tts-dirs"
    return root / dir_key(cwd)


def is_enabled(cwd: str, harness: str = "grok") -> bool:
    return marker_path(cwd, harness).is_file()


def set_enabled(cwd: str, enabled: bool, harness: str = "grok") -> Path:
    path = marker_path(cwd, harness)
    path.parent.mkdir(parents=True, exist_ok=True)
    if enabled:
        path.write_text("on", encoding="utf-8")
    elif path.is_file():
        path.unlink()
    return path


def toggle(cwd: str | None = None, harness: str = "grok") -> tuple[bool, str]:
    """Toggle marker for cwd. Returns (now_on, cwd)."""
    cwd = cwd or os.getcwd()
    now = not is_enabled(cwd, harness)
    set_enabled(cwd, now, harness)
    return now, cwd


def resolve_cwd_from_env_and_payload(payload: dict | None = None) -> str | None:
    payload = payload or {}
    for key in ("cwd", "workspaceRoot", "workspace_root"):
        v = payload.get(key)
        if v:
            return str(v)
    for env in ("GROK_WORKSPACE_ROOT", "CLAUDE_PROJECT_DIR", "PWD"):
        v = os.environ.get(env)
        if v:
            return v
    return os.getcwd()
