from __future__ import annotations

from ai_tts.config import get_api_key, load_config, save_config


def test_load_defaults(isolated_home):
    cfg = load_config()
    assert cfg.voice == "carina"
    assert cfg.mode == "direct"
    assert cfg.daemon_enabled is False
    assert cfg.daemon.port == 18765
    assert cfg.daemon.host == "127.0.0.1"


def test_load_and_save_roundtrip(isolated_home, write_config):
    write_config(
        {
            "voice": "eve",
            "language": "en",
            "speed": 1.1,
            "mode": "daemon",
            "daemon": {
                "enabled": True,
                "host": "127.0.0.1",
                "port": 19001,
                "autoStart": True,
                "optimizeStreamingLatency": 1,
                "sampleRate": 16000,
            },
        }
    )
    cfg = load_config()
    assert cfg.voice == "eve"
    assert cfg.daemon_enabled is True
    assert cfg.daemon.port == 19001
    assert cfg.daemon.auto_start is True
    assert cfg.daemon.optimize_streaming_latency == 1
    assert cfg.daemon.sample_rate == 16000

    cfg.voice = "leo"
    cfg.mode = "direct"
    cfg.daemon.enabled = False
    save_config(cfg)
    cfg2 = load_config()
    assert cfg2.voice == "leo"
    assert cfg2.daemon_enabled is False


def test_mode_daemon_enables_without_flag(isolated_home, write_config):
    write_config({"mode": "daemon", "daemon": {"enabled": False}})
    assert load_config().daemon_enabled is True


def test_get_api_key_from_env(isolated_home, monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-key-123")
    assert get_api_key() == "test-key-123"
