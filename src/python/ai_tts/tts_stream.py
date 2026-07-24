"""Streaming WebSocket TTS: wss://api.x.ai/v1/tts

Uses the optional `websockets` package when installed; otherwise raises so
callers can fall back to REST.

Supports full-buffer WAV synthesis and stream-while-play (PCM chunks as they
arrive).
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

from .play import PlaybackError, open_pcm_player
from .tts_rest import TtsError
from .wavutil import pcm_to_wav_bytes

OnPcm = Callable[[bytes], None]


def streaming_available() -> bool:
    try:
        import websockets  # noqa: F401

        return True
    except ImportError:
        return False


def synthesize_stream(
    text: str,
    *,
    api_key: str,
    voice: str = "carina",
    language: str = "en",
    speed: float = 1.0,
    sample_rate: int = 24000,
    optimize_streaming_latency: int = 2,
    timeout: float = 120.0,
) -> bytes:
    """Return WAV bytes from a streaming PCM session (buffer all, then wrap)."""
    if not streaming_available():
        raise TtsError("websockets package not installed; use REST or: pip install websockets")

    pcm = bytearray()

    def _collect(chunk: bytes) -> None:
        pcm.extend(chunk)

    asyncio.run(
        _stream_async(
            text,
            api_key=api_key,
            voice=voice,
            language=language,
            speed=speed,
            sample_rate=sample_rate,
            optimize_streaming_latency=optimize_streaming_latency,
            timeout=timeout,
            on_pcm=_collect,
        )
    )
    if not pcm:
        raise TtsError("streaming TTS returned no audio")
    return pcm_to_wav_bytes(bytes(pcm), sample_rate=sample_rate)


def stream_and_play(
    text: str,
    *,
    api_key: str,
    voice: str = "carina",
    language: str = "en",
    speed: float = 1.0,
    sample_rate: int = 24000,
    optimize_streaming_latency: int = 2,
    timeout: float = 120.0,
) -> dict[str, Any]:
    """Receive PCM from xAI and play as chunks arrive.

    Returns timing metadata including time-to-first-audio (`ttfa_ms`).
    Falls back to buffer-then-play when no streaming player backend is available
    (same end result, higher latency).
    """
    if not streaming_available():
        raise TtsError("websockets package not installed; use REST or: pip install websockets")

    text = (text or "").strip()
    if not text:
        raise TtsError("empty text")

    t0 = time.perf_counter()
    first_audio_at: float | None = None
    total_pcm = 0
    player = open_pcm_player(sample_rate)
    play_mode = player.mode  # "stream" | "buffer"

    def on_pcm(chunk: bytes) -> None:
        nonlocal first_audio_at, total_pcm
        if not chunk:
            return
        total_pcm += len(chunk)
        if first_audio_at is None:
            first_audio_at = time.perf_counter()
        player.write(chunk)

    try:
        asyncio.run(
            _stream_async(
                text,
                api_key=api_key,
                voice=voice,
                language=language,
                speed=speed,
                sample_rate=sample_rate,
                optimize_streaming_latency=optimize_streaming_latency,
                timeout=timeout,
                on_pcm=on_pcm,
            )
        )
        player.close()
    except Exception:
        try:
            player.abort()
        except Exception:
            pass
        raise

    if total_pcm == 0:
        raise TtsError("streaming TTS returned no audio")

    t_end = time.perf_counter()
    ttfa_ms = (
        int((first_audio_at - t0) * 1000) if first_audio_at is not None else None
    )
    transport = "stream-play" if play_mode == "stream" else "stream"
    return {
        "ok": True,
        "transport": transport,
        "voice": voice,
        "bytes": total_pcm,
        "play_mode": play_mode,
        "ttfa_ms": ttfa_ms,
        "synth_ms": int((t_end - t0) * 1000),  # receive+play overlap for stream-play
        "play_ms": 0 if play_mode == "stream" else None,
        "ms": int((t_end - t0) * 1000),
    }


async def _stream_async(
    text: str,
    *,
    api_key: str,
    voice: str,
    language: str,
    speed: float,
    sample_rate: int,
    optimize_streaming_latency: int,
    timeout: float,
    on_pcm: OnPcm,
) -> None:
    import websockets
    from websockets.exceptions import WebSocketException

    qs = urlencode(
        {
            "language": language,
            "voice": voice,
            "codec": "pcm",
            "sample_rate": str(sample_rate),
            "speed": str(speed),
            "optimize_streaming_latency": str(optimize_streaming_latency),
        }
    )
    uri = f"wss://api.x.ai/v1/tts?{qs}"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        # websockets v11+ uses additional_headers; v10 uses extra_headers
        connect_kwargs: dict[str, Any] = {"open_timeout": timeout, "close_timeout": 10}
        try:
            async with websockets.connect(
                uri, additional_headers=headers, **connect_kwargs
            ) as ws:
                await _drive_utterance(ws, text, on_pcm)
        except TypeError:
            async with websockets.connect(
                uri, extra_headers=headers, **connect_kwargs
            ) as ws:
                await _drive_utterance(ws, text, on_pcm)
    except WebSocketException as e:
        raise TtsError(f"stream WebSocket error: {e}") from e
    except OSError as e:
        raise TtsError(f"stream network error: {e}") from e
    except PlaybackError as e:
        raise TtsError(f"stream playback error: {e}") from e


async def _drive_utterance(ws: Any, text: str, on_pcm: OnPcm) -> None:
    await ws.send(json.dumps({"type": "text.delta", "delta": text}))
    await ws.send(json.dumps({"type": "text.done"}))

    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=120)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        event = json.loads(raw)
        et = event.get("type")
        if et == "audio.delta":
            delta = event.get("delta") or ""
            if delta:
                on_pcm(base64.b64decode(delta))
        elif et == "audio.done":
            break
        elif et == "error":
            raise TtsError(f"stream error: {event.get('message')}")
