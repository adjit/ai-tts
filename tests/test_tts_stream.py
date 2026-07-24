from __future__ import annotations

import base64
import json

import pytest

from ai_tts.play import _BufferPcmPlayer
from ai_tts.tts_rest import TtsError
from ai_tts.tts_stream import stream_and_play, synthesize_stream
from ai_tts.wavutil import pcm_to_wav_bytes


class _FakeWs:
    """Minimal async websocket that yields scripted JSON events."""

    def __init__(self, events: list[dict]):
        self._events = list(events)
        self.sent: list[str] = []

    async def send(self, data: str) -> None:
        self.sent.append(data)

    async def recv(self) -> str:
        if not self._events:
            raise RuntimeError("no more events")
        return json.dumps(self._events.pop(0))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


def test_synthesize_stream_collects_pcm(monkeypatch, sample_wav_bytes):
    pcm = b"\x01\x00" * 50
    events = [
        {"type": "audio.delta", "delta": base64.b64encode(pcm[:40]).decode()},
        {"type": "audio.delta", "delta": base64.b64encode(pcm[40:]).decode()},
        {"type": "audio.done"},
    ]
    fake = _FakeWs(events)

    class _CM:
        async def __aenter__(self):
            return fake

        async def __aexit__(self, *a):
            return False

    def fake_connect(*a, **k):
        return _CM()

    import ai_tts.tts_stream as mod

    monkeypatch.setattr(mod, "streaming_available", lambda: True)

    class _WsMod:
        @staticmethod
        def connect(*a, **k):
            return fake_connect()

    # Inject websockets module name used inside _stream_async
    import sys
    import types

    ws_mod = types.ModuleType("websockets")
    ws_mod.connect = fake_connect  # type: ignore[attr-defined]
    exc_mod = types.ModuleType("websockets.exceptions")

    class WebSocketException(Exception):
        pass

    exc_mod.WebSocketException = WebSocketException  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "websockets", ws_mod)
    monkeypatch.setitem(sys.modules, "websockets.exceptions", exc_mod)

    wav = synthesize_stream(
        "hello",
        api_key="k",
        voice="carina",
        sample_rate=24000,
    )
    assert wav[:4] == b"RIFF"
    # Round-trip length: header + pcm
    assert len(wav) >= 44 + len(pcm)
    assert fake.sent  # text.delta + text.done


def test_stream_and_play_ttfa(monkeypatch):
    pcm_a = b"\x02\x00" * 100
    pcm_b = b"\x03\x00" * 100
    events = [
        {"type": "audio.delta", "delta": base64.b64encode(pcm_a).decode()},
        {"type": "audio.delta", "delta": base64.b64encode(pcm_b).decode()},
        {"type": "audio.done"},
    ]
    fake = _FakeWs(events)

    def fake_connect(*a, **k):
        class _CM:
            async def __aenter__(self):
                return fake

            async def __aexit__(self, *a):
                return False

        return _CM()

    import sys
    import types

    import ai_tts.tts_stream as mod

    ws_mod = types.ModuleType("websockets")
    ws_mod.connect = fake_connect  # type: ignore[attr-defined]
    exc_mod = types.ModuleType("websockets.exceptions")

    class WebSocketException(Exception):
        pass

    exc_mod.WebSocketException = WebSocketException  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "websockets", ws_mod)
    monkeypatch.setitem(sys.modules, "websockets.exceptions", exc_mod)
    monkeypatch.setattr(mod, "streaming_available", lambda: True)

    written: list[bytes] = []

    class FakePlayer:
        mode = "stream"

        def write(self, pcm: bytes) -> None:
            written.append(pcm)

        def close(self) -> None:
            pass

        def abort(self) -> None:
            pass

    monkeypatch.setattr(mod, "open_pcm_player", lambda *a, **k: FakePlayer())

    meta = stream_and_play("hi", api_key="k", voice="eve")
    assert meta["ok"] is True
    assert meta["transport"] == "stream-play"
    assert meta["play_mode"] == "stream"
    assert meta["ttfa_ms"] is not None
    assert meta["ttfa_ms"] >= 0
    assert meta["bytes"] == len(pcm_a) + len(pcm_b)
    assert b"".join(written) == pcm_a + pcm_b


def test_stream_and_play_empty_raises(monkeypatch):
    events = [{"type": "audio.done"}]
    fake = _FakeWs(events)

    def fake_connect(*a, **k):
        class _CM:
            async def __aenter__(self):
                return fake

            async def __aexit__(self, *a):
                return False

        return _CM()

    import sys
    import types

    import ai_tts.tts_stream as mod

    ws_mod = types.ModuleType("websockets")
    ws_mod.connect = fake_connect  # type: ignore[attr-defined]
    exc_mod = types.ModuleType("websockets.exceptions")

    class WebSocketException(Exception):
        pass

    exc_mod.WebSocketException = WebSocketException  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "websockets", ws_mod)
    monkeypatch.setitem(sys.modules, "websockets.exceptions", exc_mod)
    monkeypatch.setattr(mod, "streaming_available", lambda: True)
    monkeypatch.setattr(mod, "open_pcm_player", lambda *a, **k: _BufferPcmPlayer(24000))

    with pytest.raises(TtsError, match="no audio"):
        stream_and_play("x", api_key="k")


def test_buffer_player_builds_wav(monkeypatch, sample_wav_bytes):
    played: list[bytes] = []
    monkeypatch.setattr(
        "ai_tts.play.play_wav_bytes",
        lambda data: played.append(data),
    )
    p = _BufferPcmPlayer(24000)
    assert p.mode == "buffer"
    pcm = b"\x00\x00" * 100
    p.write(pcm)
    p.close()
    assert played and played[0] == pcm_to_wav_bytes(pcm, sample_rate=24000)
