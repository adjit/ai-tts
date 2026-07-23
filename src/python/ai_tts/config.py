"""Load ~/.ai-tts/config.json (or AI_TTS_HOME)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def home_dir() -> Path:
    if os.environ.get("AI_TTS_HOME"):
        return Path(os.environ["AI_TTS_HOME"]).expanduser()
    return Path.home() / ".ai-tts"


def config_path() -> Path:
    return home_dir() / "config.json"


@dataclass
class DaemonConfig:
    enabled: bool = False
    pipe_name: str = "ai-tts"
    host: str = "127.0.0.1"
    port: int = 18765
    auto_start: bool = False
    optimize_streaming_latency: int = 2
    sample_rate: int = 24000


@dataclass
class Config:
    voice: str = "carina"
    language: str = "en"
    speed: float = 1.0
    mode: str = "direct"  # direct | daemon
    daemon: DaemonConfig = field(default_factory=DaemonConfig)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def daemon_enabled(self) -> bool:
        if (self.mode or "").lower() == "daemon":
            return True
        return bool(self.daemon.enabled)


def _as_bool(v: Any, default: bool = False) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> Config:
    path = config_path()
    data: dict[str, Any] = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}

    d = data.get("daemon") or {}
    daemon = DaemonConfig(
        enabled=_as_bool(d.get("enabled"), False),
        pipe_name=str(d.get("pipeName") or d.get("pipe_name") or "ai-tts"),
        host=str(d.get("host") or "127.0.0.1"),
        port=int(d.get("port") or 18765),
        auto_start=_as_bool(d.get("autoStart") or d.get("auto_start"), False),
        optimize_streaming_latency=int(
            d.get("optimizeStreamingLatency")
            or d.get("optimize_streaming_latency")
            or 2
        ),
        sample_rate=int(d.get("sampleRate") or d.get("sample_rate") or 24000),
    )
    return Config(
        voice=str(data.get("voice") or "carina"),
        language=str(data.get("language") or "en"),
        speed=float(data.get("speed") or 1.0),
        mode=str(data.get("mode") or "direct"),
        daemon=daemon,
        raw=data,
    )


def save_config(cfg: Config) -> None:
    home = home_dir()
    home.mkdir(parents=True, exist_ok=True)
    payload = {
        "voice": cfg.voice,
        "language": cfg.language,
        "speed": cfg.speed,
        "mode": cfg.mode,
        "daemon": {
            "enabled": cfg.daemon.enabled,
            "pipeName": cfg.daemon.pipe_name,
            "host": cfg.daemon.host,
            "port": cfg.daemon.port,
            "autoStart": cfg.daemon.auto_start,
            "optimizeStreamingLatency": cfg.daemon.optimize_streaming_latency,
            "sampleRate": cfg.daemon.sample_rate,
        },
    }
    config_path().write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def get_api_key() -> str | None:
    key = os.environ.get("XAI_API_KEY")
    if key:
        return key
    # Windows: User-level env may exist without being in this process yet.
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as reg:
                val, _ = winreg.QueryValueEx(reg, "XAI_API_KEY")
                if val:
                    return str(val)
        except OSError:
            pass
    return None
