"""PCM helpers and WAV packaging."""

from __future__ import annotations

import struct
import wave
from pathlib import Path


def pcm_to_wav_bytes(
    pcm: bytes,
    *,
    sample_rate: int = 24000,
    channels: int = 1,
    sample_width: int = 2,
) -> bytes:
    """Wrap raw PCM (s16le) as a WAV file in memory."""
    import io

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def write_wav(
    path: Path | str,
    pcm: bytes,
    *,
    sample_rate: int = 24000,
    channels: int = 1,
    sample_width: int = 2,
) -> Path:
    path = Path(path)
    path.write_bytes(
        pcm_to_wav_bytes(
            pcm, sample_rate=sample_rate, channels=channels, sample_width=sample_width
        )
    )
    return path


def wav_header_size() -> int:
    return 44


def is_probably_wav(data: bytes) -> bool:
    return len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WAVE"
