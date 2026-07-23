"""Streaming WebSocket TTS: wss://api.x.ai/v1/tts

Uses the optional `websockets` package when installed; otherwise raises so
callers can fall back to REST.
"""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any
from urllib.parse import urlencode

from .tts_rest import TtsError
from .wavutil import pcm_to_wav_bytes


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
    """Return WAV bytes from a streaming PCM session."""
    if not streaming_available():
        raise TtsError("websockets package not installed; use REST or: pip install websockets")

    return asyncio.run(
        _stream_async(
            text,
            api_key=api_key,
            voice=voice,
            language=language,
            speed=speed,
            sample_rate=sample_rate,
            optimize_streaming_latency=optimize_streaming_latency,
            timeout=timeout,
        )
    )


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
) -> bytes:
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

    pcm = bytearray()
    try:
        # websockets v11+ uses additional_headers; v10 uses extra_headers
        connect_kwargs: dict[str, Any] = {"open_timeout": timeout, "close_timeout": 10}
        try:
            async with websockets.connect(
                uri, additional_headers=headers, **connect_kwargs
            ) as ws:
                await _drive_utterance(ws, text, pcm)
        except TypeError:
            async with websockets.connect(
                uri, extra_headers=headers, **connect_kwargs
            ) as ws:
                await _drive_utterance(ws, text, pcm)
    except WebSocketException as e:
        raise TtsError(f"stream WebSocket error: {e}") from e
    except OSError as e:
        raise TtsError(f"stream network error: {e}") from e

    if not pcm:
        raise TtsError("streaming TTS returned no audio")
    return pcm_to_wav_bytes(bytes(pcm), sample_rate=sample_rate)


async def _drive_utterance(ws: Any, text: str, pcm: bytearray) -> None:
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
                pcm.extend(base64.b64decode(delta))
        elif et == "audio.done":
            break
        elif et == "error":
            raise TtsError(f"stream error: {event.get('message')}")
