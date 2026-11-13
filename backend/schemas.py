"""
Pydantic V2 schemas for the Splic Indic Auto-Editor pipeline.
All timestamps are floating-point seconds.

The director LLM returns ONE response holding two JSON documents:
  * sticker_requests -> StickerRequest[]   (fed to the scraper / sticker library)
  * edit_plan        -> cuts, transitions, sticker placements (+ animations), sfx, zooms, effects
plan_builder sanitises both and main.py returns them merged as one EditPlan.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from catalog import EFFECT_IDS, TRANSITION_IDS


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


class WordTimestamp(BaseModel):
    """Single word with its start/end timestamps from Saaras v4 STT."""

    word: str
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")


class CaptionWord(BaseModel):
    """Per-word highlight timing used inside a karaoke chunk."""

    word: str
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    emphasis: bool = Field(default=False, description="Director flagged this as a punch word")


# ---------------------------------------------------------------------------
# Captions (built from Sarvam STT word timestamps, never from the LLM)
# ---------------------------------------------------------------------------


class CaptionChunk(BaseModel):
    """2-to-4 word Romanized karaoke caption block."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    start: float = Field(..., description="Chunk start time in seconds")
    end: float = Field(..., description="Chunk end time in seconds")
    text: str = Field(..., description="Full chunk text (space-joined words)")
    words: List[CaptionWord] = Field(
        ..., description="Per-word highlight timing"
    )
    highlight_color: str = Field(
        default="#FFD600",
        description="Active-word highlight colour (hex)",
    )
    position: dict = Field(
        default={"x": 50, "y": 75},
        description="Relative position on frame (percent, 0-100)",
    )


# ---------------------------------------------------------------------------
# Cuts & Transitions
# ---------------------------------------------------------------------------


class CutSegment(BaseModel):
    """Ripple-cut interval to remove from the timeline."""

    start: float = Field(..., description="Cut start in seconds")
    end: float = Field(..., description="Cut end in seconds")
    duration: float = Field(..., description="Cut duration in seconds")
    reason: str = Field(
        default="dead_air",
        description="Why this segment is cut (dead_air, filler_word, etc.)",
    )


# Exact Timeline Studio transition ids (PROJECT_TRANSITION_IDS), e.g. "wipe-left".
TransitionType = Enum("TransitionType", {t.replace("-", "_"): t for t in TRANSITION_IDS}, type=str)


class TransitionEvent(BaseModel):
    """Transition applied on the clip seam a ripple cut leaves behind."""

    at: float = Field(..., description="Seam position on the ORIGINAL clock (the cut's end), seconds")
    cut_index: int = Field(..., ge=0, description="Index into EditPlan.cuts this transition belongs to")
    transition_id: TransitionType = Field(..., description="Timeline Studio transition id")
    duration: float = Field(default=0.3, ge=0.1, le=1.5, description="Transition duration in seconds")


# ---------------------------------------------------------------------------
# Stickers
# ---------------------------------------------------------------------------


class StickerPosition(BaseModel):
    """Normalized (0–1) frame position for a sticker overlay."""

    x: float = Field(..., ge=0.0, le=1.0, description="Horizontal 0=left, 1=right")
    y: float = Field(..., ge=0.0, le=1.0, description="Vertical 0=top, 1=bottom")


class StickerRequest(BaseModel):
    """JSON 1 entry: what the scraper / library must supply, and how it resolved."""

    ref: str = Field(..., description="Id the edit plan's sticker placements point at")
    concept: str = Field(..., description="What the sticker depicts (spoken word / idea)")
    source: Literal["library", "scrape"] = Field(..., description="Requested source")
    library_id: Optional[str] = Field(default=None, description="Sticker library id when source=library")
    query: Optional[str] = Field(default=None, description="Image-search query when source=scrape")
    resolved: bool = Field(default=False, description="True when an image was found")
    resolution: Optional[str] = Field(
        default=None, description="library | cache | scraped | fallback_library | unresolved")
    asset_url: Optional[str] = Field(default=None, description="Resolved PNG URL")


class AnimationPhase(BaseModel):
    """Editor-native clip animation phase (timeline_studio/src/lib/visualClipAnimations.js)."""

    id: Literal["none", "fade", "zoom", "slide-left", "slide-up"] = "none"
    duration: float = Field(default=0.4, ge=0.1, le=3.0)


class StickerAnimation(BaseModel):
    """Same shape as Timeline Studio's segment.animation: {"in": {id, duration}, "out": {id, duration}}."""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    in_: AnimationPhase = Field(default_factory=AnimationPhase, alias="in")
    out: AnimationPhase = Field(default_factory=AnimationPhase)


class TransformKeyframe(BaseModel):
    """Editor transform keyframe (lib/visualEffects.js). time is local to the sticker; values are absolute."""

    time: float = Field(..., ge=0.0, description="Seconds from the sticker's start")
    scale: Optional[float] = Field(default=None, ge=0.1, le=20)
    rotation: Optional[float] = None
    opacity: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class StickerOverlay(BaseModel):
    """Sticker placed on the sticker track, with in/out animation."""

    keyword: str = Field(..., description="Concept the sticker depicts")
    slug: str = Field(..., description="Filesystem-safe slug for the PNG asset")
    asset_url: str = Field(..., description="URL path to the RGBA PNG sticker")
    start: float = Field(..., description="Sticker appear time in seconds")
    duration: float = Field(default=2.0, description="Sticker display duration in seconds")
    position: StickerPosition = Field(
        default_factory=lambda: StickerPosition(x=0.5, y=0.3)
    )
    scale: float = Field(default=1.0, description="Sticker scale multiplier")
    ref: Optional[str] = Field(default=None, description="StickerRequest.ref this placement uses")
    rotation: float = Field(default=0.0, ge=-45, le=45, description="Base rotation in degrees")
    source: Optional[str] = Field(default=None, description="How the asset resolved (StickerRequest.resolution)")
    animation_in: str = Field(default="none", description="Director's in-animation id (native or keyframed)")
    animation_out: str = Field(default="none", description="Director's out-animation id (native or keyframed)")
    emphasis: str = Field(default="none", description="none | wiggle | pulse")
    animation: StickerAnimation = Field(
        default_factory=StickerAnimation,
        description="Editor-native in/out phases (ids the editor already renders)",
    )
    keyframes: List[TransformKeyframe] = Field(
        default_factory=list,
        description="Compiled keyframes for animations the editor lacks (pop, bounce, spin, wiggle, pulse)",
    )


# ---------------------------------------------------------------------------
# Audio SFX, Zoom, Effects
# ---------------------------------------------------------------------------


class SfxEvent(BaseModel):
    """Sound-effect event placed on the audio SFX track."""

    asset: str = Field(..., description="Path or URL to the audio asset")
    sound_id: Optional[str] = Field(default=None, description="Bundled sound id (file stem)")
    start: float = Field(..., description="Playback start time in seconds")
    volume: float = Field(default=0.8, ge=0.0, le=1.0, description="Playback volume 0–1")
    label: Optional[str] = Field(
        default=None, description="Human-readable label for the SFX track UI"
    )


class ZoomKeyframe(BaseModel):
    """Punch-in zoom applied to the video track between start and end."""

    start: float = Field(..., description="Zoom ramp-in start in seconds")
    end: float = Field(..., description="Zoom ramp-out end in seconds")
    scale: float = Field(default=1.25, description="Peak scale multiplier")


# Timeline Studio effect ids (subset of TIMELINE_EFFECT_IDS) allowed in auto-edits.
EffectType = Enum("EffectType", {e.replace("-", "_"): e for e in EFFECT_IDS}, type=str)


class TimelineEffect(BaseModel):
    """Short timeline effect clip (glitch hit, shake on an impact, ...)."""

    effect: EffectType
    start: float = Field(..., description="Effect start in seconds")
    duration: float = Field(default=0.6, ge=0.1, le=3.0)
    intensity: float = Field(default=0.6, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Raw director response (shape check before sanitising)
# ---------------------------------------------------------------------------


class DirectorResponse(BaseModel):
    """Top-level shape the director LLM must return: two JSON documents in one object."""

    model_config = ConfigDict(extra="allow")

    sticker_requests: List[Dict[str, Any]] = Field(default_factory=list)
    edit_plan: Dict[str, Any]


# ---------------------------------------------------------------------------
# Top-Level Edit Plan
# ---------------------------------------------------------------------------


class EditPlan(BaseModel):
    """Top-level response schema returned by /api/sarvam-auto-edit."""

    project_id: Optional[str] = Field(
        default=None,
        description="Optional project identifier; auto-generated if omitted",
    )
    transcript: str = Field(..., description="Full Romanized transcript text")
    language_code: str = Field(
        default="hi-IN",
        description="BCP-47 language code detected by Saaras",
    )
    duration: float = Field(..., description="Total source video duration in seconds")

    words: List[WordTimestamp] = Field(
        ..., description="Word-level timestamp array from Saaras v4"
    )
    captions: List[CaptionChunk] = Field(
        default_factory=list, description="Karaoke caption chunks"
    )
    cuts: List[CutSegment] = Field(
        default_factory=list, description="Ripple-cut intervals"
    )
    transitions: List[TransitionEvent] = Field(
        default_factory=list, description="Clip transitions on cut seams"
    )
    stickers: List[StickerOverlay] = Field(
        default_factory=list, description="Sticker placements with animations"
    )
    sfx: List[SfxEvent] = Field(
        default_factory=list, description="SFX events"
    )
    zooms: List[ZoomKeyframe] = Field(
        default_factory=list, description="Punch-in zoom keyframes"
    )
    effects: List[TimelineEffect] = Field(
        default_factory=list, description="Sparing timeline effects (glitch, shake, ...)"
    )
    sticker_requests: List[StickerRequest] = Field(
        default_factory=list, description="JSON 1: sticker requests and how each resolved"
    )

    # Pipeline diagnostics (non-fatal). All timestamps above are on the
    # ORIGINAL source clock; the frontend applies `cuts` last (ripple-delete)
    # or offsets downstream items by the total cut duration preceding them.
    director: Optional[str] = Field(
        default=None,
        description="Which engine produced the creative decisions: sarvam | groq | gemini | heuristic",
    )
    run_id: Optional[str] = Field(
        default=None,
        description="Folder under ~/.splic/runs/ holding sticker_requests.json + edit_plan.json",
    )
    warnings: List[str] = Field(
        default_factory=list, description="Non-fatal pipeline warnings (fallbacks taken, items dropped)"
    )

    @classmethod
    def sample(cls) -> "EditPlan":
        """Return a minimal valid EditPlan for unit tests (no live API calls)."""
        return cls(
            project_id="sample-001",
            transcript="Aaj hum baat karenge Zomato ke baare mein",
            language_code="hi-IN",
            duration=12.5,
            words=[
                WordTimestamp(word="Aaj", start_time=0.0, end_time=0.4),
                WordTimestamp(word="hum", start_time=0.45, end_time=0.75),
                WordTimestamp(word="baat", start_time=0.80, end_time=1.10),
                WordTimestamp(word="karenge", start_time=1.15, end_time=1.70),
                WordTimestamp(word="Zomato", start_time=1.80, end_time=2.40),
                WordTimestamp(word="ke", start_time=2.45, end_time=2.60),
                WordTimestamp(word="baare", start_time=2.65, end_time=2.95),
                WordTimestamp(word="mein", start_time=3.00, end_time=3.30),
            ],
            captions=[
                CaptionChunk(
                    id="cap_1",
                    start=0.0,
                    end=1.70,
                    text="Aaj hum baat karenge",
                    words=[
                        CaptionWord(word="Aaj", start_time=0.0, end_time=0.4),
                        CaptionWord(word="hum", start_time=0.45, end_time=0.75),
                        CaptionWord(word="baat", start_time=0.80, end_time=1.10),
                        CaptionWord(word="karenge", start_time=1.15, end_time=1.70),
                    ],
                ),
                CaptionChunk(
                    id="cap_2",
                    start=1.80,
                    end=3.30,
                    text="Zomato ke baare mein",
                    words=[
                        CaptionWord(word="Zomato", start_time=1.80, end_time=2.40, emphasis=True),
                        CaptionWord(word="ke", start_time=2.45, end_time=2.60),
                        CaptionWord(word="baare", start_time=2.65, end_time=2.95),
                        CaptionWord(word="mein", start_time=3.00, end_time=3.30),
                    ],
                ),
            ],
            cuts=[
                CutSegment(start=4.50, end=6.20, duration=1.70, reason="dead_air"),
            ],
            transitions=[
                TransitionEvent(at=6.20, cut_index=0, transition_id="fade", duration=0.3),
            ],
            stickers=[
                StickerOverlay(
                    keyword="Zomato",
                    slug="zomato",
                    asset_url="/api/stickers/zomato.png",
                    start=1.80,
                    duration=2.0,
                    position=StickerPosition(x=0.5, y=0.3),
                    scale=1.0,
                    ref="s1",
                    source="scraped",
                    animation_in="pop",
                    animation_out="fade",
                    animation=StickerAnimation(out=AnimationPhase(id="fade", duration=0.3)),
                    keyframes=[
                        TransformKeyframe(time=0.0, scale=0.2, opacity=0.0),
                        TransformKeyframe(time=0.22, scale=1.18, opacity=1.0),
                        TransformKeyframe(time=0.35, scale=1.0),
                    ],
                ),
            ],
            sfx=[
                SfxEvent(
                    asset="/assets/sound-effects/coins-1.mp3",
                    sound_id="coins-1",
                    start=1.80,
                    volume=0.8,
                    label="coins-1",
                ),
            ],
            zooms=[
                ZoomKeyframe(start=1.80, end=2.40, scale=1.25),
            ],
            sticker_requests=[
                StickerRequest(ref="s1", concept="Zomato", source="scrape", query="Zomato logo",
                               resolved=True, resolution="scraped", asset_url="/api/stickers/zomato.png"),
            ],
        )
