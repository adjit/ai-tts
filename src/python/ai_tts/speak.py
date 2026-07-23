"""One-shot speak orchestration (stream preferred, REST fallback)."""

from __future__ import annotations

import time
from typing import Literal

from .config import Config, get_api_key, load_config
from .play import play_wav_bytes
from .tts_rest import TtsError, synthesize_rest
from .tts_stream import streaming_available, synthesize_stream

Transport = Literal["auto", "stream", "rest"]


def speak_text(
    text: str,
    *,
    voice: str | None = None,
    language: str | None = None,
    speed: float | None = None,
    transport: Transport = "auto",
    cfg: Config | None = None,
) -> dict:
    """Synthesize and play text. Returns timing metadata."""
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

    t0 = time.perf_counter()
    audio: bytes
    used: str

    if transport == "rest":
        audio = synthesize_rest(
            text,
            api_key=api_key,
            voice=voice,
            language=language,
            speed=speed,
            sample_rate=sample_rate,
        )
        used = "rest"
    elif transport == "stream":
        audio = synthesize_stream(
            text,
            api_key=api_key,
            voice=voice,
            language=language,
            speed=speed,
            sample_rate=sample_rate,
            optimize_streaming_latency=opt,
        )
        used = "stream"
    else:
        # auto
        if streaming_available():
            try:
                audio = synthesize_stream(
                    text,
                    api_key=api_key,
                    voice=voice,
                    language=language,
                    speed=speed,
                    sample_rate=sample_rate,
                    optimize_streaming_latency=opt,
                )
                used = "stream"
            except TtsError:
                audio = synthesize_rest(
                    text,
                    api_key=api_key,
                    voice=voice,
                    language=language,
                    speed=speed,
                    sample_rate=sample_rate,
                )
                used = "rest-fallback"
        else:
            audio = synthesize_rest(
                text,
                api_key=api_key,
                voice=voice,
                language=language,
                speed=speed,
                sample_rate=sample_rate,
            )
            used = "rest"

    t_synth = time.perf_counter()
    play_wav_bytes(audio)
    t_end = time.perf_counter()

    return {
        "ok": True,
        "transport": used,
        "voice": voice,
        "bytes": len(audio),
        "synth_ms": int((t_synth - t0) * 1000),
        "play_ms": int((t_end - t_synth) * 1000),
        "ms": int((t_end - t0) * 1000),
    }
