"""Optional warm TCP daemon (127.0.0.1:18765 by default)."""

from __future__ import annotations

import json
import logging
import socket
import threading
import time
from pathlib import Path
from typing import Any

from .config import Config, home_dir, load_config, save_config
from .speak import speak_text
from .tts_rest import TtsError

LOG = logging.getLogger("ai_tts.daemon")


def _pid_path() -> Path:
    return home_dir() / "daemon.pid"


def _log_path() -> Path:
    return home_dir() / "daemon.log"


def setup_logging() -> None:
    home_dir().mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(_log_path(), encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def write_pid() -> None:
    import os

    _pid_path().write_text(str(os.getpid()), encoding="ascii")


def clear_pid() -> None:
    try:
        _pid_path().unlink(missing_ok=True)
    except OSError:
        pass


def handle_payload(payload: dict[str, Any], cfg: Config) -> dict[str, Any]:
    cmd = payload.get("cmd")
    if cmd == "ping":
        import os

        return {"ok": True, "pong": True, "pid": os.getpid()}
    if cmd == "shutdown":
        return {"ok": True, "shutdown": True}

    text = (payload.get("text") or "").strip()
    if not text:
        return {"ok": False, "error": "missing text"}

    t0 = time.perf_counter()
    try:
        meta = speak_text(
            text,
            voice=payload.get("voice"),
            language=payload.get("language"),
            speed=payload.get("speed"),
            transport="auto",
            cfg=cfg,
        )
        meta["ms"] = int((time.perf_counter() - t0) * 1000)
        return meta
    except TtsError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def serve(cfg: Config | None = None) -> None:
    cfg = cfg or load_config()
    setup_logging()
    host = cfg.daemon.host
    port = int(cfg.daemon.port)

    write_pid()
    LOG.info("ai-tts daemon listening on %s:%s voice=%s", host, port, cfg.voice)

    stop = threading.Event()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen(8)
        server.settimeout(1.0)

        try:
            while not stop.is_set():
                try:
                    conn, addr = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                threading.Thread(
                    target=_client_thread,
                    args=(conn, addr, cfg, stop),
                    daemon=True,
                ).start()
        finally:
            clear_pid()
            LOG.info("ai-tts daemon stopped")


def _client_thread(
    conn: socket.socket,
    addr: Any,
    cfg: Config,
    stop: threading.Event,
) -> None:
    try:
        with conn:
            conn.settimeout(180.0)
            buf = bytearray()
            while b"\n" not in buf:
                chunk = conn.recv(8192)
                if not chunk:
                    break
                buf.extend(chunk)
            if not buf:
                return
            line = buf.decode("utf-8", errors="replace").strip().splitlines()[0]
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                resp = {"ok": False, "error": "invalid json"}
            else:
                if payload.get("cmd") == "shutdown":
                    resp = {"ok": True, "shutdown": True}
                    conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
                    stop.set()
                    return
                resp = handle_payload(payload, cfg)

            conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
            if resp.get("ok"):
                LOG.info("spoke from %s ms=%s", addr, resp.get("ms"))
            else:
                LOG.warning("error for %s: %s", addr, resp.get("error"))
    except Exception as e:  # noqa: BLE001
        LOG.exception("client handler failed: %s", e)


def mark_config_daemon_enabled(enabled: bool = True) -> None:
    cfg = load_config()
    cfg.mode = "daemon" if enabled else "direct"
    cfg.daemon.enabled = enabled
    save_config(cfg)
