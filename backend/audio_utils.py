"""
audio_utils.py — Normalise uploaded media into 16 kHz mono 16-bit PCM WAV.

Every downstream stage (silence detection, Sarvam STT chunking) works on the
same canonical WAV so timestamps stay on one clock.

ffmpeg resolution order:
  1. ``FFMPEG_PATH`` env var
  2. ``ffmpeg`` on PATH
  3. the binary bundled with the ``imageio-ffmpeg`` pip package
If no ffmpeg is found, plain PCM WAV uploads still work (pure-stdlib path);
compressed audio and video containers raise ``AudioDecodeError``.
"""

from __future__ import annotations

import array
import io
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional

TARGET_RATE = 16000


class AudioDecodeError(RuntimeError):
    """Raised when an upload cannot be decoded into PCM audio."""


@dataclass
class PreparedAudio:
    wav_bytes: bytes          # 16 kHz mono 16-bit PCM WAV
    duration: float           # seconds
    sample_rate: int = TARGET_RATE


@lru_cache(maxsize=1)
def find_ffmpeg() -> Optional[str]:
    env_path = os.getenv("FFMPEG_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path
    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def has_ffmpeg() -> bool:
    return find_ffmpeg() is not None


def _is_riff_wav(data: bytes) -> bool:
    return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"


def _ffmpeg_to_wav(data: bytes, ffmpeg: str) -> bytes:
    """Transcode arbitrary audio/video bytes to 16 kHz mono s16 WAV via ffmpeg."""
    # Containers like MP4/MOV need a seekable input, so go through a temp file.
    fd, in_path = tempfile.mkstemp(prefix="splic_in_")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        cmd = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin",
            "-i", in_path,
            "-vn", "-ac", "1", "-ar", str(TARGET_RATE),
            "-acodec", "pcm_s16le", "-f", "wav", "pipe:1",
        ]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        proc = subprocess.run(cmd, capture_output=True, timeout=120, creationflags=creationflags)
    finally:
        try:
            os.remove(in_path)
        except OSError:
            pass

    if proc.returncode != 0 or not _is_riff_wav(proc.stdout):
        err = proc.stderr.decode("utf-8", errors="replace").strip()[:500]
        raise AudioDecodeError(f"ffmpeg could not decode the upload: {err or 'no audio stream found'}")
    return _fix_wav_header(proc.stdout)


def _fix_wav_header(wav: bytes) -> bytes:
    """ffmpeg writing to a pipe leaves RIFF/data sizes unset; rewrite cleanly."""
    samples, rate = _read_wav_mono_int16(wav, tolerate_bad_sizes=True)
    return encode_wav(samples, rate)


def _read_wav_mono_int16(wav: bytes, tolerate_bad_sizes: bool = False) -> tuple[array.array, int]:
    """Decode a PCM WAV into mono int16 samples (downmixing / width-converting)."""
    if tolerate_bad_sizes:
        # Locate the 'data' chunk manually and read to EOF (handles size=0xFFFFFFFF).
        pos = 12
        fmt = None
        while pos + 8 <= len(wav):
            cid = wav[pos:pos + 4]
            size = int.from_bytes(wav[pos + 4:pos + 8], "little")
            body = pos + 8
            if cid == b"fmt ":
                fmt = wav[body:body + size]
            elif cid == b"data":
                if fmt is None:
                    break
                channels = int.from_bytes(fmt[2:4], "little")
                rate = int.from_bytes(fmt[4:8], "little")
                width = int.from_bytes(fmt[14:16], "little") // 8
                raw = wav[body:]
                return _pcm_to_mono_int16(raw, channels, width), rate
            pos = body + size + (size & 1)
        raise AudioDecodeError("Malformed WAV stream from ffmpeg")

    try:
        with wave.open(io.BytesIO(wav), "rb") as wf:
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            rate = wf.getframerate()
            raw = wf.readframes(wf.getnframes())
    except (wave.Error, EOFError) as exc:
        raise AudioDecodeError(f"Unsupported WAV file: {exc}") from exc
    return _pcm_to_mono_int16(raw, channels, width), rate


def _pcm_to_mono_int16(raw: bytes, channels: int, width: int) -> array.array:
    if width == 2:
        samples = array.array("h")
        samples.frombytes(raw[: len(raw) - len(raw) % 2])
    elif width == 1:  # unsigned 8-bit
        samples = array.array("h", ((b - 128) << 8 for b in raw))
    elif width == 4:
        wide = array.array("i")
        wide.frombytes(raw[: len(raw) - len(raw) % 4])
        samples = array.array("h", (s >> 16 for s in wide))
    elif width == 3:
        n = len(raw) // 3
        samples = array.array(
            "h",
            (int.from_bytes(raw[i * 3:i * 3 + 3], "little", signed=True) >> 8 for i in range(n)),
        )
    else:
        raise AudioDecodeError(f"Unsupported PCM sample width: {width * 8}-bit")

    if sys.byteorder == "big":
        samples.byteswap()

    if channels > 1:
        frames = len(samples) // channels
        samples = array.array(
            "h",
            (sum(samples[f * channels:(f + 1) * channels]) // channels for f in range(frames)),
        )
    return samples


def _resample_linear(samples: array.array, src_rate: int, dst_rate: int) -> array.array:
    if src_rate == dst_rate or not samples:
        return samples
    ratio = src_rate / dst_rate
    n_out = int(len(samples) / ratio)
    last = len(samples) - 1
    out = array.array("h", bytes(2 * n_out))
    for i in range(n_out):
        pos = i * ratio
        j = int(pos)
        frac = pos - j
        a = samples[j]
        b = samples[j + 1] if j < last else a
        out[i] = int(a + (b - a) * frac)
    return out


def encode_wav(samples: array.array, rate: int = TARGET_RATE) -> bytes:
    buf = io.BytesIO()
    data = samples
    if sys.byteorder == "big":
        data = array.array("h", samples)
        data.byteswap()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(data.tobytes())
    return buf.getvalue()


def prepare_audio(data: bytes, filename: str = "") -> PreparedAudio:
    """Convert any uploaded audio/video into canonical 16 kHz mono WAV."""
    if not data:
        raise AudioDecodeError("Uploaded file is empty")

    ffmpeg = find_ffmpeg()
    if ffmpeg:
        wav = _ffmpeg_to_wav(data, ffmpeg)
    elif _is_riff_wav(data):
        samples, rate = _read_wav_mono_int16(data)
        wav = encode_wav(_resample_linear(samples, rate, TARGET_RATE), TARGET_RATE)
    else:
        raise AudioDecodeError(
            f"Cannot decode '{filename or 'upload'}' without ffmpeg. "
            "Upload a PCM .wav file or `pip install imageio-ffmpeg`."
        )

    n_samples = (len(wav) - 44) // 2
    return PreparedAudio(wav_bytes=wav, duration=round(n_samples / TARGET_RATE, 3))


def split_wav(wav: bytes, max_seconds: float) -> List[tuple[float, bytes]]:
    """Split a canonical WAV into <= max_seconds pieces: [(offset_seconds, wav_bytes)]."""
    samples, rate = _read_wav_mono_int16(wav)
    step = int(max_seconds * rate)
    if len(samples) <= step:
        return [(0.0, wav)]
    pieces = []
    for start in range(0, len(samples), step):
        pieces.append((start / rate, encode_wav(samples[start:start + step], rate)))
    return pieces
