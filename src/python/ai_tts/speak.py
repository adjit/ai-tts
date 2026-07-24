"""One-shot speak orchestration (stream-while-play preferred, REST fallback)."""

from __future__ import annotations

import time
from typing import Any, Literal

from .config import Config, get_api_key, load_config
from .play import play_wav_bytes
from .tts_rest import TtsError, synthesize_rest
from .tts_stream import stream_and_play, streaming_available

Transport = Literal["auto", "stream", "rest"]


def speak_text(
    text: str,
    *,
    voice: str | None = None,
    language: str | None = None,
    speed: float | None = None,
    transport: Transport = "auto",
    cfg: Config | None = None,
) -> dict[str, Any]:
    """Synthesize and play text. Returns timing metadata.

    When streaming is available, prefers **stream-while-play** (audio starts as
    PCM chunks arrive). Falls back to buffer-then-play stream, then REST.
    """
    text = (text or "").strip()
    if not text:
        raise TtsError("empty text")

    cfg = cfg or load_config()
    voice = voice or cfg.voice
    language = language or cfg.language
    speed = float(speed if speed is not None else cfg.speed)
    sample_rate = cfg.daemon.sample_rate
    opt = cfg.daemon.optimize_streaming_latency

    api_key = get_api_key()
    if not api_key:
        raise TtsError("XAI_API_KEY is not set")

    if transport == "rest":
        return _speak_rest(
            text,
            api_key=api_key,
            voice=voice,
            language=language,
            speed=speed,
            sample_rate=sample_rate,
        )

    if transport == "stream":
        return _speak_stream(
            text,
            api_key=api_key,
            voice=voice,
            language=language,
            speed=speed,
            sample_rate=sample_rate,
            optimize_streaming_latency=opt,
        )

    # auto
    if streaming_available():
        try:
            return _speak_stream(
                text,
                api_key=api_key,
                voice=voice,
                language=language,
                speed=speed,
                sample_rate=sample_rate,
                optimize_streaming_latency=opt,
            )
        except TtsError:
            meta = _speak_rest(
                text,
                api_key=api_key,
                voice=voice,
                language=language,
                speed=speed,
                sample_rate=sample_rate,
            )
            meta["transport"] = "rest-fallback"
            return meta

    return _speak_rest(
        text,
        api_key=api_key,
        voice=voice,
        language=language,
        speed=speed,
        sample_rate=sample_rate,
    )


def _speak_stream(
    text: str,
    *,
    api_key: str,
    voice: str,
    language: str,
    speed: float,
    sample_rate: int,
    optimize_streaming_latency: int,
) -> dict[str, Any]:
    """Stream-while-play path; optional buffer-WAV fallback inside stream_and_play."""
    meta = stream_and_play(
        text,
        api_key=api_key,
        voice=voice,
        language=language,
        speed=speed,
        sample_rate=sample_rate,
        optimize_streaming_latency=optimize_streaming_latency,
    )
    meta["voice"] = voice
    return meta


def _speak_rest(
    text: str,
    *,
    api_key: str,
    voice: str,
    language: str,
    speed: float,
    sample_rate: int,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    audio = synthesize_rest(
        text,
        api_key=api_key,
        voice=voice,
        language=language,
        speed=speed,
        sample_rate=sample_rate,
    )
    t_synth = time.perf_counter()
    play_wav_bytes(audio)
    t_end = time.perf_counter()
    return {
        "ok": True,
        "transport": "rest",
        "voice": voice,
        "bytes": len(audio),
        "ttfa_ms": int((t_synth - t0) * 1000),  # first audio only after full synth
        "synth_ms": int((t_synth - t0) * 1000),
        "play_ms": int((t_end - t_synth) * 1000),
        "ms": int((t_end - t0) * 1000),
    }


__all__ = ["speak_text", "stream_and_play", "streaming_available"]
