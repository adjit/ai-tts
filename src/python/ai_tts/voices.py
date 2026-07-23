"""Known xAI TTS voice ids (static list; live catalog may grow)."""

from __future__ import annotations

# Common voices documented in docs/voices.md
KNOWN_VOICES: tuple[str, ...] = (
    "ara",
    "atlas",
    "carina",
    "celeste",
    "eve",
    "iris",
    "leo",
    "luna",
    "orion",
    "rex",
    "sal",
)

VOICE_META: dict[str, dict[str, str]] = {
    "ara": {"name": "Ara", "gender": "female"},
    "atlas": {"name": "Atlas", "gender": "male"},
    "carina": {"name": "Carina", "gender": "female"},
    "celeste": {"name": "Celeste", "gender": "female"},
    "eve": {"name": "Eve", "gender": "female"},
    "iris": {"name": "Iris", "gender": "female"},
    "leo": {"name": "Leo", "gender": "male"},
    "luna": {"name": "Luna", "gender": "female"},
    "orion": {"name": "Orion", "gender": "male"},
    "rex": {"name": "Rex", "gender": "male"},
    "sal": {"name": "Sal", "gender": "male"},
}


def list_known_voices() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for vid in KNOWN_VOICES:
        meta = VOICE_META.get(vid, {})
        out.append(
            {
                "voice_id": vid,
                "name": meta.get("name", vid.title()),
                "gender": meta.get("gender", ""),
            }
        )
    return out
