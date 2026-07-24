"""Post-install health checks with fix hints (read-only)."""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .config import get_api_key, home_dir, load_config
from .play import probe_players
from .tts_stream import streaming_available


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    hint: str = ""
    critical: bool = False


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def check_python() -> Check:
    ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    ok = sys.version_info >= (3, 10)
    return Check(
        name="python",
        ok=ok,
        detail=f"{sys.executable} ({ver})",
        hint="Install Python 3.10+ and re-run install." if not ok else "",
        critical=True,
    )


def check_package_layout() -> Check:
    home = home_dir()
    lib = home / "lib" / "ai_tts"
    # Also OK when running from a checkout via PYTHONPATH (no install yet)
    pkg_ok = lib.is_dir() or bool(__import__("ai_tts").__file__)
    bin_unix = home / "bin" / "ai-tts"
    bin_win = home / "bin" / "ai-tts.cmd"
    launcher = bin_unix if bin_unix.is_file() else bin_win if bin_win.is_file() else None
    if lib.is_dir() and launcher:
        return Check(
            name="install_layout",
            ok=True,
            detail=f"home={home} launcher={launcher}",
        )
    if pkg_ok and not launcher:
        return Check(
            name="install_layout",
            ok=True,
            detail=f"package importable; no launcher under {home}/bin (checkout mode OK)",
            hint=f"Run install.sh / install.ps1 to install launcher under {home}.",
        )
    return Check(
        name="install_layout",
        ok=False,
        detail=f"missing package under {lib}",
        hint="From the repo: ./install.sh Grok   or   .\\install.ps1 -Target Grok",
        critical=True,
    )


def check_api_key() -> Check:
    key = get_api_key()
    if key:
        return Check(name="api_key", ok=True, detail="XAI_API_KEY is set")
    if os.name == "nt":
        hint = (
            "Create a key at https://console.x.ai/team/default/api-keys then:\n"
            "  [Environment]::SetEnvironmentVariable('XAI_API_KEY','xai-...','User')\n"
            "Restart the terminal / agent so detached hooks see it."
        )
    else:
        hint = (
            "Create a key at https://console.x.ai/team/default/api-keys then add to "
            "~/.zprofile (login shells) and ~/.zshrc:\n"
            "  export XAI_API_KEY=xai-...\n"
            "Open a new terminal so hooks see it."
        )
    return Check(
        name="api_key",
        ok=False,
        detail="XAI_API_KEY is MISSING",
        hint=hint,
        critical=True,
    )


def check_players() -> Check:
    players = probe_players()
    if players:
        return Check(
            name="players",
            ok=True,
            detail=", ".join(players),
        )
    if sys.platform == "darwin":
        hint = "afplay should ship with macOS; check PATH."
    elif os.name == "nt":
        hint = "winsound is built-in; ensure a working audio device."
    else:
        hint = "Install one of: ffmpeg (ffplay), paplay (pulseaudio), or aplay (alsa)."
    return Check(
        name="players",
        ok=False,
        detail="(none)",
        hint=hint,
        critical=True,
    )


def check_streaming() -> Check:
    ok = streaming_available()
    return Check(
        name="streaming",
        ok=ok,
        detail="websockets available" if ok else "websockets not installed (REST fallback OK)",
        hint="" if ok else "pip install --user 'websockets>=12.0'   # optional lower latency",
        critical=False,
    )


def check_path() -> Check:
    home_bin = home_dir() / "bin"
    path = os.environ.get("PATH", "")
    parts = path.split(os.pathsep)
    home_bin_s = str(home_bin)
    on_path = any(Path(p).resolve() == home_bin.resolve() for p in parts if p)
    # Also: launcher name resolvable
    which = _which("ai-tts")
    if on_path or which:
        detail = f"ai-tts on PATH ({which or home_bin_s})"
        return Check(name="path", ok=True, detail=detail)
    env_sh = home_dir() / "env.sh"
    hint = (
        f"Add to PATH, e.g. in ~/.zprofile:\n"
        f"  source {env_sh}\n"
        f"or: export PATH=\"{home_bin}:$PATH\"\n"
        f"Or symlink: ln -sf {home_bin / 'ai-tts'} ~/.local/bin/ai-tts"
    )
    return Check(
        name="path",
        ok=False,
        detail=f"{home_bin} not on PATH; full path still works",
        hint=hint,
        critical=False,
    )


def check_grok_hooks() -> Check:
    path = Path.home() / ".grok" / "hooks" / "tts.json"
    if not path.is_file():
        return Check(
            name="grok_hooks",
            ok=False,
            detail="~/.grok/hooks/tts.json missing",
            hint="Re-run: ./install.sh Grok   (or install.ps1 -Target Grok)",
            critical=False,
        )
    try:
        raw = path.read_bytes()
    except OSError as e:
        return Check(
            name="grok_hooks",
            ok=False,
            detail=f"cannot read {path}: {e}",
            critical=False,
        )
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    try:
        text = raw.decode("utf-8-sig")
        data = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return Check(
            name="grok_hooks",
            ok=False,
            detail=f"tts.json invalid JSON: {e}",
            hint="Re-run install.ps1 -Target Grok (writes UTF-8 without BOM)",
            critical=False,
        )
    blob = text.lower()
    if "hook-stop" not in blob and "ai-tts" not in blob:
        return Check(
            name="grok_hooks",
            ok=False,
            detail=f"{path} present but no ai-tts hook-stop command",
            hint="Re-run install.ps1 -Target Grok",
            critical=False,
        )
    if has_bom:
        return Check(
            name="grok_hooks",
            ok=False,
            detail=f"{path} has UTF-8 BOM (Grok may ignore hooks)",
            hint=(
                "Re-run install.ps1 -Target Grok (fixed no-BOM writer), "
                "or rewrite tts.json as UTF-8 without BOM"
            ),
            critical=False,
        )
    _ = data  # parsed successfully
    return Check(name="grok_hooks", ok=True, detail=str(path))


def check_claude_hooks() -> Check:
    snippet = home_dir() / "claude-settings.hooks.snippet.json"
    settings = Path.home() / ".claude" / "settings.json"
    skill = Path.home() / ".claude" / "skills" / "tts" / "SKILL.md"
    if not skill.is_file() and not snippet.is_file():
        return Check(
            name="claude_hooks",
            ok=False,
            detail="Claude integration not installed",
            hint="Optional: ./install.sh Claude  then merge hook snippet into ~/.claude/settings.json",
            critical=False,
        )
    merged = False
    if settings.is_file():
        try:
            text = settings.read_text(encoding="utf-8")
            merged = "hook-stop" in text or "ai-tts" in text or "tts" in text.lower()
        except OSError:
            merged = False
    if merged:
        return Check(
            name="claude_hooks",
            ok=True,
            detail=f"skill present; settings.json looks configured ({settings})",
        )
    return Check(
        name="claude_hooks",
        ok=False,
        detail="Claude skill/snippet present but settings.json may lack hooks",
        hint=(
            f"Merge hooks from {snippet} into {settings} "
            "(SessionStart + Stop), then restart Claude Code."
            if snippet.is_file()
            else f"Add Stop/SessionStart hooks calling ai-tts into {settings}"
        ),
        critical=False,
    )


def check_config() -> Check:
    cfg = load_config()
    return Check(
        name="config",
        ok=True,
        detail=f"voice={cfg.voice} mode={cfg.mode} language={cfg.language} speed={cfg.speed}",
    )


DEFAULT_CHECKS: tuple[Callable[[], Check], ...] = (
    check_python,
    check_package_layout,
    check_config,
    check_api_key,
    check_players,
    check_streaming,
    check_path,
    check_grok_hooks,
    check_claude_hooks,
)


def run_checks(checks: tuple[Callable[[], Check], ...] | None = None) -> list[Check]:
    fns = checks or DEFAULT_CHECKS
    return [fn() for fn in fns]


def format_report(results: list[Check]) -> str:
    lines: list[str] = ["ai-tts doctor", ""]
    for c in results:
        mark = "PASS" if c.ok else ("FAIL" if c.critical else "WARN")
        lines.append(f"[{mark}] {c.name}: {c.detail}")
        if not c.ok and c.hint:
            for hline in c.hint.splitlines():
                lines.append(f"       → {hline}")
    lines.append("")
    crit_fail = sum(1 for c in results if not c.ok and c.critical)
    warn = sum(1 for c in results if not c.ok and not c.critical)
    if crit_fail:
        lines.append(f"Result: {crit_fail} critical failure(s), {warn} warning(s).")
    elif warn:
        lines.append(f"Result: OK with {warn} warning(s).")
    else:
        lines.append("Result: all checks passed.")
    lines.append("Next: ai-tts speak \"Hello\"   then new agent session + /tts")
    return "\n".join(lines) + "\n"


def doctor_exit_code(results: list[Check]) -> int:
    if any(not c.ok and c.critical for c in results):
        return 1
    return 0
