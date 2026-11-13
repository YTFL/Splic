"""
catalog.py — The editor's real creative vocabulary, shared by the director prompt
(so the LLM only picks things Timeline Studio can render) and by plan_builder /
schemas (so anything else is rejected).

Sources of truth in timeline_studio/src (keep these lists in sync):
  * transitions     -> lib/projectCommandEngine.js  PROJECT_TRANSITION_IDS (+ lib/maskTransitions.js)
  * clip in/out     -> lib/visualClipAnimations.js  VISUAL_CLIP_ANIMATION_OPTIONS
  * timeline effects-> lib/timelineEffects.js       TIMELINE_EFFECT_IDS (subset suited to auto-edits)
  * sound effects   -> public/assets/sound-effects/*.mp3
  * sticker library -> public/assets/stickers/stickers-manifest.json  (+ cached scrapes in ~/.splic/stickers)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from config import STICKERS_DIR, TIMELINE_STUDIO_MANIFEST, TIMELINE_STUDIO_SFX_DIR

logger = logging.getLogger("catalog")

# ---------------------------------------------------------------------------
# Transitions (visual clip seams after a cut) — exact editor ids
# ---------------------------------------------------------------------------
TRANSITION_IDS: List[str] = [
    "fade", "zoom", "flash", "wipe-left", "wipe-up", "blur", "split", "glitch",
    "diagonal-fold", "ripple-mask", "step-mask", "shutter-mask",
]
LEGACY_TRANSITIONS: Dict[str, str] = {
    "fade_black": "fade", "crossfade": "fade", "wipe_left": "wipe-left",
    "wipe_up": "wipe-up", "zoom_in": "zoom", "none": "",
}

# ---------------------------------------------------------------------------
# Sticker in / out animations
# NATIVE ids are the editor's own clip animations ({in:{id,duration}, out:{id,duration}}).
# KEYFRAMED ids do not exist in the editor; plan_builder compiles them into
# transform keyframes ({time, scale, rotation, opacity}) on the sticker.
# ---------------------------------------------------------------------------
NATIVE_ANIMATIONS: List[str] = ["fade", "zoom", "slide-left", "slide-up"]
KEYFRAMED_IN: List[str] = ["pop", "bounce", "spin"]
KEYFRAMED_OUT: List[str] = ["pop"]
ANIMATION_IN_IDS: List[str] = ["none"] + NATIVE_ANIMATIONS + KEYFRAMED_IN
ANIMATION_OUT_IDS: List[str] = ["none"] + NATIVE_ANIMATIONS + KEYFRAMED_OUT
EMPHASIS_IDS: List[str] = ["none", "wiggle", "pulse"]

# ---------------------------------------------------------------------------
# Timeline effects (used sparingly)
# ---------------------------------------------------------------------------
EFFECT_IDS: List[str] = ["glitch", "shake", "chromatic", "glow", "shape-flash", "vignette"]

# ---------------------------------------------------------------------------
# Sound effects
# ---------------------------------------------------------------------------
SFX_DIR_URL = "/assets/sound-effects"
# Musical single notes are useless as edit SFX; keep them out of the prompt.
_SFX_EXCLUDE_PREFIXES = ("piano-", "nylon-guitar-", "steel-guitar-")
_SFX_FALLBACK_IDS = [
    "soft-thud", "coins-1", "bell-hit", "ui-glitch-1", "laugh", "gasp", "wrong-a",
    "correct-a", "clap", "ui-switch-1", "level-up-a",
]

# Legacy / colloquial names -> real file ids
SFX_ALIASES: Dict[str, str] = {
    "vine_boom": "soft-thud", "boom": "soft-thud", "vineboom": "soft-thud", "bass_boom": "soft-thud",
    "bruh": "soft-thud", "thud": "soft-thud",
    "cash": "coins-1", "money": "coins-1", "cash_register": "coins-1", "coins": "coins-1",
    "kaching": "coins-1", "cha_ching": "coins-1",
    "ding": "bell-hit", "bell": "bell-hit", "notification": "bell-hit",
    "success": "correct-a", "correct": "correct-a",
    "record_scratch": "ui-glitch-1", "scratch": "ui-glitch-1", "glitch": "ui-glitch-1",
    "applause": "clap", "whoosh": "ui-switch-1", "swoosh": "ui-switch-1", "swipe": "ui-switch-1",
    "fail": "wrong-a", "buzzer": "wrong-a", "wrong": "wrong-a",
    "win": "level-up-a", "level_up": "level-up-a", "pop": "ui-click-1", "click": "ui-click-1",
}

_sfx_cache: Optional[List[str]] = None


def sfx_ids() -> List[str]:
    """All usable bundled SFX ids (file stems), discovered from disk once."""
    global _sfx_cache
    if _sfx_cache is None:
        ids: List[str] = []
        if TIMELINE_STUDIO_SFX_DIR.exists():
            ids = sorted(
                p.stem for p in TIMELINE_STUDIO_SFX_DIR.glob("*.mp3")
                if not p.stem.startswith(_SFX_EXCLUDE_PREFIXES)
            )
        _sfx_cache = ids or list(_SFX_FALLBACK_IDS)
    return _sfx_cache


def sfx_url(sound_id: str) -> str:
    return f"{SFX_DIR_URL}/{sound_id}.mp3"


def resolve_sfx_id(raw: object) -> Optional[str]:
    """Map 'coins-1', 'coins-1.mp3', '/assets/sound-effects/coins-1.mp3', 'cash', 'boom' -> real id."""
    import re

    text = str(raw or "").strip()
    if not text:
        return None
    stem = re.sub(r"\.(mp3|wav|ogg|m4a)$", "", text.rsplit("/", 1)[-1].strip().lower())
    known = set(sfx_ids())
    if stem in known:
        return stem
    alias = SFX_ALIASES.get(re.sub(r"[^a-z0-9]+", "_", stem).strip("_"))
    if alias and alias in known:
        return alias
    hyph = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return hyph if hyph in known else None


# ---------------------------------------------------------------------------
# Sticker library (bundled manifest + previously scraped stickers on disk)
# ---------------------------------------------------------------------------

def bundled_stickers() -> List[Dict[str, str]]:
    """[{id, name, category, asset_url}] from the Timeline Studio sticker manifest."""
    if not TIMELINE_STUDIO_MANIFEST.exists():
        return []
    try:
        items = json.loads(TIMELINE_STUDIO_MANIFEST.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not read sticker manifest: %s", exc)
        return []
    out = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or not item.get("id") or not item.get("src"):
            continue
        out.append({
            "id": str(item["id"]),
            "name": str(item.get("nameEn") or item["id"]),
            "category": str(item.get("category") or ""),
            "asset_url": str(item["src"]),
        })
    return out


def cached_stickers() -> List[Dict[str, str]]:
    """Stickers already scraped into ~/.splic/stickers (reusable at zero cost)."""
    if not STICKERS_DIR.exists():
        return []
    return [
        {"id": p.stem, "name": p.stem.replace("_", " "), "category": "scraped",
         "asset_url": f"/api/stickers/{p.name}"}
        for p in sorted(STICKERS_DIR.glob("*.png"))
        if p.stat().st_size > 0
    ]


def sticker_library() -> Dict[str, Dict[str, str]]:
    """id -> entry for every sticker the director may reference with source='library'."""
    lib = {s["id"]: s for s in cached_stickers()}
    lib.update({s["id"]: s for s in bundled_stickers()})  # bundled ids win on clash
    return lib


def prompt_catalog() -> Dict[str, object]:
    """Compact catalogue injected into the director's user message."""
    return {
        "sticker_library": [
            {"id": s["id"], "name": s["name"], "category": s["category"]}
            for s in sticker_library().values()
        ],
        "sound_effects": sfx_ids(),
        "transitions": TRANSITION_IDS,
        "animation_in": ANIMATION_IN_IDS,
        "animation_out": ANIMATION_OUT_IDS,
        "emphasis": EMPHASIS_IDS,
        "effects": EFFECT_IDS,
    }
