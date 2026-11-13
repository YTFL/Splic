"""
silence_detector.py — Local silence detection for Splic Indic Auto-Editor.

Preferred path : pydub (libav/ffmpeg-backed, handles MP3/AAC/etc.)
Fallback path  : stdlib `wave` + pure-Python PCM RMS scanner
                 (any PCM WAV; multi-channel is downmixed)

The pipeline always passes canonical 16 kHz mono WAV (see audio_utils.py),
which pydub decodes natively without needing ffmpeg.
"""

from __future__ import annotations

import io
import math
from typing import Any

# ---------------------------------------------------------------------------
# Optional pydub import
# ---------------------------------------------------------------------------
import warnings

try:
    with warnings.catch_warnings():
        # pydub warns at import time when ffmpeg is not on PATH; we only feed it
        # RIFF WAV (decoded natively) or let audio_utils' ffmpeg handle the rest.
        warnings.simplefilter("ignore", RuntimeWarning)
        from pydub import AudioSegment
        from pydub.silence import detect_silence as _pydub_detect_silence

    _PYDUB_AVAILABLE = True
except ImportError:  # pragma: no cover - e.g. Python 3.13+ without audioop-lts
    _PYDUB_AVAILABLE = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_silences(
    audio_bytes: bytes,
    min_silence_ms: int = 550,
    silence_thresh_dbfs: float = -36.0,
    padding_ms: int = 40,
) -> list[dict[str, Any]]:
    """Detect silent intervals in *audio_bytes*.

    Parameters
    ----------
    audio_bytes:
        Raw audio file bytes (any format pydub supports, or 16kHz 16-bit mono
        WAV when only the stdlib fallback is available).
    min_silence_ms:
        Minimum run of silence (in ms) that qualifies as a gap worth cutting.
    silence_thresh_dbfs:
        dBFS threshold below which audio is considered silent (e.g. -36.0).
    padding_ms:
        Milliseconds to trim *inward* from both edges of each detected silence
        so that speech edges are not clipped.

    Returns
    -------
    list[dict]
        Each dict: ``{"start": float, "end": float, "duration": float,
        "reason": "dead_air"}`` with timestamps in seconds (3 d.p.).
        Intervals shorter than 150 ms after padding are dropped.
    """
    if _PYDUB_AVAILABLE:
        try:
            return _detect_pydub(audio_bytes, min_silence_ms, silence_thresh_dbfs, padding_ms)
        except Exception:
            if audio_bytes[:4] != b"RIFF":
                raise
            # fall through to the stdlib scanner for WAV input
    return _detect_pcm(audio_bytes, min_silence_ms, silence_thresh_dbfs, padding_ms)


# ---------------------------------------------------------------------------
# pydub implementation
# ---------------------------------------------------------------------------


def _detect_pydub(
    audio_bytes: bytes,
    min_silence_ms: int,
    silence_thresh_dbfs: float,
    padding_ms: int,
) -> list[dict[str, Any]]:
    fmt = "wav" if audio_bytes[:4] == b"RIFF" else None
    audio: AudioSegment = AudioSegment.from_file(io.BytesIO(audio_bytes), format=fmt)

    raw_intervals: list[list[int]] = _pydub_detect_silence(
        audio,
        min_silence_len=min_silence_ms,
        silence_thresh=silence_thresh_dbfs,
        seek_step=10,  # 10ms resolution: ~100x faster than 1ms, ample for cuts
    )

    return _build_results(raw_intervals, padding_ms)


# ---------------------------------------------------------------------------
# Pure-PCM stdlib fallback
# ---------------------------------------------------------------------------


def _detect_pcm(
    audio_bytes: bytes,
    min_silence_ms: int,
    silence_thresh_dbfs: float,
    padding_ms: int,
) -> list[dict[str, Any]]:
    """Decode a PCM WAV (any channel count / width) and scan for silences."""
    from audio_utils import _read_wav_mono_int16

    samples, framerate = _read_wav_mono_int16(audio_bytes)
    n_samples = len(samples)
    if n_samples == 0:
        return []

    # Convert dBFS threshold -> linear RMS amplitude (16-bit peak = 32768)
    linear_thresh = 32768.0 * (10.0 ** (silence_thresh_dbfs / 20.0))

    # 20ms sliding window
    window_ms = 20
    window_size = max(1, int(framerate * window_ms / 1000))

    # Build list of (start_ms, end_ms) silent runs
    raw_intervals: list[list[int]] = []
    silence_start: int | None = None

    for i in range(0, n_samples, window_size):
        chunk = samples[i : i + window_size]
        rms = math.sqrt(sum(s * s for s in chunk) / len(chunk))
        window_start_ms = int(i * 1000 / framerate)
        window_end_ms = int((i + len(chunk)) * 1000 / framerate)

        if rms < linear_thresh:
            if silence_start is None:
                silence_start = window_start_ms
        else:
            if silence_start is not None:
                run_len = window_start_ms - silence_start
                if run_len >= min_silence_ms:
                    raw_intervals.append([silence_start, window_start_ms])
                silence_start = None

    # Close any trailing silence
    if silence_start is not None:
        end_ms = int(n_samples * 1000 / framerate)
        run_len = end_ms - silence_start
        if run_len >= min_silence_ms:
            raw_intervals.append([silence_start, end_ms])

    return _build_results(raw_intervals, padding_ms)


# ---------------------------------------------------------------------------
# Shared post-processing
# ---------------------------------------------------------------------------

_MIN_AFTER_PADDING_MS = 150  # drop intervals narrower than this after trimming


def _build_results(
    raw_intervals: list[list[int]],
    padding_ms: int,
) -> list[dict[str, Any]]:
    """Apply inward padding, drop short intervals, and format output."""
    results: list[dict[str, Any]] = []

    for start_ms, end_ms in raw_intervals:
        padded_start_ms = start_ms + padding_ms
        padded_end_ms = end_ms - padding_ms

        if padded_end_ms - padded_start_ms < _MIN_AFTER_PADDING_MS:
            continue  # too short after padding — keep speech intact

        start_s = round(padded_start_ms / 1000.0, 3)
        end_s = round(padded_end_ms / 1000.0, 3)
        duration_s = round(end_s - start_s, 3)

        results.append(
            {
                "start": start_s,
                "end": end_s,
                "duration": duration_s,
                "reason": "dead_air",
            }
        )

    return results


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python silence_detector.py <audio_file>")
        print(
            "       Detects silences in the given audio file and prints a JSON list."
        )
        sys.exit(0)

    import json

    audio_path = sys.argv[1]
    with open(audio_path, "rb") as fh:
        data = fh.read()

    backend = "pydub" if _PYDUB_AVAILABLE else "pure-PCM (stdlib wave)"
    print(f"[silence_detector] Using backend: {backend}")

    silences = detect_silences(data)
    print(json.dumps(silences, indent=2))
    print(f"\n[silence_detector] Found {len(silences)} silent interval(s).")
