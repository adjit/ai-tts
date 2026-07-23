"""TCP client for the optional ai-tts daemon."""

from __future__ import annotations

import json
import socket
from typing import Any

from .config import Config, load_config


class DaemonClientError(RuntimeError):
    pass


def daemon_request(
    payload: dict[str, Any],
    *,
    host: str | None = None,
    port: int | None = None,
    timeout: float = 120.0,
    cfg: Config | None = None,
) -> dict[str, Any]:
    cfg = cfg or load_config()
    host = host or cfg.daemon.host
    port = int(port if port is not None else cfg.daemon.port)

    line = json.dumps(payload, ensure_ascii=False) + "\n"
    data = line.encode("utf-8")

    try:
        with socket.create_connection((host, port), timeout=min(timeout, 5.0)) as sock:
            sock.settimeout(timeout)
            sock.sendall(data)
            # Read one line response
            buf = bytearray()
            while b"\n" not in buf:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buf.extend(chunk)
    except OSError as e:
        raise DaemonClientError(f"cannot connect to daemon {host}:{port}: {e}") from e

    if not buf:
        raise DaemonClientError("empty response from daemon")

    try:
        resp = json.loads(buf.decode("utf-8").strip().splitlines()[0])
    except json.JSONDecodeError as e:
        raise DaemonClientError(f"bad daemon JSON: {buf[:200]!r}") from e

    if not resp.get("ok"):
        raise DaemonClientError(resp.get("error") or "daemon error")
    return resp


def speak_via_daemon(
    text: str,
    *,
    voice: str | None = None,
    language: str | None = None,
    speed: float | None = None,
    cfg: Config | None = None,
) -> dict[str, Any]:
    cfg = cfg or load_config()
    payload = {
        "text": text,
        "voice": voice or cfg.voice,
        "language": language or cfg.language,
        "speed": speed if speed is not None else cfg.speed,
    }
    return daemon_request(payload, cfg=cfg)


def ping_daemon(cfg: Config | None = None) -> dict[str, Any]:
    return daemon_request({"cmd": "ping"}, timeout=2.0, cfg=cfg)


def shutdown_daemon(cfg: Config | None = None) -> dict[str, Any]:
    return daemon_request({"cmd": "shutdown"}, timeout=2.0, cfg=cfg)
