from __future__ import annotations

import socket
import threading
import time

import pytest

from ai_tts.client import DaemonClientError, daemon_request, ping_daemon, speak_via_daemon
from ai_tts.config import load_config
from ai_tts.daemon_server import handle_payload, serve


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_handle_payload_ping():
    cfg = load_config()
    r = handle_payload({"cmd": "ping"}, cfg)
    assert r["ok"] is True
    assert r.get("pong") is True


def test_handle_payload_missing_text(isolated_home):
    cfg = load_config()
    r = handle_payload({}, cfg)
    assert r["ok"] is False


def test_handle_payload_speak(monkeypatch, isolated_home, write_config):
    write_config({"voice": "carina"})
    cfg = load_config()
    monkeypatch.setattr(
        "ai_tts.daemon_server.speak_text",
        lambda text, **k: {
            "ok": True,
            "transport": "rest",
            "voice": "carina",
            "ms": 1,
            "bytes": 10,
        },
    )
    r = handle_payload({"text": "hi there"}, cfg)
    assert r["ok"] is True
    assert r["voice"] == "carina"


def test_tcp_daemon_integration(monkeypatch, isolated_home, write_config):
    """Spin real TCP server; mock only synthesis/playback."""
    port = _free_port()
    write_config(
        {
            "voice": "carina",
            "mode": "daemon",
            "daemon": {
                "enabled": True,
                "host": "127.0.0.1",
                "port": port,
                "autoStart": False,
            },
        }
    )
    cfg = load_config()

    monkeypatch.setattr(
        "ai_tts.daemon_server.speak_text",
        lambda text, **k: {
            "ok": True,
            "transport": "rest",
            "voice": "carina",
            "bytes": 4,
            "synth_ms": 1,
            "play_ms": 1,
            "ms": 2,
        },
    )

    t = threading.Thread(target=serve, args=(cfg,), daemon=True)
    t.start()

    # Wait for listen
    deadline = time.time() + 3
    while time.time() < deadline:
        try:
            ping_daemon(cfg)
            break
        except DaemonClientError:
            time.sleep(0.05)
    else:
        pytest.fail("daemon did not start")

    pong = ping_daemon(cfg)
    assert pong["ok"] is True

    spoken = speak_via_daemon("hello from test", cfg=cfg)
    assert spoken["ok"] is True

    # shutdown
    r = daemon_request({"cmd": "shutdown"}, cfg=cfg, timeout=5)
    assert r.get("shutdown") is True
    t.join(timeout=3)
