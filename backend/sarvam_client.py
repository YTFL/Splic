"""
sarvam_client.py — Sarvam AI API client for Splic Indic Auto-Editor.

Provides:
  - transcribe_audio()   : Sarvam Saaras v4 speech-to-text (Romanized Indic, word timestamps)
  - direct_video_edit()  : Sarvam-105B Conversations video director LLM (JSON mode),
                           with Groq / Gemini fallback when Sarvam fails or times out

Environment variables (loaded by config.py via python-dotenv):
  USE_MOCK           : "true" to use sample_edit_plan.json instead of live APIs (default true)
  SARVAM_API_KEY     : Sarvam subscription key
  FALLBACK_PROVIDER  : "none" | "groq" | "gemini"
  GROQ_API_KEY       : Required when FALLBACK_PROVIDER=groq
  GEMINI_API_KEY     : Required when FALLBACK_PROVIDER=gemini
  SARVAM_STT_MODEL   : override (default "saaras:v4")
  SARVAM_LLM_MODEL   : override (default "sarvam-105b-conversations")
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger("sarvam_client")

# ---------------------------------------------------------------------------
# Config accessors (python-dotenv already called in config.py)
# ---------------------------------------------------------------------------

def _is_mock() -> bool:
    return os.getenv("USE_MOCK", "true").strip().lower() in ("1", "true", "yes", "on")


def is_mock_enabled() -> bool:
    return _is_mock()


def _resolve_mock(mock: Optional[bool]) -> bool:
    return _is_mock() if mock is None else bool(mock)


def _get_sarvam_api_key() -> str:
    return os.getenv("SARVAM_API_KEY", "").strip()


def _get_fallback_provider() -> str:
    return os.getenv("FALLBACK_PROVIDER", "none").strip().lower()


def _stt_model() -> str:
    return os.getenv("SARVAM_STT_MODEL", "saaras:v4")


def _llm_model() -> str:
    return os.getenv("SARVAM_LLM_MODEL", "sarvam-105b-conversations")


_SAMPLE_PLAN_PATH: Path = Path(__file__).resolve().parent / "sample_edit_plan.json"

_STT_TIMEOUT: float = 60.0
_LLM_TIMEOUT: float = 90.0
_STT_CHUNK_SECONDS: float = 25.0   # Sarvam's synchronous STT accepts ~30 s per request

_SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
_SARVAM_CHAT_URL = "https://api.sarvam.ai/v2/chat/completions"
_GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
_GEMINI_CHAT_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

# ---------------------------------------------------------------------------
# Director LLM system prompt
# ---------------------------------------------------------------------------

DIRECTOR_SYSTEM_PROMPT: str = """You are an expert short-form viral video editor for Instagram Reels and YouTube Shorts made by Indian creators.
You receive a Romanized Indic (Hinglish/Tanglish/etc.) transcript with word timestamps (float seconds), the total duration, and pre-detected acoustic silence intervals.

Tasks:
1. CUTS: ripple-cut dead-air pauses > 0.6s and filler hesitations ("uhm", "matlab", "arre", "basically", "toh", "like"). Use silence_cuts as candidates. NEVER cut meaningful words. Each cut: {"start", "end", "reason"} with reason "dead_air" or "filler_word".
2. TRANSITIONS: for each cut choose one of fade_black | wipe_left | crossfade | zoom_in, at the cut's end time, duration 0.3.
3. CAPTIONS: group the words, in order, into 2-to-4 word karaoke chunks (max ~1.8s each). Each chunk: {"text": "<the exact words joined by spaces>"}. Do not change spellings.
4. STICKERS: Indian brands, foods, places, celebrities, objects and cultural terms that are mentioned. Each: {"keyword", "start" (first mention time), "duration": 2.0, "position": {"x": 0..1, "y": 0..1}, "scale": 1.0}. Max 6.
5. SFX: punchlines, surprises, money moments. Each: {"asset": one of "vine_boom" | "cash" | "ding" | "record_scratch" | "laugh" | "gasp" | "wrong" | "clap" | "whoosh", "start", "volume": 0.8, "label"}.
6. ZOOMS: 1.25x punch-in on high-energy statements: {"start", "end", "scale": 1.25}. Max 3.

All times are float seconds on the ORIGINAL clock. Output ONLY one JSON object, no markdown, no explanation:
{"cuts":[...],"transitions":[...],"captions":[...],"stickers":[...],"sfx":[...],"zooms":[...]}"""


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def load_sample_plan() -> dict:
    """Load the cached sample edit plan from disk. Raises if missing."""
    if not _SAMPLE_PLAN_PATH.exists():
        raise FileNotFoundError(f"Mock mode is enabled but sample plan not found at: {_SAMPLE_PLAN_PATH}")
    with _SAMPLE_PLAN_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


_load_sample_plan = load_sample_plan  # backwards-compatible alias


# ---------------------------------------------------------------------------
# Speech-to-text
# ---------------------------------------------------------------------------

def normalize_stt_response(resp: Dict[str, Any], offset: float = 0.0) -> Dict[str, Any]:
    """Normalise Sarvam STT JSON into {"transcript", "words":[{word,start_time,end_time}], "language_code"}.

    Handles both shapes:
      * {"words": [{"word", "start_time", "end_time"}]}
      * {"timestamps": {"words": [...], "start_time_seconds": [...], "end_time_seconds": [...]}}
    Timestamp entries that contain several words (phrase-level) are split proportionally
    by character length so every caption word gets its own highlight timing.
    """
    transcript = str(resp.get("transcript") or "").strip()
    entries: List[Tuple[str, float, float]] = []

    if isinstance(resp.get("words"), list):
        for w in resp["words"]:
            if isinstance(w, dict):
                s = w.get("start_time", w.get("start"))
                e = w.get("end_time", w.get("end"))
                if w.get("word") is not None and s is not None and e is not None:
                    entries.append((str(w["word"]), float(s), float(e)))
    ts = resp.get("timestamps")
    if not entries and isinstance(ts, dict):
        toks = ts.get("words") or []
        starts = ts.get("start_time_seconds") or []
        ends = ts.get("end_time_seconds") or []
        for tok, s, e in zip(toks, starts, ends):
            entries.append((str(tok), float(s), float(e)))

    words: List[Dict[str, Any]] = []
    for text, s, e in entries:
        parts = text.split()
        if not parts:
            continue
        span = max(e - s, 0.01)
        total_chars = sum(len(p) for p in parts) or 1
        t = s
        for p in parts:
            d = span * len(p) / total_chars
            words.append({
                "word": p,
                "start_time": round(t + offset, 3),
                "end_time": round(t + d + offset, 3),
            })
            t += d

    if not transcript:
        transcript = " ".join(w["word"] for w in words)
    return {
        "transcript": transcript,
        "words": words,
        "language_code": resp.get("language_code"),
    }


def _stt_request(wav_bytes: bytes, filename: str, language_code: str) -> Dict[str, Any]:
    key = _get_sarvam_api_key()
    if not key:
        raise RuntimeError("SARVAM_API_KEY is not set. Add it to backend/.env or set USE_MOCK=true.")
    data = {
        "model": _stt_model(),
        "mode": "transliteration",
        "with_timestamps": "true",
    }
    if language_code:
        data["language_code"] = language_code
    with httpx.Client(timeout=_STT_TIMEOUT) as client:
        response = client.post(
            _SARVAM_STT_URL,
            headers={"api-subscription-key": key},
            data=data,
            files={"file": (filename, wav_bytes, "audio/wav")},
        )
    if response.status_code != 200:
        raise RuntimeError(f"Sarvam STT returned HTTP {response.status_code}: {response.text[:500]}")
    return response.json()


def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    language_code: str = "hi-IN",
    mock: Optional[bool] = None,
) -> dict:
    """Transcribe audio using Sarvam Saaras v4 in transliteration mode.

    ``audio_bytes`` should be the canonical 16 kHz mono WAV from audio_utils.
    Audio longer than ~25 s is split and the word timestamps are re-offset.

    Returns ``{"transcript": str, "words": [...], "language_code": str|None}``.
    """
    if _resolve_mock(mock):
        plan = load_sample_plan()
        return {
            "transcript": plan.get("transcript", ""),
            "words": plan.get("words", []),
            "language_code": plan.get("language_code"),
        }

    pieces: List[Tuple[float, bytes]] = [(0.0, audio_bytes)]
    if audio_bytes[:4] == b"RIFF":
        from audio_utils import split_wav

        pieces = split_wav(audio_bytes, _STT_CHUNK_SECONDS)

    transcripts, words, detected = [], [], None
    stem = Path(filename or "audio").stem or "audio"
    for i, (offset, chunk) in enumerate(pieces):
        resp = _stt_request(chunk, f"{stem}_{i}.wav", language_code)
        norm = normalize_stt_response(resp, offset=offset)
        if norm["transcript"]:
            transcripts.append(norm["transcript"])
        words.extend(norm["words"])
        detected = detected or norm.get("language_code")
    return {"transcript": " ".join(transcripts), "words": words, "language_code": detected}


# ---------------------------------------------------------------------------
# Director LLM
# ---------------------------------------------------------------------------

def _build_user_message(
    transcript: str,
    words: list[dict],
    silence_cuts: list[dict],
    language_code: str,
    duration: Optional[float] = None,
) -> str:
    payload = {
        "language_code": language_code,
        "duration": duration,
        "transcript": transcript,
        "words": [
            {"w": w.get("word"), "s": w.get("start_time"), "e": w.get("end_time")} for w in words
        ],
        "silence_cuts": [{"start": c.get("start"), "end": c.get("end")} for c in silence_cuts],
    }
    return json.dumps(payload, ensure_ascii=False)


def direct_video_edit(
    transcript: str,
    words: list[dict],
    silence_cuts: list[dict],
    language_code: str = "hi-IN",
    duration: Optional[float] = None,
    mock: Optional[bool] = None,
) -> dict:
    """Ask the director LLM for creative edit decisions.

    Returns the raw director dict plus ``"director"`` (provider that answered) and
    ``"warnings"``. The caller must pass it through plan_builder.build_edit_plan()
    before validating against schemas.EditPlan.

    Raises RuntimeError only if Sarvam AND the configured fallback both fail.
    """
    if _resolve_mock(mock):
        plan = load_sample_plan()
        plan["director"] = "mock"
        return plan

    messages = [
        {"role": "system", "content": DIRECTOR_SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_message(transcript, words, silence_cuts, language_code, duration)},
    ]

    warnings: List[str] = []
    providers = [("sarvam", _call_sarvam)]
    fallback = _get_fallback_provider()
    if fallback == "groq":
        providers.append(("groq", _call_groq))
    elif fallback == "gemini":
        providers.append(("gemini", _call_gemini))

    errors = []
    for name, fn in providers:
        try:
            plan = fn(messages)
            plan["director"] = name
            plan["warnings"] = warnings
            return plan
        except Exception as exc:  # timeout, HTTP error, bad JSON...
            logger.warning("Director provider %s failed: %s", name, exc)
            errors.append(f"{name}: {exc}")
            warnings.append(f"Director '{name}' failed ({type(exc).__name__}); trying next option")
    raise RuntimeError("All director providers failed: " + " | ".join(errors))


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

def _post_chat(url: str, headers: dict, payload: dict, provider: str) -> dict:
    with httpx.Client(timeout=_LLM_TIMEOUT) as client:
        response = client.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise RuntimeError(f"{provider} LLM returned HTTP {response.status_code}: {response.text[:500]}")
    return parse_chat_response(response.json(), provider=provider)


def _call_sarvam(messages: list[dict]) -> dict:
    key = _get_sarvam_api_key()
    if not key:
        raise RuntimeError("SARVAM_API_KEY is not set. Add it to backend/.env or set USE_MOCK=true.")
    payload = {
        "model": _llm_model(),
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "messages": messages,
    }
    headers = {
        "api-subscription-key": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    return _post_chat(_SARVAM_CHAT_URL, headers, payload, "sarvam")


def _call_groq(messages: list[dict]) -> dict:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set but FALLBACK_PROVIDER=groq.")
    payload = {
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "messages": messages,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    return _post_chat(_GROQ_CHAT_URL, headers, payload, "groq")


def _call_gemini(messages: list[dict]) -> dict:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set but FALLBACK_PROVIDER=gemini.")
    payload = {
        "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "messages": messages,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    return _post_chat(_GEMINI_CHAT_URL, headers, payload, "gemini")


def extract_json_object(content: str) -> dict:
    """Parse a JSON object from LLM text, tolerating <think> blocks and ``` fences."""
    text = re.sub(r"<think>.*?</think>", "", content or "", flags=re.DOTALL).strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise
        obj = json.loads(text[start:end + 1])
    if not isinstance(obj, dict):
        raise ValueError("Director output is not a JSON object")
    return obj


def parse_chat_response(response_json: dict, provider: str = "sarvam") -> dict:
    """Extract and parse the JSON edit plan from a chat completion response."""
    try:
        content = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"{provider} response missing choices[0].message.content") from exc
    try:
        return extract_json_object(content)
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"{provider} returned non-JSON content: {str(content)[:300]!r}") from exc


_parse_chat_response = parse_chat_response  # backwards-compatible alias
