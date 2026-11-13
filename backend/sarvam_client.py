"""
sarvam_client.py — Sarvam AI API client for Splic Indic Auto-Editor.

Provides:
  - transcribe_audio()   : Sarvam Saaras v4 speech-to-text (mode="translit", Romanized Indic)
  - direct_video_edit()  : GLM-5.3-flash video director on the Sarvam API (JSON mode).
                           ONE call returns two JSON documents:
                             sticker_requests -> sticker scraper / library
                             edit_plan        -> cuts, transitions, sticker placements
                                                 (+ in/out animations), sfx, zooms, effects
                           Groq / Gemini fallback when Sarvam fails or times out.

Environment variables (loaded from backend/.env by config.py via python-dotenv):
  SARVAM_API_KEY     : Sarvam subscription key (required)
  FALLBACK_PROVIDER  : "none" | "groq" | "gemini"
  GROQ_API_KEY       : Required when FALLBACK_PROVIDER=groq
  GEMINI_API_KEY     : Required when FALLBACK_PROVIDER=gemini
  SARVAM_STT_MODEL   : override (default "saaras:v4")
  SARVAM_LLM_MODEL   : override (default "glm5.3-flash")
  SARVAM_MAX_TOKENS  : completion budget for the director (default 8000, 0 = omit)
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

_PLACEHOLDER_KEYS = ("", "your_sarvam_api_subscription_key")


def _get_sarvam_api_key() -> str:
    key = os.getenv("SARVAM_API_KEY", "").strip()
    return "" if key in _PLACEHOLDER_KEYS else key


def is_sarvam_configured() -> bool:
    return bool(_get_sarvam_api_key())


def _get_fallback_provider() -> str:
    return os.getenv("FALLBACK_PROVIDER", "none").strip().lower()


# ---------------------------------------------------------------------------
# Sarvam model registry
# Verified against https://docs.sarvam.ai/api/getting-started/models and
# GET https://api.sarvam.ai/v2/models (model ids are case-sensitive).
# ---------------------------------------------------------------------------
SAARAS_STT_MODEL = "saaras:v4"              # latest/recommended ASR; "saaras:v3" still active
SAARAS_STT_MODES = ("transcribe", "translate", "verbatim", "translit", "codemix")
SAARAS_STT_MODE = "translit"                # Romanized Hinglish for karaoke captions
SARVAM_DIRECTOR_MODEL = "glm5.3-flash"      # listed by GET /v2/models; "sarvam-105b" still available
SARVAM_REASONING_EFFORTS = ("low", "medium", "high")


def _stt_model() -> str:
    return os.getenv("SARVAM_STT_MODEL", SAARAS_STT_MODEL)


def _stt_mode() -> str:
    mode = os.getenv("SARVAM_STT_MODE", SAARAS_STT_MODE).strip().lower()
    return mode if mode in SAARAS_STT_MODES else SAARAS_STT_MODE


def _llm_model() -> str:
    return os.getenv("SARVAM_LLM_MODEL", SARVAM_DIRECTOR_MODEL)


_STT_TIMEOUT: float = 60.0
# sarvam-105b is a reasoning model: the director prompt measured ~125 s and
# ~12k reasoning tokens even at reasoning_effort="low", so 90 s always timed out.
_LLM_TIMEOUT: float = float(os.getenv("SARVAM_LLM_TIMEOUT", "240"))


def _reasoning_effort() -> str:
    """"low" | "medium" | "high", or "" to omit the parameter.

    Only sarvam-105b documents reasoning_effort, so it is omitted by default for
    other models unless SARVAM_REASONING_EFFORT is set explicitly.
    """
    default = "low" if _llm_model().startswith("sarvam-105b") else ""
    return os.getenv("SARVAM_REASONING_EFFORT", default).strip().lower()


def _max_tokens() -> int:
    try:
        return max(0, int(os.getenv("SARVAM_MAX_TOKENS", "8000")))
    except ValueError:
        return 8000


_STT_CHUNK_SECONDS: float = 25.0   # Sarvam's synchronous STT accepts ~30 s per request

_SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
_SARVAM_CHAT_URL = "https://api.sarvam.ai/v2/chat/completions"
_GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
_GEMINI_CHAT_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

# ---------------------------------------------------------------------------
# Director LLM system prompt
# ---------------------------------------------------------------------------

DIRECTOR_SYSTEM_PROMPT: str = """You are the lead editor for viral Indian short-form videos (Instagram Reels / YouTube Shorts).
You receive the script of ONE talking-head video: Romanized Indic (Hinglish/Tanglish/...) captions and word timestamps from speech-to-text, the duration, pre-detected silence intervals, the editor's catalog (the ONLY stickers, sounds, transitions, animations and effects you may use), and density targets.

EDITING STYLE: mildly aggressive. Something should happen on screen every few seconds - a sticker popping in, a punch-in zoom, a whoosh on a cut - so the viewer never gets bored. But every element must be motivated by what is being said at that moment. Never stack elements just to fill space, never decorate silence, never put two big moments on the same word.

Return exactly ONE JSON object with exactly two keys, no markdown, no commentary:
{"sticker_requests": [...], "edit_plan": {...}}

=== 1. sticker_requests (sent to the sticker scraper) ===
Find every stickerable concept in the script - be generous and think broadly, NOT only Indian foods and brands:
objects (phone, laptop, car, bag), foods and drinks, brands and apps, places and landmarks, people and roles (boss, mom, doctor), animals, emotions and reactions (shock, love, anger, crying, laughing, confused), actions (running, sleeping, cooking, studying), money and prices, time (morning, late night, deadline), weather, tech, numbers and achievements (first place, 10x, viral), festivals and culture.
Each request: {"ref": "s1", "concept": "<short English name>", "source": "library" | "scrape", "library_id": "<exact id>" (library only), "query": "<image search>" (scrape only)}
- concept is in English even when the speaker said it in Hindi etc. ("paisa" -> "money", "neend" -> "sleeping").
- PREFER THE LIBRARY: if any catalog.sticker_library entry fits the meaning, use source "library" with its exact id (money -> coins, amazing/hot -> flame, idea -> light bulb, shock -> surprise face, celebration -> confetti, sale/price -> tag). Entries with category "scraped" are previous downloads - reuse them freely.
- Otherwise use source "scrape" with a concise English image-search query that returns a clean, isolated image: brands -> "<Brand> logo"; objects/food -> "<thing> 3d icon"; emotions -> "<emotion> face emoji"; actions -> "<action> 3d emoji"; places -> "<place> landmark icon".
- One request per distinct concept; refs unique ("s1", "s2", ...). A concept that comes up again reuses its ref.

=== 2. edit_plan (applied to the timeline editor) ===
All times are float seconds on the ORIGINAL clock of the video (the word timestamps you were given). Use the exact ids from the catalog - anything else is discarded.

"cuts": [{"start", "end", "reason": "dead_air" | "filler_word"}]
  Remove dead air longer than ~0.5 s (silence_cuts are good candidates) and pure hesitation fillers (uhm, matlab, arre, basically...). NEVER cut a meaningful word.

"transitions": [{"at": <end time of the cut it covers>, "transition_id": <catalog.transitions>, "duration": 0.2-0.5}]
  Only on cut seams. Cover roughly 60-80% of interior cuts, skipping tiny mid-sentence filler cuts. Match the energy: "flash"/"zoom"/"glitch" for punchy topic jumps, "wipe-left"/"wipe-up"/"split"/mask transitions for a new point or list item, "fade"/"blur" for calm moments. Vary them; do not repeat the same id three times in a row.

"stickers": [{"ref": "s1", "start", "duration": 1.2-2.5, "x": 0-1, "y": 0-1, "scale": 0.7-1.4, "rotation": -15..15, "animation_in": <catalog.animation_in>, "animation_out": <catalog.animation_out>, "emphasis": <catalog.emphasis>}]
  - start = start_time of the word that triggers the sticker (it lands exactly on the word).
  - Placement: keep stickers off the speaker's face (avoid the centre x 0.35-0.65, y 0.25-0.6) and out of the caption band (y 0.62-0.9). Good spots: top-right (0.78, 0.2), top-left (0.22, 0.2), mid-right (0.8, 0.45), mid-left (0.2, 0.45), top-centre (0.5, 0.14). Alternate sides between consecutive stickers. At most 2 stickers on screen at once.
  - Animations: "pop" is the default energetic entry; "bounce" for fun/excited moments; "spin" rarely, for a reveal; "zoom"/"fade" for softer moments; "slide-left"/"slide-up" when something arrives or rises. Exits: mostly "fade" or "pop"; use "none" only when a cut immediately follows.
  - emphasis "wiggle" for funny/playful lines, "pulse" for important numbers/money; otherwise "none".

"sfx": [{"sound_id": <catalog.sound_effects>, "start", "volume": 0.4-0.9, "reason": "<few words>"}]
  Pair sounds with visual moments: a light click/pop ("ui-click-1", "ui-tick-1", "bell-hit") on many sticker entries; "ui-switch-1"/"ui-switch-2"/"ui-open-1" whooshes on wipe/slide/zoom transitions; "coins-1"/"coins-2" on money; "soft-thud" on a punchline or zoom hit; "wrong-a"/"wrong-b"/"ui-error-1" on mistakes; "correct-a"/"level-up-a"/"you-win-a"/"congratulations-a" on wins; "laugh" on jokes; "gasp" on shocks; "clap" on achievements; "ui-glitch-1" with glitch transitions. Keep sound effects at least 0.4 s apart and keep the volume below the voice (0.5-0.8 typical).

"zooms": [{"start", "end", "scale": 1.1-1.3}]
  Punch-in on emphatic statements, punchlines, reveals and key numbers; 0.6-2.0 s long; never two in a row.

"effects": [{"effect": <catalog.effects>, "start", "duration": 0.3-0.8, "intensity": 0.4-0.8}]
  Seasoning only: the 1-2 biggest moments of the video (a shock, a reveal, a big punchline). "shake" for impact, "glitch"/"chromatic" for a twist, "glow"/"shape-flash" for a highlight, "vignette" for drama. Use none if nothing deserves one.

"caption_emphasis": [{"word": "<exact word from the captions>", "time": <its start_time>}]
  Punch words to highlight in the captions: key numbers, money, brand names, strong emotions. At most about one per caption chunk.

Hit the density targets you are given, but quality beats quantity: skip a slot rather than force something irrelevant.
"""


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
        raise RuntimeError("SARVAM_API_KEY is not set. Add it to backend/.env and restart the backend.")
    data = {
        "model": _stt_model(),
        "mode": _stt_mode(),
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
) -> dict:
    """Transcribe audio using Sarvam Saaras v4 with mode="translit" (Romanized Indic).

    ``audio_bytes`` should be the canonical 16 kHz mono WAV from audio_utils.
    Audio longer than ~25 s is split and the word timestamps are re-offset.

    Returns ``{"transcript": str, "words": [...], "language_code": str|None}``.
    """
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
    captions: Optional[list[dict]] = None,
) -> str:
    import catalog
    from plan_builder import density_targets

    payload = {
        "language_code": language_code,
        "duration": duration,
        "transcript": transcript,
        "captions": [
            {"id": c.get("id"), "start": c.get("start"), "end": c.get("end"), "text": c.get("text")}
            for c in (captions or [])
        ],
        "words": [
            {"w": w.get("word"), "s": w.get("start_time"), "e": w.get("end_time")} for w in words
        ],
        "silence_cuts": [{"start": c.get("start"), "end": c.get("end")} for c in silence_cuts],
        "targets": density_targets(duration or (words[-1]["end_time"] if words else 0.0)),
        "catalog": catalog.prompt_catalog(),
    }
    return json.dumps(payload, ensure_ascii=False)


def validate_director_output(obj: dict) -> dict:
    """Pydantic shape check (AGENTS.md Rule 6). Accepts the two-document shape, or
    a legacy flat plan which is wrapped as {"edit_plan": ...}. Raises ValueError."""
    from pydantic import ValidationError
    from schemas import DirectorResponse

    if not isinstance(obj, dict):
        raise ValueError("Director output is not a JSON object")
    if "edit_plan" not in obj:
        if not any(k in obj for k in ("cuts", "stickers", "sfx", "zooms", "transitions", "effects")):
            raise ValueError("Director output has neither 'edit_plan' nor any plan keys")
        obj = {"sticker_requests": obj.pop("sticker_requests", []), "edit_plan": obj}
    try:
        return DirectorResponse.model_validate(obj).model_dump()
    except ValidationError as exc:
        raise ValueError(f"Director output failed schema validation: {exc.errors(include_url=False)[:3]}") from exc


def direct_video_edit(
    transcript: str,
    words: list[dict],
    silence_cuts: list[dict],
    language_code: str = "hi-IN",
    duration: Optional[float] = None,
    captions: Optional[list[dict]] = None,
) -> dict:
    """Ask the director LLM for both JSON documents in one call.

    Returns {"sticker_requests": [...], "edit_plan": {...}, "director": <provider>,
    "warnings": [...]}. The caller resolves sticker_requests with the scraper and
    passes everything through plan_builder.build_edit_plan() before validating
    against schemas.EditPlan.

    Raises RuntimeError only if Sarvam AND the configured fallback both fail.
    """
    messages = [
        {"role": "system", "content": DIRECTOR_SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_message(
            transcript, words, silence_cuts, language_code, duration, captions)},
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
            plan = validate_director_output(fn(messages))
            plan["director"] = name
            plan["warnings"] = warnings
            return plan
        except Exception as exc:  # timeout, HTTP error, bad JSON, wrong shape...
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
        raise RuntimeError("SARVAM_API_KEY is not set. Add it to backend/.env and restart the backend.")
    payload = {
        "model": _llm_model(),
        "response_format": {"type": "json_object"},
        "temperature": 0.4,
        "messages": messages,
    }
    if _max_tokens():
        payload["max_tokens"] = _max_tokens()
    if _reasoning_effort():
        payload["reasoning_effort"] = _reasoning_effort()
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
