from __future__ import annotations

from ai_tts.wavutil import is_probably_wav, pcm_to_wav_bytes, write_wav


def test_pcm_to_wav_has_riff_header():
    pcm = b"\x00\x00" * 240  # 10ms at 24kHz mono s16
    wav = pcm_to_wav_bytes(pcm, sample_rate=24000)
    assert is_probably_wav(wav)
    assert wav[0:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"
    # data chunk present
    assert b"data" in wav[:64]
    assert len(wav) == 44 + len(pcm)


def test_write_wav_roundtrip(tmp_path):
    pcm = b"\x01\x00" * 50
    path = write_wav(tmp_path / "t.wav", pcm, sample_rate=16000)
    data = path.read_bytes()
    assert is_probably_wav(data)
    assert len(data) == 44 + len(pcm)


def test_is_probably_wav_rejects_garbage():
    assert not is_probably_wav(b"")
    assert not is_probably_wav(b"not a wav file!!!!")
