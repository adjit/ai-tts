"""Uninstall helpers (shared runtime + harness files)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

from .config import home_dir


def _rm(path: Path, removed: list[str]) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, ignore_errors=True)
    else:
        try:
            path.unlink()
        except OSError:
            pass
    removed.append(str(path))


def uninstall(
    *,
    target: str = "both",
    remove_config: bool = False,
    remove_markers: bool = False,
) -> list[str]:
    """Remove install artifacts. Returns list of removed paths."""
    target = (target or "both").lower()
    removed: list[str] = []
    home = Path.home()
    ai = home_dir()

    if target in {"grok", "both"}:
        for p in (
            home / ".grok" / "hooks" / "tts.json",
            home / ".grok" / "hooks" / "tts-state.ps1",
            home / ".grok" / "hooks" / "tts-stop.ps1",
            home / ".grok" / "skills" / "tts",
            home / ".grok" / "rules" / "voice-tts.md",
            home / ".grok" / "speak.ps1",
        ):
            _rm(p, removed)
        if remove_markers:
            _rm(home / ".grok" / ".tts-dirs", removed)

    if target in {"claude", "both"}:
        for p in (
            home / ".claude" / "hooks" / "tts-state.ps1",
            home / ".claude" / "hooks" / "tts-stop.ps1",
            home / ".claude" / "skills" / "tts",
            home / ".claude" / "rules" / "voice-tts.md",
            home / ".claude" / "speak.ps1",
        ):
            _rm(p, removed)
        if remove_markers:
            _rm(home / ".claude" / ".tts-dirs", removed)

    # Local bin symlink if it points into our home
    local_link = home / ".local" / "bin" / "ai-tts"
    if local_link.is_symlink() or local_link.is_file():
        try:
            resolved = local_link.resolve()
            if str(ai) in str(resolved) or resolved == (ai / "bin" / "ai-tts").resolve():
                _rm(local_link, removed)
        except OSError:
            pass

    if target in {"shared", "both"} or remove_config:
        if remove_config:
            _rm(ai, removed)
        else:
            for p in (
                ai / "bin",
                ai / "lib",
                ai / "docs",
                ai / "scripts",
                ai / "speak.ps1",
                ai / "speak-core.ps1",
                ai / "common.ps1",
                ai / "daemon.ps1",
                ai / "daemon.pid",
                ai / "daemon.log",
                ai / "env.sh",
                ai / "claude-settings.hooks.snippet.json",
            ):
                _rm(p, removed)
            # keep config.json unless remove_config

    return removed


def format_uninstall_report(removed: Iterable[str], *, notes: list[str] | None = None) -> str:
    lines = ["ai-tts uninstall"]
    items = list(removed)
    if not items:
        lines.append("  (nothing removed)")
    else:
        for p in items:
            lines.append(f"  removed {p}")
    for n in notes or []:
        lines.append(f"  note: {n}")
    lines.append("Done.")
    return "\n".join(lines) + "\n"
