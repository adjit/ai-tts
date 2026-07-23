from __future__ import annotations

import io
import json
from urllib.error import HTTPError

import pytest

from ai_tts.tts_rest import TtsError, synthesize_rest


class _FakeResp:
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_synthesize_rest_success(monkeypatch, sample_wav_bytes):
    def fake_urlopen(req, timeout=None):
        assert req.get_method() == "POST"
        assert "Authorization" in req.headers or req.headers.get("Authorization")
        body = json.loads(req.data.decode("utf-8"))
        assert body["text"] == "hi"
        assert body["voice_id"] == "carina"
        assert body["output_format"]["codec"] == "wav"
        return _FakeResp(sample_wav_bytes)

    monkeypatch.setattr("ai_tts.tts_rest.urllib.request.urlopen", fake_urlopen)
    out = synthesize_rest("hi", api_key="k", voice="carina")
    assert out == sample_wav_bytes


def test_synthesize_rest_http_error(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise HTTPError(
            "https://api.x.ai/v1/tts",
            401,
            "nope",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"bad key"}'),
        )

    monkeypatch.setattr("ai_tts.tts_rest.urllib.request.urlopen", fake_urlopen)
    with pytest.raises(TtsError, match="401"):
        synthesize_rest("hi", api_key="bad")


def test_synthesize_rest_empty(monkeypatch):
    monkeypatch.setattr(
        "ai_tts.tts_rest.urllib.request.urlopen",
        lambda *a, **k: _FakeResp(b""),
    )
    with pytest.raises(TtsError, match="empty"):
        synthesize_rest("hi", api_key="k")
