"""Config get/set helpers for the CLI."""

from __future__ import annotations

from .config import Config, load_config, save_config
from .daemon_server import mark_config_daemon_enabled


SETTABLE = frozenset({"voice", "language", "speed", "mode"})


def config_as_dict(cfg: Config | None = None) -> dict:
    cfg = cfg or load_config()
    return {
        "voice": cfg.voice,
        "language": cfg.language,
        "speed": cfg.speed,
        "mode": cfg.mode,
        "daemon": {
            "enabled": cfg.daemon.enabled,
            "host": cfg.daemon.host,
            "port": cfg.daemon.port,
            "autoStart": cfg.daemon.auto_start,
            "optimizeStreamingLatency": cfg.daemon.optimize_streaming_latency,
            "sampleRate": cfg.daemon.sample_rate,
        },
        "daemon_enabled": cfg.daemon_enabled,
    }


def set_config_value(key: str, value: str) -> Config:
    key = key.strip().lower()
    if key not in SETTABLE:
        raise ValueError(
            f"unknown key {key!r}; settable: {', '.join(sorted(SETTABLE))}"
        )
    cfg = load_config()
    if key == "voice":
        cfg.voice = value.strip()
    elif key == "language":
        cfg.language = value.strip()
    elif key == "speed":
        cfg.speed = float(value)
    elif key == "mode":
        mode = value.strip().lower()
        if mode not in {"direct", "daemon"}:
            raise ValueError("mode must be 'direct' or 'daemon'")
        cfg.mode = mode
        if mode == "daemon":
            mark_config_daemon_enabled(True)
            return load_config()
        cfg.daemon.enabled = False
    save_config(cfg)
    return load_config()
