"""SessionStart / Stop hook helpers for Grok Build and Claude Code."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from .client import DaemonClientError, speak_via_daemon
from .config import load_config
from .markers import is_enabled, resolve_cwd_from_env_and_payload
from .speak import speak_text
from .tts_rest import TtsError

SAY_RE = re.compile(r"(?s)<say>(.*?)</say>")


def read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def last_say_block(text: str | None) -> str | None:
    if not text:
        return None
    matches = SAY_RE.findall(text)
    if not matches:
        return None
    say = matches[-1].strip()
    return say or None


def extract_assistant_text(payload: dict[str, Any]) -> str | None:
    text = payload.get("lastAssistantMessage") or payload.get("last_assistant_message")
    if text:
        return str(text)

    tp = payload.get("transcript_path") or payload.get("transcriptPath")
    if not tp:
        return None
    path = Path(tp)
    if not path.is_file():
        return None

    # Claude-style JSONL: walk backward for last assistant text
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None

    for line in reversed(lines):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "assistant":
            continue
        msg = obj.get("message") or {}
        content = msg.get("content") or []
        parts: list[str] = []
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for blk in content:
                if isinstance(blk, dict) and blk.get("type") == "text":
                    parts.append(str(blk.get("text") or ""))
        joined = "".join(parts).strip()
        if joined:
            return joined
    return None


def hook_state(harness: str = "grok") -> int:
    """SessionStart: print context for the model (JSON for Grok, text for Claude)."""
    payload = read_stdin_json()
    cwd = resolve_cwd_from_env_and_payload(payload)
    cfg = load_config()
    voice = cfg.voice
    on = bool(cwd and is_enabled(cwd, harness))

    if on:
        msg = (
            f"[tts] Voice output is ON for this directory (voice: {voice}). "
            "End each response with a concise <say>one to two sentence spoken summary</say> "
            "line - plain spoken language only (no code, paths, markdown). "
            "A Stop hook speaks it asynchronously via xAI; do NOT call speak yourself. "
            "Run /tts to turn it off for this directory."
        )
    else:
        msg = (
            "[tts] Voice output is OFF (default) for this directory. "
            "Do not emit <say> markers. Run /tts to enable voice for this directory."
        )

    # Grok-style additionalContext + Claude plain text
    out = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": msg,
        },
        "systemMessage": msg,
    }
    # Always emit JSON (Grok uses it; Claude may show raw — also print text line for Claude)
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    # Claude Code historically used plain stdout; many builds also accept JSON.
    # Emit a trailing newline + plain line for maximum compatibility.
    sys.stdout.write("\n" + msg + "\n")
    return 0


def _try_autostart_daemon(cfg) -> bool:
    if not cfg.daemon.auto_start:
        return False
    # Launch: python -m ai_tts daemon in background
    try:
        kwargs: dict[str, Any] = {
            "args": [sys.executable, "-m", "ai_tts", "daemon"],
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(
                subprocess, "DETACHED_PROCESS", 0x00000008
            )
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(**kwargs)
        import time

        for _ in range(20):
            time.sleep(0.15)
            try:
                from .client import ping_daemon

                ping_daemon(cfg)
                return True
            except DaemonClientError:
                continue
    except OSError:
        return False
    return False


def speak_request(text: str) -> None:
    """Dispatch speak via daemon or direct, based on config."""
    cfg = load_config()
    if cfg.daemon_enabled:
        try:
            speak_via_daemon(text, cfg=cfg)
            return
        except DaemonClientError:
            if _try_autostart_daemon(cfg):
                try:
                    speak_via_daemon(text, cfg=cfg)
                    return
                except DaemonClientError:
                    pass
            # fall through to direct

    # Direct (blocking in this process — hooks should spawn us detached if needed)
    speak_text(text, cfg=cfg)


def hook_stop(harness: str = "grok") -> int:
    """Stop hook: extract <say> and speak (spawn detached player when possible)."""
    payload = read_stdin_json()

    reason = payload.get("reason")
    if reason and reason != "end_turn":
        return 0

    cwd = resolve_cwd_from_env_and_payload(payload)
    if not cwd or not is_enabled(cwd, harness):
        return 0

    text = extract_assistant_text(payload)
    say = last_say_block(text)
    if not say:
        return 0

    # Detach so Stop hook returns quickly
    try:
        args = [sys.executable, "-m", "ai_tts", "speak", "--", say]
        kwargs: dict[str, Any] = {
            "args": args,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(
                subprocess, "DETACHED_PROCESS", 0x00000008
            )
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(**kwargs)
    except OSError:
        # Last resort: speak in-process (blocks)
        try:
            speak_request(say)
        except TtsError:
            return 0
    return 0
