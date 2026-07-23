"""Cross-platform audio playback for WAV files."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


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
