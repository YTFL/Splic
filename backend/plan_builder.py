"""
plan_builder.py — Turns raw director output + STT words + acoustic silences
into a clean, internally consistent EditPlan dict.

LLM output is treated as *suggestions*. This module guarantees:
  * all timestamps are float seconds on the ORIGINAL source clock, clamped to [0, duration]
  * cuts never remove real speech (only silence or filler words), are merged and sorted
  * every caption chunk has 1-4 words (normally 2-4), never straddles a cut,
    and its per-word timings come straight from STT
  * stickers / sfx / zooms / effects never start inside a removed region
  * transitions, sticker animations, sfx and effects only use ids the editor
    actually supports (catalog.py); everything else is dropped with a warning
  * sticker placements only survive if their sticker request resolved to a PNG
  * density stays "mildly aggressive": capped per second of video, never stacked
If the director failed entirely, `heuristic_director()` supplies a basic
director response so the creator still gets a useful first cut.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

import catalog

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

MAX_WORDS_PER_CAPTION = 4
MAX_CAPTION_SPAN = 1.8          # seconds
CAPTION_GAP_BREAK = 0.6         # a pause longer than this starts a new chunk
WORD_GAP_CUT = 0.7              # gaps between words longer than this are dead air
SPEECH_PAD = 0.06               # keep this much air around every spoken word
MIN_CUT = 0.3                   # drop cut fragments shorter than this
MAX_STICKER_REQUESTS = 30
MAX_CONCURRENT_STICKERS = 2
CAPTION_BAND = (0.62, 0.9)      # captions sit at y=75%; stickers stay out of this band

# Spots that keep stickers off the speaker's face and out of the caption band.
STICKER_SLOTS = [
    {"x": 0.78, "y": 0.2},
    {"x": 0.22, "y": 0.2},
    {"x": 0.8, "y": 0.45},
    {"x": 0.2, "y": 0.45},
    {"x": 0.5, "y": 0.14},
]

FILLER_WORDS = {
    "uh", "uhh", "um", "umm", "uhm", "hmm", "hm", "er", "erm", "ah", "aah",
    "matlab", "arre", "arey", "are", "basically", "actually", "like", "toh",
    "na", "haan", "achha", "acha", "accha", "yaani", "woh", "wo", "bas", "so",
    "you know", "i mean",
}

# Legacy logical names kept for old callers; real ids live in catalog.SFX_ALIASES.
SFX_LIBRARY: Dict[str, str] = {
    name: catalog.sfx_url(sid) for name, sid in {
        "vine_boom": "soft-thud", "cash": "coins-1", "ding": "bell-hit",
        "record_scratch": "ui-glitch-1", "laugh": "laugh", "gasp": "gasp", "wrong": "wrong-a",
        "correct": "correct-a", "clap": "clap", "whoosh": "ui-switch-1", "level_up": "level-up-a",
    }.items()
}


def density_caps(duration: float) -> Dict[str, int]:
    """Upper bounds for a 'mildly aggressive' edit, scaled by video length."""
    d = max(0.0, float(duration or 0.0))
    return {
        "stickers": min(25, max(3, math.ceil(d / 3.0))),
        "sfx": min(40, max(4, math.ceil(d / 2.0))),
        "zooms": min(12, max(2, math.ceil(d / 6.0))),
        "effects": min(4, max(1, math.ceil(d / 15.0))),
    }


def density_targets(duration: float) -> Dict[str, str]:
    """Soft ranges given to the director (below the hard caps above)."""
    d = max(1.0, float(duration or 0.0))
    rng = lambda lo, hi: f"{max(1, round(d / hi))}-{max(1, round(d / lo))}"  # noqa: E731
    return {
        "stickers": rng(3.0, 5.0),
        "sfx": rng(2.5, 4.0),
        "zooms": rng(6.0, 9.0),
        "effects": f"0-{density_caps(d)['effects']}",
        "transitions": "on roughly 60-80% of interior cuts",
    }

# Heuristic entity dictionary (used only when the director LLM is unavailable)
HEURISTIC_ENTITIES = {
    "zomato": "Zomato", "swiggy": "Swiggy", "zepto": "Zepto", "blinkit": "Blinkit",
    "flipkart": "Flipkart", "amazon": "Amazon", "myntra": "Myntra", "paytm": "Paytm",
    "phonepe": "PhonePe", "gpay": "Google Pay", "upi": "UPI", "jio": "Jio", "ola": "Ola",
    "uber": "Uber", "irctc": "IRCTC", "biryani": "Biryani", "chai": "Chai",
    "samosa": "Samosa", "dosa": "Dosa", "idli": "Idli", "vada": "Vada Pav",
    "maggi": "Maggi", "paneer": "Paneer", "golgappa": "Golgappa", "panipuri": "Pani Puri",
    "auto": "Auto Rickshaw", "rickshaw": "Auto Rickshaw", "metro": "Metro",
    "cricket": "Cricket", "ipl": "IPL", "bollywood": "Bollywood", "diwali": "Diwali",
    "holi": "Holi", "mumbai": "Mumbai", "delhi": "Delhi", "bangalore": "Bangalore",
    "bengaluru": "Bangalore",
    # Additional common Indic entities
    "rasgulla": "Rasgulla", "jalebi": "Jalebi", "khandvi": "Khandvi", "dhokla": "Dhokla",
    "gulab jamun": "Gulab Jamun", "rasmalai": "Rasmalai", "sweet": "Mithai",
    "street food": "Street Food", "chaat": "Chaat", "pav bhaji": "Pav Bhaji",
    "dabeli": "Dabeli", "bhel puri": "Bhel Puri", "sev puri": "Sev Puri",
    "pani puri": "Pani Puri", "phool gobi": "Phool Gobi",
}
HEURISTIC_SFX_TRIGGERS = {
    "cash": {"paisa", "paise", "rupaye", "rupees", "rupee", "upi", "payment", "salary", "cash", "paytm", "lakh", "crore"},
    "ding": {"mast", "ekdum", "perfect", "badhiya", "zabardast", "wow", "saala", "accha"},
    "vine_boom": {"boom", "scene", "seedha", "bhai", "shock", "pagal", "bhayanak"},
    "laugh": {"haha", "hahaha", "lol", "rofl", "funny", "comedy", "happy"},
    "gasp": {"wow", "oh no", "damn", "shit", "oh my", "my god"},
    "wrong": {"galti", "gayab", "sahi", "galat", "sorry", "mastani"},
}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _f(value: Any, default: Optional[float] = None) -> Optional[float]:
    """Parse a float second value; accepts numbers, '1.25', '1.25s', 'mm:ss.xx'."""
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip().lower().rstrip("s")
        try:
            if ":" in s:
                total = 0.0
                for part in s.split(":"):
                    total = total * 60 + float(part)
                return total
            return float(s)
        except ValueError:
            return default
    return default


def _r(x: float) -> float:
    return round(float(x), 3)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def slugify(keyword: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", keyword.lower()).strip("_")
    return slug or "sticker"


def _norm_token(word: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", word.lower())


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _merge_intervals(intervals: Iterable[Tuple[float, float, str]], join_gap: float = 0.0) -> List[Tuple[float, float, str]]:
    items = sorted((s, e, r) for s, e, r in intervals if e > s)
    merged: List[Tuple[float, float, str]] = []
    for s, e, r in items:
        if merged and s <= merged[-1][1] + join_gap:
            ps, pe, pr = merged[-1]
            reason = pr if r == pr or r in pr.split("+") else f"{pr}+{r}"
            merged[-1] = (ps, max(pe, e), reason)
        else:
            merged.append((s, e, r))
    return merged


def _subtract(interval: Tuple[float, float], blockers: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    pieces = [interval]
    for bs, be in blockers:
        nxt = []
        for ps, pe in pieces:
            if be <= ps or bs >= pe:
                nxt.append((ps, pe))
                continue
            if bs > ps:
                nxt.append((ps, bs))
            if be < pe:
                nxt.append((be, pe))
        pieces = nxt
    return pieces


def _inside_cut(t: float, cuts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for c in cuts:
        if c["start"] <= t < c["end"]:
            return c
    return None


def _push_out_of_cuts(t: float, cuts: List[Dict[str, Any]]) -> float:
    c = _inside_cut(t, cuts)
    return c["end"] if c else t


# ---------------------------------------------------------------------------
# Words
# ---------------------------------------------------------------------------

def normalize_words(raw_words: Any) -> List[Dict[str, Any]]:
    """Accept [{word,start_time,end_time}] or [{word,start,end}] and sanitize."""
    out = []
    for w in _as_list(raw_words):
        if not isinstance(w, dict):
            continue
        text = str(w.get("word") or w.get("text") or "").strip()
        start = _f(w.get("start_time", w.get("start")))
        end = _f(w.get("end_time", w.get("end")))
        if not text or start is None or end is None:
            continue
        if end < start:
            start, end = end, start
        if end == start:
            end = start + 0.05
        out.append({"word": text, "start_time": _r(max(0.0, start)), "end_time": _r(max(0.0, end))})
    out.sort(key=lambda w: (w["start_time"], w["end_time"]))
    return out


_FILLER_TOKENS = {_norm_token(f) for f in FILLER_WORDS}


def _is_filler(word: str) -> bool:
    return _norm_token(word) in _FILLER_TOKENS


def _filler_keys(words: List[Dict[str, Any]]) -> set:
    """Keys (start_time, word) of filler words, including hesitations STT spells
    out letter by letter ("U M M," -> "umm")."""
    keys = {(w["start_time"], w["word"]) for w in words if _is_filler(w["word"])}
    i = 0
    while i < len(words):
        j = i
        while j < len(words) and len(_norm_token(words[j]["word"])) == 1:
            j += 1
        if j - i >= 2 and "".join(_norm_token(w["word"]) for w in words[i:j]) in _FILLER_TOKENS:
            keys.update((w["start_time"], w["word"]) for w in words[i:j])
        i = max(j, i + 1)
    return keys


SILENCE_EDGE = 0.05             # keep this much of a silence next to each word after snapping


def refine_words_with_silences(words: List[Dict[str, Any]], silence_cuts: Any) -> List[Dict[str, Any]]:
    """Snap STT word boundaries out of acoustically silent intervals.

    Saaras returns phrase-level timestamps that we split by character length, so
    word timings tile the audio with no gaps and swallow real pauses. The local
    silence detector measures audio energy, so it is ground truth for "nobody is
    speaking": a word overlapping a silence is clipped to the side of the silence
    its centre lies on. Idempotent; words never reorder or vanish.
    """
    silences = []
    for c in _as_list(silence_cuts):
        if isinstance(c, dict):
            s, e = _f(c.get("start")), _f(c.get("end"))
            if s is not None and e is not None and e - s > 2 * SILENCE_EDGE + 0.1:
                silences.append((s + SILENCE_EDGE, e - SILENCE_EDGE))
    if not silences or not words:
        return words
    out = [dict(w) for w in words]
    for s, e in sorted(silences):
        mid = (s + e) / 2
        for i, w in enumerate(out):
            if w["end_time"] <= s or w["start_time"] >= e:
                continue
            if w["start_time"] >= s and w["end_time"] <= e:
                continue  # STT heard a whole word here: trust it over the energy detector
            if (w["start_time"] + w["end_time"]) / 2 < mid:
                # Belongs before the pause: end at its start edge.
                prev_end = out[i - 1]["end_time"] if i else 0.0
                w["end_time"] = _r(s)
                w["start_time"] = _r(max(prev_end, min(w["start_time"], s - 0.08)))
            else:
                # Belongs after the pause: start at its end edge.
                w["start_time"] = _r(e)
                w["end_time"] = _r(max(w["end_time"], e + 0.08))
    # Keep the sequence monotonic (later words only ever move forward).
    for a, b in zip(out, out[1:]):
        if b["start_time"] < a["end_time"]:
            b["start_time"] = a["end_time"]
            b["end_time"] = _r(max(b["end_time"], b["start_time"] + 0.05))
    for w in out:
        if w["end_time"] <= w["start_time"]:
            w["end_time"] = _r(w["start_time"] + 0.02)
    return out


# ---------------------------------------------------------------------------
# Cuts
# ---------------------------------------------------------------------------

def build_cuts(
    llm_cuts: Any,
    silence_cuts: Any,
    words: List[Dict[str, Any]],
    duration: float,
    warnings: List[str],
) -> List[Dict[str, Any]]:
    candidates: List[Tuple[float, float, str]] = []
    fillers = _filler_keys(words)

    # 1) Acoustic dead air + word-gap dead air (never overlaps padded speech)
    speech = [(max(0.0, w["start_time"] - SPEECH_PAD), w["end_time"] + SPEECH_PAD) for w in words]
    dead_air: List[Tuple[float, float]] = []
    for c in _as_list(silence_cuts):
        s, e = _f(c.get("start")), _f(c.get("end"))
        if s is not None and e is not None and e > s:
            dead_air.append((s, e))
    if words:
        lead = words[0]["start_time"]
        if lead > WORD_GAP_CUT:
            dead_air.append((0.0, lead - 0.15))
        for a, b in zip(words, words[1:]):
            if b["start_time"] - a["end_time"] > WORD_GAP_CUT:
                dead_air.append((a["end_time"] + 0.1, b["start_time"] - 0.1))
        tail = duration - words[-1]["end_time"]
        if tail > WORD_GAP_CUT:
            dead_air.append((words[-1]["end_time"] + 0.2, duration))
    for s, e in dead_air:
        for ps, pe in _subtract((_clamp(s, 0, duration), _clamp(e, 0, duration)), speech):
            if pe - ps >= MIN_CUT:
                candidates.append((ps, pe, "dead_air"))

    # 2) Director-proposed cuts: only allowed to remove silence or filler words
    dropped = 0
    for c in _as_list(llm_cuts):
        if not isinstance(c, dict):
            continue
        s, e = _f(c.get("start")), _f(c.get("end"))
        if s is None or e is None:
            continue
        s, e = _clamp(min(s, e), 0, duration), _clamp(max(s, e), 0, duration)
        if e - s < MIN_CUT * 0.5:
            continue
        reason = str(c.get("reason") or "filler_word").strip() or "filler_word"
        # Every director cut is trimmed below to filler words + silence only (padded
        # non-filler speech is subtracted), so it can never remove a real word.
        if "dead_air" not in reason:
            if any(
                (w["start_time"], w["word"]) not in fillers
                and min(e, w["end_time"]) - max(s, w["start_time"]) > 0.5 * (w["end_time"] - w["start_time"])
                for w in words
            ):
                dropped += 1  # counted as "trimmed", not discarded
            # Grow the cut to swallow filler words it mostly covers or touches
            # (e.g. the leading "U" of a letter-spelled "U M M").
            grown = True
            while grown:
                grown = False
                for w in words:
                    if (w["start_time"], w["word"]) not in fillers:
                        continue
                    covered = min(e, w["end_time"]) - max(s, w["start_time"]) > 0.5 * (w["end_time"] - w["start_time"])
                    touching = w["end_time"] >= s - 0.15 and w["start_time"] <= e + 0.15
                    if (covered or touching) and (w["start_time"] < s or w["end_time"] > e):
                        s, e = min(s, w["start_time"]), max(e, w["end_time"])
                        grown = True
        # Snap filler cuts outward from partially-covered speech words
        for ps, pe in _subtract((s, e), [
            (max(0.0, w["start_time"] - SPEECH_PAD), w["end_time"] + SPEECH_PAD)
            for w in words if (w["start_time"], w["word"]) not in fillers
        ]):
            if pe - ps >= MIN_CUT * 0.5:
                candidates.append((ps, pe, reason))
    if dropped:
        warnings.append(f"Trimmed {dropped} director cut(s) back to filler words/silence; they overlapped spoken (non-filler) words")

    merged = _merge_intervals(candidates, join_gap=0.05)
    cuts = [
        {"start": _r(s), "end": _r(e), "duration": _r(e - s), "reason": r}
        for s, e, r in merged
        if e - s >= MIN_CUT * 0.5
    ]
    if duration > 0 and sum(c["duration"] for c in cuts) > 0.9 * duration:
        warnings.append("Cuts would remove >90% of the video; keeping only dead-air cuts longer than 1s")
        cuts = [c for c in cuts if c["duration"] > 1.0 and c["reason"] == "dead_air"]
    return cuts


def _transition_id(raw: Any) -> Optional[str]:
    tid = str(raw or "").strip().lower().replace("_", "-")
    if tid in catalog.TRANSITION_IDS:
        return tid
    legacy = catalog.LEGACY_TRANSITIONS.get(str(raw or "").strip().lower())
    return legacy or None


def build_transitions(
    cuts: List[Dict[str, Any]],
    llm_transitions: Any,
    duration: float,
    warnings: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Attach director transitions to interior cut seams.

    The director chooses which seams get a transition (not forced on every cut).
    Only when it sent no `transitions` key at all do we fall back to a default
    on every other interior cut.
    """
    interior = [
        (i, c) for i, c in enumerate(cuts)
        # A cut at the very start/end of the video has no clip boundary to blend.
        if c["start"] > 0.01 and c["end"] < duration - 0.01
    ]
    if llm_transitions is None:
        defaults = ["fade", "zoom"]
        return [
            {"at": c["end"], "cut_index": i, "transition_id": defaults[n % 2], "duration": 0.3}
            for n, (i, c) in enumerate(interior) if n % 2 == 0
        ]

    out: List[Dict[str, Any]] = []
    used = set()
    bad = 0
    for t in _as_list(llm_transitions):
        if not isinstance(t, dict):
            continue
        tid = _transition_id(t.get("transition_id") or t.get("transitionId") or t.get("type") or t.get("id"))
        at = _f(t.get("at"))
        if not tid or at is None:
            bad += 1
            continue
        # Snap to the nearest interior seam (the director saw silence candidates,
        # final cuts can differ slightly).
        best = None
        for i, c in interior:
            dist = min(abs(at - c["end"]), abs(at - c["start"]))
            if dist <= 0.6 and i not in used and (best is None or dist < best[0]):
                best = (dist, i, c)
        if best is None:
            bad += 1
            continue
        _, i, c = best
        used.add(i)
        out.append({
            "at": c["end"], "cut_index": i, "transition_id": tid,
            "duration": _r(_clamp(_f(t.get("duration"), 0.3) or 0.3, 0.1, 1.0)),
        })
    if bad and warnings is not None:
        warnings.append(f"Dropped {bad} transition(s) with an unknown id or no matching cut seam")
    out.sort(key=lambda x: x["cut_index"])
    return out


# ---------------------------------------------------------------------------
# Captions
# ---------------------------------------------------------------------------

def _cut_between(a: Dict[str, Any], b: Dict[str, Any], cuts: List[Dict[str, Any]]) -> bool:
    return any(c["start"] < b["start_time"] and c["end"] > a["end_time"] for c in cuts)


def _chunk(words: List[Dict[str, Any]], idx: int, color: str = "#FFD600", position: Optional[dict] = None) -> Dict[str, Any]:
    return {
        "id": f"cap_{idx}",
        "start": words[0]["start_time"],
        "end": words[-1]["end_time"],
        "text": " ".join(w["word"] for w in words),
        "words": [dict(w) for w in words],
        "highlight_color": color,
        "position": position or {"x": 50, "y": 75},
    }


def _caption_style(llm_captions: Any) -> Tuple[str, dict]:
    color, position = "#FFD600", {"x": 50, "y": 75}
    for c in _as_list(llm_captions):
        if isinstance(c, dict):
            hc = c.get("highlight_color")
            if isinstance(hc, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", hc):
                color = hc
            pos = c.get("position")
            if isinstance(pos, dict):
                x, y = _f(pos.get("x")), _f(pos.get("y"))
                if x is not None and y is not None and 0 <= x <= 100 and 0 <= y <= 100:
                    position = {"x": x, "y": y}
            break
    return color, position


def build_captions(words: List[Dict[str, Any]], cuts: List[Dict[str, Any]], llm_captions: Any) -> List[Dict[str, Any]]:
    # Words (mostly) removed by a cut, and filler words touched by a filler cut,
    # do not get captions.
    fillers = _filler_keys(words)
    kept = [w for w in words if not any(
        min(c["end"], w["end_time"]) - max(c["start"], w["start_time"]) >= 0.5 * (w["end_time"] - w["start_time"])
        or ((w["start_time"], w["word"]) in fillers and "filler" in c.get("reason", "")
            and min(c["end"], w["end_time"]) > max(c["start"], w["start_time"]))
        for c in cuts
    )]
    if not kept:
        return []
    color, position = _caption_style(llm_captions)

    # Try to honour the director's chunking if it is valid against the STT words.
    llm_groups = []
    for c in _as_list(llm_captions):
        if isinstance(c, dict):
            text = c.get("text") or " ".join(
                str(w.get("word", "")) for w in _as_list(c.get("words")) if isinstance(w, dict)
            )
            tokens = [t for t in str(text).split() if _norm_token(t)]
            llm_groups.append(tokens)
    flat = [_norm_token(t) for g in llm_groups for t in g]
    if (
        llm_groups
        and all(1 <= len(g) <= MAX_WORDS_PER_CAPTION for g in llm_groups)
        and flat == [_norm_token(w["word"]) for w in kept if _norm_token(w["word"])]
    ):
        out, i = [], 0
        for g in llm_groups:
            group = []
            while len(group) < len(g) and i < len(kept):
                if _norm_token(kept[i]["word"]):
                    group.append(kept[i])
                i += 1
            # Director chunks must also respect cuts / span limits
            if group and not any(_cut_between(a, b, cuts) for a, b in zip(group, group[1:])) \
                    and group[-1]["end_time"] - group[0]["start_time"] <= MAX_CAPTION_SPAN + 0.6:
                out.append(group)
            else:
                out = None
                break
        if out:
            return [_chunk(g, n + 1, color, position) for n, g in enumerate(out)]

    # Deterministic 2-4 word chunking
    groups: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    for w in kept:
        if current:
            prev = current[-1]
            hard_break = (
                w["start_time"] - prev["end_time"] > CAPTION_GAP_BREAK
                or _cut_between(prev, w, cuts)
            )
            soft_break = (
                len(current) >= MAX_WORDS_PER_CAPTION
                or (len(current) >= 2 and w["end_time"] - current[0]["start_time"] > MAX_CAPTION_SPAN)
                or (len(current) >= 2 and re.search(r"[.!?,;:]$", prev["word"]))
            )
            if hard_break or soft_break:
                groups.append(current)
                current = []
        current.append(w)
    if current:
        groups.append(current)

    # Fold orphan single-word chunks into a neighbour when no hard break separates them.
    # If the neighbour is already full (4 words), rebalance 4+1 into 3+2 instead.
    fixed: List[List[Dict[str, Any]]] = []
    for g in groups:
        joinable = (
            len(g) == 1 and fixed
            and g[0]["start_time"] - fixed[-1][-1]["end_time"] <= CAPTION_GAP_BREAK
            and not _cut_between(fixed[-1][-1], g[0], cuts)
        )
        if joinable and len(fixed[-1]) < MAX_WORDS_PER_CAPTION:
            fixed[-1].append(g[0])
        elif joinable and len(fixed[-1]) >= 3:
            fixed.append([fixed[-1].pop(), g[0]])
        else:
            fixed.append(g)
    return [_chunk(g, n + 1, color, position) for n, g in enumerate(fixed)]


# ---------------------------------------------------------------------------
# Director output -> (sticker_requests, edit_plan)
# ---------------------------------------------------------------------------

def split_director_output(raw: Optional[Dict[str, Any]]) -> Tuple[List[Any], Dict[str, Any]]:
    """Return (sticker_requests, edit_plan) from the director response.

    Accepts the two-document shape {"sticker_requests": [...], "edit_plan": {...}}
    and the legacy flat shape {"cuts": [...], "stickers": [{"keyword": ...}], ...}.
    """
    raw = raw if isinstance(raw, dict) else {}
    edit = raw.get("edit_plan")
    if not isinstance(edit, dict):
        edit = {k: v for k, v in raw.items() if k != "sticker_requests"}
    return _as_list(raw.get("sticker_requests")), edit


def normalize_sticker_requests(
    raw_requests: Any,
    placements: Any,
    library: Optional[Dict[str, Dict[str, str]]] = None,
) -> List[Dict[str, Any]]:
    """Sanitise JSON 1. Legacy placements that carry a `keyword` but no `ref`
    get a synthetic scrape request (and the placement is given that ref)."""
    library = catalog.sticker_library() if library is None else library
    out: List[Dict[str, Any]] = []
    seen = set()

    def add(ref: str, concept: str, source: str, library_id: Optional[str], query: Optional[str]) -> None:
        if not ref or ref in seen or len(out) >= MAX_STICKER_REQUESTS:
            return
        concept = concept.strip()[:80]
        if source == "library" and library_id not in library:
            # Unknown library id: let the scraper find it instead.
            source, library_id = "scrape", None
        if source == "scrape":
            query = (query or concept).strip()[:120]
            if not query:
                return
        seen.add(ref)
        out.append({
            "ref": ref, "concept": concept or (library_id or query or ref),
            "source": source,
            "library_id": library_id if source == "library" else None,
            "query": query if source == "scrape" else None,
        })

    for r in raw_requests if isinstance(raw_requests, list) else []:
        if not isinstance(r, dict):
            continue
        ref = str(r.get("ref") or r.get("id") or "").strip()
        concept = str(r.get("concept") or r.get("keyword") or r.get("query") or r.get("library_id") or "")
        source = str(r.get("source") or "").strip().lower()
        library_id = r.get("library_id")
        library_id = str(library_id).strip() if library_id else None
        if source not in ("library", "scrape"):
            source = "library" if library_id else "scrape"
        query = r.get("query")
        add(ref, concept, source, library_id, str(query) if query else None)

    for p in placements if isinstance(placements, list) else []:
        if isinstance(p, dict) and not p.get("ref"):
            keyword = str(p.get("keyword") or p.get("entity") or p.get("name") or "").strip()
            if keyword:
                ref = f"k_{slugify(keyword)}"
                p["ref"] = ref
                add(ref, keyword, "scrape", None, keyword)
    return out


# ---------------------------------------------------------------------------
# Sticker animations
# ---------------------------------------------------------------------------

_IN_DEFAULT = {"fade": 0.35, "zoom": 0.35, "slide-left": 0.4, "slide-up": 0.4,
               "pop": 0.35, "bounce": 0.6, "spin": 0.5}
_OUT_DEFAULT = {"fade": 0.3, "zoom": 0.3, "slide-left": 0.35, "slide-up": 0.35, "pop": 0.3}


def _anim_id(raw: Any, allowed: List[str]) -> str:
    v = str(raw or "none").strip().lower().replace("_", "-").replace(" ", "-")
    v = {"pop-in": "pop", "pop-out": "pop", "fade-in": "fade", "fade-out": "fade", "zoom-in": "zoom",
         "zoom-out": "zoom", "slide-in": "slide-up", "slide-right": "slide-left", "scale": "zoom",
         "bounce-in": "bounce", "spin-in": "spin"}.get(v, v)
    return v if v in allowed else "none"


def compile_sticker_animation(
    anim_in: str,
    anim_out: str,
    emphasis: str,
    duration: float,
    scale: float,
    rotation: float,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Turn director animation ids into editor data.

    Native ids (fade / zoom / slide-left / slide-up) map onto the editor's own
    segment.animation {in, out}. Ids the editor lacks (pop, bounce, spin, wiggle,
    pulse) are compiled into transform keyframes, local to the sticker, whose
    values are absolute (base scale/rotation baked in) and that always return to
    the base transform so the sticker rests normally between phases.
    """
    b, r = scale, rotation
    budget = max(0.2, duration * 0.4)
    animation = {"in": {"id": "none", "duration": 0.4}, "out": {"id": "none", "duration": 0.4}}
    frames: Dict[float, Dict[str, float]] = {}

    def kf(t: float, **vals: float) -> None:
        t = _r(_clamp(t, 0.0, duration))
        frames.setdefault(t, {}).update({k: _r(v) for k, v in vals.items()})

    in_d = min(_IN_DEFAULT.get(anim_in, 0.4), budget)
    out_d = min(_OUT_DEFAULT.get(anim_out, 0.3), budget)

    if anim_in in catalog.NATIVE_ANIMATIONS:
        animation["in"] = {"id": anim_in, "duration": _r(max(0.1, in_d))}
    elif anim_in == "pop":
        kf(0, scale=0.2 * b, opacity=0.0)
        kf(0.6 * in_d, scale=1.18 * b, opacity=1.0)
        kf(in_d, scale=b)
    elif anim_in == "bounce":
        kf(0, scale=0.3 * b, opacity=0.0)
        kf(0.25 * in_d, scale=1.15 * b, opacity=1.0)
        kf(0.5 * in_d, scale=0.92 * b)
        kf(0.75 * in_d, scale=1.05 * b)
        kf(in_d, scale=b)
    elif anim_in == "spin":
        kf(0, scale=0.3 * b, rotation=r - 180, opacity=0.0)
        kf(in_d, scale=b, rotation=r, opacity=1.0)
    in_end = in_d if anim_in != "none" else 0.0

    out_start = duration - out_d if anim_out != "none" else duration
    if anim_out in catalog.NATIVE_ANIMATIONS:
        animation["out"] = {"id": anim_out, "duration": _r(max(0.1, out_d))}
    elif anim_out == "pop":
        kf(out_start, scale=b, opacity=1.0)
        kf(out_start + 0.35 * out_d, scale=1.12 * b)
        kf(duration, scale=0.2 * b, opacity=0.0)

    hold_start, hold_end = in_end + 0.05, out_start - 0.05
    if emphasis == "wiggle" and hold_end - hold_start >= 0.5:
        for k, delta in enumerate((8, -8, 6, -4, 0)):
            kf(hold_start + k * 0.1, rotation=r + delta)
    elif emphasis == "pulse" and hold_end - hold_start >= 0.5:
        mid = (hold_start + hold_end) / 2
        kf(mid - 0.18, scale=b)
        kf(mid, scale=1.1 * b)
        kf(mid + 0.18, scale=b)

    keyframes = [{"time": t, **vals} for t, vals in sorted(frames.items())]
    return animation, keyframes


# ---------------------------------------------------------------------------
# Stickers, SFX, Zooms, Effects
# ---------------------------------------------------------------------------

def _find_mention(keyword: str, words: List[Dict[str, Any]], near: Optional[float]) -> Optional[float]:
    tokens = [_norm_token(t) for t in re.split(r"[\s\-_]+", keyword) if _norm_token(t)]
    if not tokens:
        return None
    hits = [
        w["start_time"] for w in words
        if (nt := _norm_token(w["word"])) and (nt == tokens[0] or nt.startswith(tokens[0]) or tokens[0].startswith(nt) and len(nt) >= 3)
    ]
    if not hits:
        return None
    if near is None:
        return hits[0]
    return min(hits, key=lambda t: abs(t - near))


def _position(raw: Any) -> Optional[Dict[str, float]]:
    if not isinstance(raw, dict):
        return None
    x, y = _f(raw.get("x")), _f(raw.get("y"))
    if x is None or y is None:
        return None
    if x > 1 or y > 1:  # percent coordinates
        x, y = x / 100.0, y / 100.0
    return {"x": _r(_clamp(x, 0.08, 0.92)), "y": _r(_clamp(y, 0.08, 0.92))}


def _overlaps(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    return a["start"] < b["start"] + b["duration"] and b["start"] < a["start"] + a["duration"]


def build_stickers(
    placements: Any,
    requests: List[Dict[str, Any]],
    sticker_assets: Optional[Dict[str, Dict[str, Any]]],
    words: List[Dict[str, Any]],
    cuts: List[Dict[str, Any]],
    duration: float,
    warnings: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Sanitise sticker placements and attach the resolved asset for each ref."""
    by_ref = {r["ref"]: r for r in requests}
    cap = density_caps(duration)["stickers"]
    out: List[Dict[str, Any]] = []
    unresolved, unknown = set(), 0
    for s in _as_list(placements):
        if not isinstance(s, dict):
            continue
        ref = str(s.get("ref") or "").strip()
        req = by_ref.get(ref)
        if not req:
            unknown += 1
            continue
        if sticker_assets is not None:
            asset = sticker_assets.get(ref) or {}
            if not asset.get("asset_url"):
                unresolved.add(req["concept"])
                continue
            asset_url, source = asset["asset_url"], asset.get("resolution")
        else:  # not resolved yet (unit tests / dry runs)
            lib = catalog.sticker_library().get(req.get("library_id") or "")
            asset_url = lib["asset_url"] if lib else f"/api/stickers/{slugify(req['concept'])}.png"
            source = "library" if lib else "pending"

        start = _f(s.get("start"))
        mention = _find_mention(req["concept"], words, start)
        if mention is not None and (start is None or abs(mention - start) <= 1.5):
            start = mention
        if start is None:
            continue
        start = _push_out_of_cuts(_clamp(start, 0, max(0.0, duration - 0.5)), cuts)
        dur = _clamp(_f(s.get("duration"), 1.8) or 1.8, 0.6, 4.0)
        dur = min(dur, max(0.5, duration - start))

        pos = _position(s.get("position")) or _position({"x": s.get("x"), "y": s.get("y")})
        if pos and CAPTION_BAND[0] < pos["y"] < CAPTION_BAND[1]:
            pos = None  # would sit on the captions
        scale = _r(_clamp(_f(s.get("scale"), 1.0) or 1.0, 0.5, 2.0))
        rotation = _r(_clamp(_f(s.get("rotation"), 0.0) or 0.0, -30, 30))
        raw_in = s.get("animation_in") or s.get("in")
        raw_out = s.get("animation_out") or s.get("out")
        anim_in = _anim_id(raw_in, catalog.ANIMATION_IN_IDS)
        anim_out = _anim_id(raw_out, catalog.ANIMATION_OUT_IDS)
        # Missing / unknown ids get the house style; only an explicit "none" means none.
        if anim_in == "none" and str(raw_in or "").strip().lower() != "none":
            anim_in = "pop"
        if anim_out == "none" and str(raw_out or "").strip().lower() != "none":
            anim_out = "fade"
        emphasis = _anim_id(s.get("emphasis"), catalog.EMPHASIS_IDS)

        out.append({
            "keyword": req["concept"],
            "slug": slugify(req["concept"]),
            "asset_url": str(asset_url),
            "source": source,
            "ref": ref,
            "start": _r(start),
            "duration": _r(dur),
            "position": pos,
            "scale": scale,
            "rotation": rotation,
            "animation_in": anim_in,
            "animation_out": anim_out,
            "emphasis": emphasis,
        })

    out.sort(key=lambda x: x["start"])
    kept: List[Dict[str, Any]] = []
    for cur in out:
        live = [p for p in kept if _overlaps(p, cur)]
        if len(live) >= MAX_CONCURRENT_STICKERS:
            continue
        if any(p["ref"] == cur["ref"] and cur["start"] - p["start"] < 4.0 for p in kept):
            continue  # same sticker re-popping within 4 s looks like a glitch
        used = {(p["position"]["x"], p["position"]["y"]) for p in live if p["position"]}
        if cur["position"] is None or (cur["position"]["x"], cur["position"]["y"]) in used \
                or any(abs(p["position"]["x"] - cur["position"]["x"]) < 0.2
                       and abs(p["position"]["y"] - cur["position"]["y"]) < 0.2 for p in live):
            slot = next((sl for sl in STICKER_SLOTS[len(kept) % len(STICKER_SLOTS):] + STICKER_SLOTS
                         if (sl["x"], sl["y"]) not in used), STICKER_SLOTS[0])
            cur["position"] = dict(slot)
        kept.append(cur)
        if len(kept) >= cap:
            break

    for cur in kept:
        cur["animation"], cur["keyframes"] = compile_sticker_animation(
            cur["animation_in"], cur["animation_out"], cur["emphasis"],
            cur["duration"], cur["scale"], cur["rotation"],
        )
    if warnings is not None:
        if unresolved:
            warnings.append("No sticker image available for: " + ", ".join(sorted(unresolved)))
        if unknown:
            warnings.append(f"Dropped {unknown} sticker placement(s) whose ref has no sticker request")
        if len(out) > len(kept):
            warnings.append(f"Thinned {len(out) - len(kept)} sticker placement(s) (overlap / density cap)")
    return kept


def resolve_sfx_asset(raw: Any) -> Tuple[str, str]:
    """Map 'coins-1', 'vine_boom.mp3', '/assets/sfx/cash.mp3', 'boom' ... -> (sound_id, asset_path).
    Raises ValueError for sounds that are not bundled."""
    sid = catalog.resolve_sfx_id(raw)
    if not sid:
        raise ValueError(f"unknown sound {raw!r}")
    return sid, catalog.sfx_url(sid)


def build_sfx(llm_sfx: Any, cuts: List[Dict[str, Any]], duration: float,
              warnings: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    unknown = 0
    for s in _as_list(llm_sfx):
        if not isinstance(s, dict):
            continue
        start = _f(s.get("start"))
        if start is None:
            continue
        start = _push_out_of_cuts(_clamp(start, 0, max(0.0, duration - 0.1)), cuts)
        try:
            sid, asset = resolve_sfx_asset(s.get("sound_id") or s.get("asset") or s.get("name") or s.get("sfx"))
        except ValueError:
            unknown += 1
            continue
        label = s.get("label") or s.get("reason")
        items.append({
            "asset": asset,
            "sound_id": sid,
            "start": _r(start),
            "volume": _r(_clamp(_f(s.get("volume"), 0.8) or 0.8, 0.0, 1.0)),
            "label": str(label)[:60] if label else sid,
        })
    items.sort(key=lambda x: x["start"])
    out: List[Dict[str, Any]] = []
    for it in items:
        if out and it["start"] - out[-1]["start"] < 0.35:
            continue  # never stack two hits on top of each other
        out.append(it)
    out = out[:density_caps(duration)["sfx"]]
    if unknown and warnings is not None:
        warnings.append(f"Dropped {unknown} sound effect(s) not in the bundled library")
    return out


def build_zooms(llm_zooms: Any, cuts: List[Dict[str, Any]], duration: float) -> List[Dict[str, Any]]:
    items = []
    for z in _as_list(llm_zooms):
        if not isinstance(z, dict):
            continue
        s, e = _f(z.get("start")), _f(z.get("end"))
        if s is None:
            continue
        if e is None:
            e = s + 0.8
        s, e = _clamp(min(s, e), 0, duration), _clamp(max(s, e), 0, duration)
        s = _push_out_of_cuts(s, cuts)
        for c in cuts:  # stop the zoom where the next cut begins
            if s < c["start"] < e:
                e = c["start"]
        e = min(e, s + 3.0)
        if e - s < 0.3:
            continue
        scale = _clamp(_f(z.get("scale"), 1.25) or 1.25, 1.05, 1.5)
        items.append((s, e, scale))
    items.sort()
    out: List[Dict[str, Any]] = []
    for s, e, scale in items:
        if out and s < out[-1]["end"] + 0.5:
            out[-1]["end"] = _r(max(out[-1]["end"], e))
            continue
        out.append({"start": _r(s), "end": _r(e), "scale": _r(scale)})
    return out[:density_caps(duration)["zooms"]]


def build_effects(llm_effects: Any, cuts: List[Dict[str, Any]], duration: float,
                  warnings: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    items = []
    unknown = 0
    for fx in _as_list(llm_effects):
        if not isinstance(fx, dict):
            continue
        eid = str(fx.get("effect") or fx.get("id") or fx.get("type") or "").strip().lower().replace("_", "-")
        start = _f(fx.get("start"))
        if eid not in catalog.EFFECT_IDS or start is None:
            unknown += 1
            continue
        start = _push_out_of_cuts(_clamp(start, 0, max(0.0, duration - 0.2)), cuts)
        dur = _clamp(_f(fx.get("duration"), 0.6) or 0.6, 0.2, 1.5)
        dur = min(dur, max(0.1, duration - start))
        items.append({
            "effect": eid, "start": _r(start), "duration": _r(dur),
            "intensity": _r(_clamp(_f(fx.get("intensity"), 0.6) or 0.6, 0.3, 0.9)),
        })
    items.sort(key=lambda x: x["start"])
    out: List[Dict[str, Any]] = []
    for it in items:
        if out and it["start"] - out[-1]["start"] < 2.0:
            continue  # effects are seasoning: keep them well apart
        out.append(it)
    if unknown and warnings is not None:
        warnings.append(f"Dropped {unknown} effect(s) with an unsupported id")
    return out[:density_caps(duration)["effects"]]


def apply_caption_emphasis(captions: List[Dict[str, Any]], emphasis: Any) -> None:
    """Flag punch words: [{"word": "paisa", "time": 4.6}] or [{"caption_id": "cap_3", "word": "paisa"}]."""
    for e in _as_list(emphasis):
        if not isinstance(e, dict):
            continue
        target = _norm_token(str(e.get("word") or ""))
        if not target:
            continue
        t = _f(e.get("time"), _f(e.get("start")))
        cid = e.get("caption_id")
        best = None
        for c in captions:
            if cid and c["id"] != cid:
                continue
            if sum(w.get("emphasis", False) for w in c["words"]) >= 1:
                continue  # one punch word per caption chunk
            for w in c["words"]:
                if _norm_token(w["word"]) != target:
                    continue
                dist = abs(w["start_time"] - t) if t is not None else 0.0
                if (t is None or dist <= 0.75) and (best is None or dist < best[0]):
                    best = (dist, w)
        if best:
            best[1]["emphasis"] = True


# ---------------------------------------------------------------------------
# Heuristic director (offline fallback) — same two-document shape as the LLM
# ---------------------------------------------------------------------------

HEURISTIC_ENTITIES = {
    "zomato": "Zomato", "swiggy": "Swiggy", "zepto": "Zepto", "blinkit": "Blinkit",
    "flipkart": "Flipkart", "amazon": "Amazon", "myntra": "Myntra", "paytm": "Paytm",
    "phonepe": "PhonePe", "gpay": "Google Pay", "upi": "UPI", "jio": "Jio", "ola": "Ola",
    "uber": "Uber", "irctc": "IRCTC", "biryani": "Biryani", "chai": "Chai",
    "samosa": "Samosa", "dosa": "Dosa", "idli": "Idli", "vada": "Vada Pav",
    "maggi": "Maggi", "paneer": "Paneer", "golgappa": "Golgappa", "panipuri": "Pani Puri",
    "rickshaw": "Auto Rickshaw", "metro": "Metro",
    "cricket": "Cricket", "ipl": "IPL", "bollywood": "Bollywood", "diwali": "Diwali",
    "holi": "Holi", "mumbai": "Mumbai", "delhi": "Delhi", "bangalore": "Bangalore",
    "bengaluru": "Bangalore", "jalebi": "Jalebi", "dhokla": "Dhokla", "chaat": "Chaat",
    "phone": "Smartphone", "mobile": "Smartphone", "laptop": "Laptop", "pizza": "Pizza",
    "coffee": "Coffee", "gym": "Dumbbell", "car": "Car", "bike": "Motorbike",
}
# Spoken word -> bundled sticker library id
HEURISTIC_LIBRARY = {
    "paisa": "shop-coins", "paise": "shop-coins", "rupaye": "shop-coins", "rupees": "shop-coins",
    "money": "shop-coins", "cash": "shop-coins", "fire": "trend-flame", "aag": "trend-flame",
    "idea": "shop-idea", "gift": "shop-gift", "love": "react-heart", "pyaar": "react-heart",
    "dil": "react-heart", "rocket": "trend-rocket", "khatra": "react-alert", "danger": "react-alert",
}
HEURISTIC_SFX_TRIGGERS = {
    "coins-1": {"paisa", "paise", "rupaye", "rupees", "rupee", "upi", "payment", "salary", "cash", "paytm", "lakh", "crore"},
    "bell-hit": {"mast", "ekdum", "perfect", "badhiya", "zabardast", "wow"},
    "soft-thud": {"boom", "scene", "seedha", "shock", "pagal", "bhayanak"},
    "laugh": {"haha", "hahaha", "lol", "rofl", "funny", "comedy"},
    "gasp": {"omg", "damn"},
    "wrong-a": {"galti", "galat", "wrong", "fail"},
}


def heuristic_director(words: List[Dict[str, Any]]) -> Dict[str, Any]:
    library = catalog.sticker_library()
    requests, placements, sfx, zooms = [], [], [], []
    refs: Dict[str, str] = {}
    for w in words:
        tok = _norm_token(w["word"])
        concept, lib_id = None, None
        if tok in HEURISTIC_LIBRARY and HEURISTIC_LIBRARY[tok] in library:
            lib_id = HEURISTIC_LIBRARY[tok]
            concept = library[lib_id]["name"]
        else:
            for key, label in HEURISTIC_ENTITIES.items():
                if tok == key or (len(key) >= 4 and tok.startswith(key)):
                    concept = label
                    break
        if concept:
            if concept not in refs:
                refs[concept] = f"s{len(refs) + 1}"
                requests.append({"ref": refs[concept], "concept": concept,
                                 **({"source": "library", "library_id": lib_id} if lib_id
                                    else {"source": "scrape", "query": f"{concept} 3d icon"})})
            placements.append({"ref": refs[concept], "start": w["start_time"], "duration": 1.8,
                               "animation_in": "pop", "animation_out": "fade"})
        for sid, triggers in HEURISTIC_SFX_TRIGGERS.items():
            if tok in triggers:
                sfx.append({"sound_id": sid, "start": w["start_time"], "volume": 0.8, "reason": tok})
                if sid == "soft-thud" and len(zooms) < 3:
                    zooms.append({"start": w["start_time"], "end": w["end_time"] + 0.5, "scale": 1.2})
                break
        if w["word"].endswith("!") and len(zooms) < 3:
            zooms.append({"start": w["start_time"], "end": w["end_time"] + 0.4, "scale": 1.2})
    return {
        "sticker_requests": requests,
        "edit_plan": {"stickers": placements, "sfx": sfx, "zooms": zooms},
    }


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------

def build_edit_plan(
    raw_plan: Optional[Dict[str, Any]],
    *,
    transcript: str = "",
    words: Any = None,
    silence_cuts: Any = None,
    duration: Optional[float] = None,
    language_code: str = "hi-IN",
    project_id: Optional[str] = None,
    director: Optional[str] = None,
    warnings: Optional[List[str]] = None,
    sticker_requests: Optional[List[Dict[str, Any]]] = None,
    sticker_assets: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Merge STT + silences + the director's two JSON documents into one EditPlan dict.

    `sticker_requests` is the already-normalised JSON 1 (normalize_sticker_requests);
    `sticker_assets` maps ref -> {"asset_url", "resolution"} from the sticker resolver.
    """
    raw = dict(raw_plan or {})
    warnings = list(warnings or []) + [w for w in _as_list(raw.get("warnings")) if isinstance(w, str)]
    raw_requests, edit = split_director_output(raw)
    if sticker_requests is None:
        sticker_requests = normalize_sticker_requests(raw_requests, edit.get("stickers"))

    norm_words = normalize_words(words) if words else normalize_words(raw.get("words"))
    norm_words = refine_words_with_silences(norm_words, silence_cuts)
    transcript = (transcript or str(raw.get("transcript") or "")).strip() or " ".join(w["word"] for w in norm_words)

    last_word_end = norm_words[-1]["end_time"] if norm_words else 0.0
    dur = _f(duration) or _f(raw.get("duration")) or 0.0
    dur = _r(max(dur, last_word_end))

    cuts = build_cuts(edit.get("cuts"), silence_cuts, norm_words, dur, warnings)
    captions = build_captions(norm_words, cuts, edit.get("captions"))
    apply_caption_emphasis(captions, edit.get("caption_emphasis"))

    requests_out = []
    for r in sticker_requests:
        asset = (sticker_assets or {}).get(r["ref"]) or {}
        requests_out.append({
            **r,
            "resolved": bool(asset.get("asset_url")),
            "resolution": asset.get("resolution") or ("unresolved" if sticker_assets is not None else None),
            "asset_url": asset.get("asset_url"),
        })

    plan = {
        "project_id": project_id or raw.get("project_id"),
        "transcript": transcript,
        "language_code": str(raw.get("language_code") or language_code or "hi-IN"),
        "duration": dur,
        "words": norm_words,
        "captions": captions,
        "cuts": cuts,
        "transitions": build_transitions(cuts, edit.get("transitions"), dur, warnings),
        "stickers": build_stickers(edit.get("stickers"), sticker_requests, sticker_assets,
                                   norm_words, cuts, dur, warnings),
        "sfx": build_sfx(edit.get("sfx"), cuts, dur, warnings),
        "zooms": build_zooms(edit.get("zooms"), cuts, dur),
        "effects": build_effects(edit.get("effects"), cuts, dur, warnings),
        "sticker_requests": requests_out,
        "director": director or raw.get("director"),
        "warnings": warnings,
    }
    if not plan["language_code"] or plan["language_code"] == "unknown":
        plan["language_code"] = language_code if language_code != "unknown" else "hi-IN"
    return plan
