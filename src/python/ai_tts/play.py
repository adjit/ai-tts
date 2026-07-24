"""Cross-platform audio playback for WAV files and streaming PCM."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Protocol

from .wavutil import pcm_to_wav_bytes


class PlaybackError(RuntimeError):
    pass


def play_wav_bytes(data: bytes) -> None:
    if not data:
        raise PlaybackError("empty audio")
    fd, name = tempfile.mkstemp(suffix=".wav", prefix="ai-tts-")
    os.close(fd)
    path = Path(name)
    try:
        path.write_bytes(data)
        play_wav_file(path)
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def play_wav_file(path: Path | str) -> None:
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise PlaybackError(f"missing audio file: {path}")

    system = platform.system()
    if system == "Windows":
        _play_windows(path)
    elif system == "Darwin":
        _play_macos(path)
    else:
        _play_linux(path)


def _play_windows(path: Path) -> None:
    try:
        import winsound

        winsound.PlaySound(str(path), winsound.SND_FILENAME)
        return
    except Exception:
        pass

    # ffplay fallback
    if shutil.which("ffplay"):
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)],
            check=False,
        )
        return

    # PowerShell MCI fallback (same reliability as legacy speak.ps1)
    ps = shutil.which("powershell") or shutil.which("pwsh")
    if ps:
        alias = f"aitts{os.getpid()}"
        script = (
            f'$p = "{str(path).replace(chr(34), chr(39))}"; '
            "Add-Type -Name W -Namespace N -MemberDefinition '"
            '[DllImport("winmm.dll", CharSet = CharSet.Auto)]'
            "public static extern int mciSendString(string c, System.Text.StringBuilder b, int s, System.IntPtr h);"
            "'; "
            f'[void][N.W]::mciSendString("open `"$p`" type waveaudio alias {alias}", $null, 0, [IntPtr]::Zero); '
            f'[void][N.W]::mciSendString("play {alias} wait", $null, 0, [IntPtr]::Zero); '
            f'[void][N.W]::mciSendString("close {alias}", $null, 0, [IntPtr]::Zero);'
        )
        r = subprocess.run([ps, "-NoProfile", "-Command", script], check=False)
        if r.returncode == 0:
            return

    raise PlaybackError("Windows playback failed (winsound/ffplay/powershell)")


def _play_macos(path: Path) -> None:
    if shutil.which("afplay"):
        subprocess.run(["afplay", str(path)], check=True)
        return
    if shutil.which("ffplay"):
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)],
            check=True,
        )
        return
    raise PlaybackError("macOS: need afplay or ffplay")


def _play_linux(path: Path) -> None:
    if shutil.which("ffplay"):
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)],
            check=True,
        )
        return
    if shutil.which("paplay"):
        subprocess.run(["paplay", str(path)], check=True)
        return
    if shutil.which("aplay"):
        subprocess.run(["aplay", "-q", str(path)], check=True)
        return
    raise PlaybackError("Linux: install ffmpeg (ffplay), paplay, or aplay")


def probe_players() -> list[str]:
    """Return available player backends for the current OS."""
    system = platform.system()
    found: list[str] = []
    if system == "Windows":
        found.append("winsound")
        if _winmm_available():
            found.append("winmm-pcm")
        if shutil.which("ffplay"):
            found.append("ffplay")
        if shutil.which("powershell") or shutil.which("pwsh"):
            found.append("powershell-mci")
    elif system == "Darwin":
        if shutil.which("afplay"):
            found.append("afplay")
        if shutil.which("ffplay"):
            found.append("ffplay")
    else:
        for name in ("ffplay", "paplay", "aplay"):
            if shutil.which(name):
                found.append(name)
    return found


# ---------------------------------------------------------------------------
# Stream-while-play (raw s16le mono PCM)
# ---------------------------------------------------------------------------


class PcmPlayer(Protocol):
    mode: str  # "stream" | "buffer"

    def write(self, pcm: bytes) -> None: ...

    def close(self) -> None: ...

    def abort(self) -> None: ...


def open_pcm_player(
    sample_rate: int,
    *,
    channels: int = 1,
    sample_width: int = 2,
) -> PcmPlayer:
    """Open the best available PCM stream player, or a buffer-then-play fallback."""
    # Prefer true streaming backends (audio starts before full utterance).
    if shutil.which("ffplay"):
        try:
            return _FFplayPcmPlayer(sample_rate, channels=channels)
        except PlaybackError:
            pass

    system = platform.system()
    if system == "Windows":
        try:
            return _WinmmPcmPlayer(sample_rate, channels=channels, sample_width=sample_width)
        except PlaybackError:
            pass
    elif system != "Darwin":
        if shutil.which("aplay"):
            try:
                return _SubprocessPcmPlayer(
                    [
                        "aplay",
                        "-q",
                        "-f",
                        "S16_LE",
                        "-r",
                        str(sample_rate),
                        "-c",
                        str(channels),
                    ],
                    name="aplay",
                )
            except PlaybackError:
                pass
        if shutil.which("paplay"):
            # paplay can take raw via --raw if pulse supports it; prefer ffplay above.
            try:
                return _SubprocessPcmPlayer(
                    [
                        "paplay",
                        "--raw",
                        f"--rate={sample_rate}",
                        f"--channels={channels}",
                        f"--format=s16le",
                    ],
                    name="paplay",
                )
            except PlaybackError:
                pass

    return _BufferPcmPlayer(sample_rate, channels=channels, sample_width=sample_width)


def stream_play_available() -> bool:
    """True when a true stream backend (not buffer-only) can be opened."""
    if shutil.which("ffplay"):
        return True
    system = platform.system()
    if system == "Windows":
        return _winmm_available()
    if system != "Darwin":
        return bool(shutil.which("aplay") or shutil.which("paplay"))
    return False


def _winmm_available() -> bool:
    if platform.system() != "Windows":
        return False
    try:
        import ctypes  # noqa: F401

        ctypes.windll.winmm  # type: ignore[attr-defined]
        return True
    except Exception:
        return False


class _BufferPcmPlayer:
    """Collect PCM and play as a single WAV when closed (no TTFA win)."""

    mode = "buffer"

    def __init__(
        self,
        sample_rate: int,
        *,
        channels: int = 1,
        sample_width: int = 2,
    ) -> None:
        self._sample_rate = sample_rate
        self._channels = channels
        self._sample_width = sample_width
        self._buf = bytearray()
        self._closed = False

    def write(self, pcm: bytes) -> None:
        if self._closed:
            return
        if pcm:
            self._buf.extend(pcm)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if not self._buf:
            return
        play_wav_bytes(
            pcm_to_wav_bytes(
                bytes(self._buf),
                sample_rate=self._sample_rate,
                channels=self._channels,
                sample_width=self._sample_width,
            )
        )
        self._buf.clear()

    def abort(self) -> None:
        self._closed = True
        self._buf.clear()


class _SubprocessPcmPlayer:
    """Pipe raw PCM into an external player (ffplay/aplay/paplay)."""

    mode = "stream"

    def __init__(self, cmd: list[str], *, name: str) -> None:
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as e:
            raise PlaybackError(f"{name} failed to start: {e}") from e
        if self._proc.stdin is None:
            raise PlaybackError(f"{name} stdin unavailable")
        self._name = name
        self._closed = False

    def write(self, pcm: bytes) -> None:
        if self._closed or not pcm:
            return
        try:
            assert self._proc.stdin is not None
            self._proc.stdin.write(pcm)
            self._proc.stdin.flush()
        except BrokenPipeError as e:
            raise PlaybackError(f"{self._name} pipe closed early") from e

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
        except OSError:
            pass
        try:
            self._proc.wait(timeout=120)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait(timeout=5)

    def abort(self) -> None:
        self._closed = True
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
        except OSError:
            pass
        try:
            self._proc.kill()
        except OSError:
            pass


class _FFplayPcmPlayer(_SubprocessPcmPlayer):
    def __init__(self, sample_rate: int, *, channels: int = 1) -> None:
        cmd = [
            "ffplay",
            "-nodisp",
            "-autoexit",
            "-loglevel",
            "quiet",
            "-f",
            "s16le",
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            "-i",
            "pipe:0",
        ]
        super().__init__(cmd, name="ffplay")


class _WinmmPcmPlayer:
    """Windows winmm waveOut streaming for s16le PCM."""

    mode = "stream"

    def __init__(
        self,
        sample_rate: int,
        *,
        channels: int = 1,
        sample_width: int = 2,
    ) -> None:
        import ctypes
        from ctypes import wintypes

        if sample_width != 2:
            raise PlaybackError("winmm player only supports 16-bit PCM")

        self._ctypes = ctypes
        self._winmm = ctypes.windll.winmm
        self._sample_rate = sample_rate
        self._channels = channels
        self._closed = False
        # Keep buffers alive while waveOut owns them
        self._held: list[bytes] = []
        self._headers: list[ctypes.Structure] = []
        self._min_chunk = max(sample_rate * channels * sample_width // 10, 2048)  # ~100ms
        self._pending = bytearray()

        class WAVEFORMATEX(ctypes.Structure):
            _fields_ = [
                ("wFormatTag", wintypes.WORD),
                ("nChannels", wintypes.WORD),
                ("nSamplesPerSec", wintypes.DWORD),
                ("nAvgBytesPerSec", wintypes.DWORD),
                ("nBlockAlign", wintypes.WORD),
                ("wBitsPerSample", wintypes.WORD),
                ("cbSize", wintypes.WORD),
            ]

        class WAVEHDR(ctypes.Structure):
            _fields_ = [
                ("lpData", ctypes.c_void_p),
                ("dwBufferLength", wintypes.DWORD),
                ("dwBytesRecorded", wintypes.DWORD),
                ("dwUser", ctypes.POINTER(ctypes.c_ulong)),
                ("dwFlags", wintypes.DWORD),
                ("dwLoops", wintypes.DWORD),
                ("lpNext", ctypes.c_void_p),
                ("reserved", ctypes.POINTER(ctypes.c_ulong)),
            ]

        self._WAVEHDR = WAVEHDR
        self._h = wintypes.HANDLE()
        fmt = WAVEFORMATEX()
        fmt.wFormatTag = 1  # WAVE_FORMAT_PCM
        fmt.nChannels = channels
        fmt.nSamplesPerSec = sample_rate
        fmt.wBitsPerSample = sample_width * 8
        fmt.nBlockAlign = channels * sample_width
        fmt.nAvgBytesPerSec = sample_rate * fmt.nBlockAlign
        fmt.cbSize = 0

        # WAVE_MAPPER = -1
        r = self._winmm.waveOutOpen(
            ctypes.byref(self._h),
            0xFFFFFFFF,
            ctypes.byref(fmt),
            0,
            0,
            0,
        )
        if r != 0:
            raise PlaybackError(f"waveOutOpen failed: {r}")

    def write(self, pcm: bytes) -> None:
        if self._closed or not pcm:
            return
        self._pending.extend(pcm)
        while len(self._pending) >= self._min_chunk:
            piece = bytes(self._pending[: self._min_chunk])
            del self._pending[: self._min_chunk]
            self._submit(piece)

    def _submit(self, pcm: bytes) -> None:
        import ctypes
        from ctypes import wintypes

        if not pcm:
            return
        # Align to frame size (2 bytes mono)
        frame = self._channels * 2
        n = len(pcm) - (len(pcm) % frame)
        if n <= 0:
            return
        pcm = pcm[:n]
        self._held.append(pcm)
        buf = ctypes.create_string_buffer(pcm)
        # Keep the ctypes buffer alive too
        self._held.append(buf)  # type: ignore[arg-type]

        hdr = self._WAVEHDR()
        hdr.lpData = ctypes.cast(buf, ctypes.c_void_p)
        hdr.dwBufferLength = n
        hdr.dwFlags = 0
        hdr.dwLoops = 0
        self._headers.append(hdr)

        r = self._winmm.waveOutPrepareHeader(
            self._h, ctypes.byref(hdr), ctypes.sizeof(hdr)
        )
        if r != 0:
            raise PlaybackError(f"waveOutPrepareHeader failed: {r}")
        r = self._winmm.waveOutWrite(self._h, ctypes.byref(hdr), ctypes.sizeof(hdr))
        if r != 0:
            raise PlaybackError(f"waveOutWrite failed: {r}")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._pending:
            self._submit(bytes(self._pending))
            self._pending.clear()
        self._wait_done()
        self._cleanup()

    def abort(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._pending.clear()
        try:
            self._winmm.waveOutReset(self._h)
        except Exception:
            pass
        self._cleanup()

    def _wait_done(self, timeout: float = 120.0) -> None:
        import ctypes

        # WHDR_DONE = 0x00000001
        deadline = time.time() + timeout
        while time.time() < deadline:
            pending = False
            for hdr in self._headers:
                if (hdr.dwFlags & 0x00000001) == 0:
                    pending = True
                    break
            if not pending:
                return
            time.sleep(0.01)
        # Timed out — reset device
        try:
            self._winmm.waveOutReset(self._h)
        except Exception:
            pass

    def _cleanup(self) -> None:
        import ctypes

        for hdr in self._headers:
            try:
                self._winmm.waveOutUnprepareHeader(
                    self._h, ctypes.byref(hdr), ctypes.sizeof(hdr)
                )
            except Exception:
                pass
        self._headers.clear()
        try:
            self._winmm.waveOutClose(self._h)
        except Exception:
            pass
        self._held.clear()
