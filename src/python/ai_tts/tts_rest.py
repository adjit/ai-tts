"""Unary REST TTS: POST https://api.x.ai/v1/tts"""

from __future__ import annotations

import json
import urllib.error
import urllib.request


class TtsError(RuntimeError):
    pass


def synthesize_rest(
    text: str,
    *,
    api_key: str,
    voice: str = "carina",
    language: str = "en",
    speed: float = 1.0,
    sample_rate: int = 24000,
    timeout: float = 120.0,
) -> bytes:
    body = {
        "text": text,
        "voice_id": voice,
        "language": language,
        "speed": speed,
        "output_format": {"codec": "wav", "sample_rate": sample_rate},
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        "https://api.x.ai/v1/tts",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            audio = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        raise TtsError(f"REST TTS HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise TtsError(f"REST TTS network error: {e}") from e

    if not audio:
        raise TtsError("REST TTS returned empty body")
    return audio
