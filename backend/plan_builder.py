"""
plan_builder.py — Turns raw director output + STT words + acoustic silences
into a clean, internally consistent EditPlan dict.

LLM output is treated as *suggestions*. This module guarantees:
  * all timestamps are float seconds on the ORIGINAL source clock, clamped to [0, duration]
  * cuts never remove real speech (only silence or filler words), are merged and sorted
  * every caption chunk has 1-4 words (normally 2-4), never straddles a cut,
    and its per-word timings come straight from STT
  * stickers / sfx / zooms never start inside a removed region
  * sfx point at real files under /assets/sound-effects/
If the director failed entirely, `heuristic_director()` supplies basic
stickers / sfx / zooms so the creator still gets a useful first cut.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

MAX_WORDS_PER_CAPTION = 4
MAX_CAPTION_SPAN = 1.8          # seconds
CAPTION_GAP_BREAK = 0.6         # a pause longer than this starts a new chunk
WORD_GAP_CUT = 0.7              # gaps between words longer than this are dead air
SPEECH_PAD = 0.06               # keep this much air around every spoken word
MIN_CUT = 0.3                   # drop cut fragments shorter than this
MAX_STICKERS = 8
TRANSITION_TYPES = ["fade_black", "crossfade", "wipe_left", "zoom_in"]

STICKER_SLOTS = [
    {"x": 0.5, "y": 0.3},
    {"x": 0.25, "y": 0.22},
    {"x": 0.75, "y": 0.22},
    {"x": 0.5, "y": 0.45},
]

FILLER_WORDS = {
    "uh", "uhh", "um", "umm", "uhm", "hmm", "hm", "er", "erm", "ah", "aah",
    "matlab", "arre", "arey", "are", "basically", "actually", "like", "toh",
    "na", "haan", "achha", "acha", "accha", "yaani", "woh", "wo", "bas", "so",
    "you know", "i mean",
}

# Logical meme-SFX name -> file bundled in timeline studio/public/assets/sound-effects
SFX_LIBRARY: Dict[str, str] = {
    "vine_boom": "/assets/sound-effects/soft-thud.mp3",
    "cash": "/assets/sound-effects/coins-1.mp3",
    "ding": "/assets/sound-effects/bell-hit.mp3",
    "record_scratch": "/assets/sound-effects/ui-glitch-1.mp3",
    "laugh": "/assets/sound-effects/laugh.mp3",
    "gasp": "/assets/sound-effects/gasp.mp3",
    "wrong": "/assets/sound-effects/wrong-a.mp3",
    "correct": "/assets/sound-effects/correct-a.mp3",
    "clap": "/assets/sound-effects/clap.mp3",
    "whoosh": "/assets/sound-effects/ui-switch-1.mp3",
    "level_up": "/assets/sound-effects/level-up-a.mp3",
}
SFX_ALIASES = {
    "boom": "vine_boom", "vineboom": "vine_boom", "bass_boom": "vine_boom", "bruh": "vine_boom",
    "money": "cash", "cash_register": "cash", "coins": "cash", "kaching": "cash", "cha_ching": "cash",
    "bell": "ding", "success": "ding", "notification": "ding",
    "scratch": "record_scratch", "glitch": "record_scratch",
    "applause": "clap", "swoosh": "whoosh", "swipe": "whoosh",
    "fail": "wrong", "buzzer": "wrong", "win": "level_up",
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
}
HEURISTIC_SFX_TRIGGERS = {
    "cash": {"paisa", "paise", "rupaye", "rupees", "rupee", "upi", "payment", "salary", "cash", "paytm", "lakh", "crore"},
    "ding": {"mast", "ekdum", "perfect", "badhiya", "zabardast", "wow"},
    "vine_boom": {"boom", "scene", "seedha", "bhai", "shock", "pagal"},
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


def _is_filler(word: str) -> bool:
    return _norm_token(word) in {_norm_token(f) for f in FILLER_WORDS}


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
        removes_speech = any(
            not _is_filler(w["word"])
            and min(e, w["end_time"]) - max(s, w["start_time"]) > 0.5 * (w["end_time"] - w["start_time"])
            for w in words
        )
        if removes_speech:
            dropped += 1
            continue
        reason = str(c.get("reason") or "filler_word").strip() or "filler_word"
        # Grow the cut to swallow whole filler words it mostly covers.
        for w in words:
            if _is_filler(w["word"]) and min(e, w["end_time"]) - max(s, w["start_time"]) > 0.5 * (w["end_time"] - w["start_time"]):
                s, e = min(s, w["start_time"]), max(e, w["end_time"])
        # Snap filler cuts outward from partially-covered speech words
        for ps, pe in _subtract((s, e), [
            (max(0.0, w["start_time"] - SPEECH_PAD), w["end_time"] + SPEECH_PAD)
            for w in words if not _is_filler(w["word"])
        ]):
            if pe - ps >= MIN_CUT * 0.5:
                candidates.append((ps, pe, reason))
    if dropped:
        warnings.append(f"Dropped {dropped} director cut(s) that would have removed spoken (non-filler) words")

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


def build_transitions(cuts: List[Dict[str, Any]], llm_transitions: Any, duration: float) -> List[Dict[str, Any]]:
    hints = []
    for t in _as_list(llm_transitions):
        if isinstance(t, dict):
            at = _f(t.get("at"))
            typ = str(t.get("type") or "").strip().lower()
            if at is not None and typ in TRANSITION_TYPES:
                hints.append((at, typ, _f(t.get("duration"), 0.3)))

    out = []
    for i, c in enumerate(cuts):
        # A cut at the very start/end of the video has no clip boundary to blend.
        if c["start"] <= 0.01 or c["end"] >= duration - 0.01:
            continue
        chosen = None
        for at, typ, dur in hints:
            if abs(at - c["end"]) < 0.5 or abs(at - c["start"]) < 0.5:
                chosen = (typ, dur)
                break
        typ, dur = chosen or (TRANSITION_TYPES[len(out) % 2], 0.3)  # alternate fade/crossfade
        out.append({"at": c["end"], "type": typ, "duration": _r(_clamp(dur or 0.3, 0.1, 1.0))})
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
    # Words (mostly) removed by a filler cut do not get captions.
    kept = [w for w in words if not any(
        min(c["end"], w["end_time"]) - max(c["start"], w["start_time"]) >= 0.5 * (w["end_time"] - w["start_time"])
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
# Stickers, SFX, Zooms
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
    return {"x": _r(_clamp(x, 0.05, 0.95)), "y": _r(_clamp(y, 0.05, 0.95))}


def build_stickers(llm_stickers: Any, words: List[Dict[str, Any]], cuts: List[Dict[str, Any]], duration: float) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for s in _as_list(llm_stickers):
        if not isinstance(s, dict):
            continue
        keyword = str(s.get("keyword") or s.get("entity") or s.get("name") or "").strip()
        if not keyword:
            continue
        slug = slugify(str(s.get("slug") or keyword))
        if slug in seen:
            continue
        seen.add(slug)

        start = _f(s.get("start"))
        mention = _find_mention(keyword, words, start)
        if mention is not None:
            start = mention
        if start is None:
            continue
        start = _push_out_of_cuts(_clamp(start, 0, max(0.0, duration - 0.5)), cuts)
        dur = _clamp(_f(s.get("duration"), 2.0) or 2.0, 0.5, 5.0)
        dur = min(dur, max(0.5, duration - start))

        asset = s.get("asset_url") or s.get("asset") or f"/api/stickers/{slug}.png"
        out.append({
            "keyword": keyword,
            "slug": slug,
            "asset_url": str(asset),
            "start": _r(start),
            "duration": _r(dur),
            "position": _position(s.get("position")) or dict(STICKER_SLOTS[0]),
            "scale": _r(_clamp(_f(s.get("scale"), 1.0) or 1.0, 0.3, 2.5)),
        })
    out.sort(key=lambda x: x["start"])
    out = out[:MAX_STICKERS]

    # Stagger stickers that would sit on top of each other.
    for i, cur in enumerate(out):
        used = {
            (p["position"]["x"], p["position"]["y"])
            for p in out[:i]
            if p["start"] < cur["start"] + cur["duration"] and cur["start"] < p["start"] + p["duration"]
        }
        if (cur["position"]["x"], cur["position"]["y"]) in used:
            for slot in STICKER_SLOTS:
                if (slot["x"], slot["y"]) not in used:
                    cur["position"] = dict(slot)
                    break
    return out


def resolve_sfx_asset(raw: Any) -> Tuple[str, str]:
    """Map 'vine_boom.mp3', '/assets/sfx/cash.mp3', 'boom' ... -> (name, asset_path)."""
    text = str(raw or "").strip()
    if text.startswith("/assets/sound-effects/") and text in SFX_LIBRARY.values():
        name = next(k for k, v in SFX_LIBRARY.items() if v == text)
        return name, text
    stem = re.sub(r"\.(mp3|wav|ogg|m4a)$", "", text.rsplit("/", 1)[-1].lower())
    stem = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
    name = stem if stem in SFX_LIBRARY else SFX_ALIASES.get(stem, "vine_boom")
    return name, SFX_LIBRARY[name]


def build_sfx(llm_sfx: Any, cuts: List[Dict[str, Any]], duration: float) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in _as_list(llm_sfx):
        if not isinstance(s, dict):
            continue
        start = _f(s.get("start"))
        if start is None:
            continue
        start = _push_out_of_cuts(_clamp(start, 0, max(0.0, duration - 0.1)), cuts)
        name, asset = resolve_sfx_asset(s.get("asset") or s.get("name") or s.get("sfx"))
        if any(abs(o["start"] - start) < 0.5 for o in out):
            continue
        label = s.get("label")
        out.append({
            "asset": asset,
            "start": _r(start),
            "volume": _r(_clamp(_f(s.get("volume"), 0.8) or 0.8, 0.0, 1.0)),
            "label": str(label) if label else name,
        })
    out.sort(key=lambda x: x["start"])
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
        scale = _clamp(_f(z.get("scale"), 1.25) or 1.25, 1.0, 2.0)
        items.append((s, e, scale))
    items.sort()
    out: List[Dict[str, Any]] = []
    for s, e, scale in items:
        if out and s < out[-1]["end"]:
            out[-1]["end"] = _r(max(out[-1]["end"], e))
            continue
        out.append({"start": _r(s), "end": _r(e), "scale": _r(scale)})
    return out


# ---------------------------------------------------------------------------
# Heuristic director (offline fallback)
# ---------------------------------------------------------------------------

def heuristic_director(words: List[Dict[str, Any]]) -> Dict[str, Any]:
    stickers, sfx, zooms = [], [], []
    seen = set()
    for w in words:
        tok = _norm_token(w["word"])
        for key, label in HEURISTIC_ENTITIES.items():
            if tok == key or (len(key) >= 4 and tok.startswith(key)):
                if label not in seen:
                    seen.add(label)
                    stickers.append({"keyword": label, "start": w["start_time"], "duration": 2.0})
                break
        for name, triggers in HEURISTIC_SFX_TRIGGERS.items():
            if tok in triggers:
                sfx.append({"asset": name, "start": w["start_time"], "volume": 0.8, "label": name})
                if name == "vine_boom" and len(zooms) < 3:
                    zooms.append({"start": w["start_time"], "end": w["end_time"] + 0.5, "scale": 1.25})
                break
        if w["word"].endswith("!") and len(zooms) < 3:
            zooms.append({"start": w["start_time"], "end": w["end_time"] + 0.4, "scale": 1.25})
    return {"stickers": stickers, "sfx": sfx[:6], "zooms": zooms}


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
) -> Dict[str, Any]:
    """Merge STT + silences + director suggestions into a consistent EditPlan dict."""
    raw = dict(raw_plan or {})
    warnings = list(warnings or []) + [w for w in _as_list(raw.get("warnings")) if isinstance(w, str)]

    norm_words = normalize_words(words) if words else normalize_words(raw.get("words"))
    transcript = (transcript or str(raw.get("transcript") or "")).strip() or " ".join(w["word"] for w in norm_words)

    last_word_end = norm_words[-1]["end_time"] if norm_words else 0.0
    dur = _f(duration) or _f(raw.get("duration")) or 0.0
    dur = _r(max(dur, last_word_end))

    cuts = build_cuts(raw.get("cuts"), silence_cuts, norm_words, dur, warnings)
    plan = {
        "project_id": project_id or raw.get("project_id"),
        "transcript": transcript,
        "language_code": str(raw.get("language_code") or language_code or "hi-IN"),
        "duration": dur,
        "words": norm_words,
        "captions": build_captions(norm_words, cuts, raw.get("captions")),
        "cuts": cuts,
        "transitions": build_transitions(cuts, raw.get("transitions"), dur),
        "stickers": build_stickers(raw.get("stickers"), norm_words, cuts, dur),
        "sfx": build_sfx(raw.get("sfx"), cuts, dur),
        "zooms": build_zooms(raw.get("zooms"), cuts, dur),
        "director": director or raw.get("director"),
        "warnings": warnings,
    }
    if not plan["language_code"] or plan["language_code"] == "unknown":
        plan["language_code"] = language_code if language_code != "unknown" else "hi-IN"
    return plan
