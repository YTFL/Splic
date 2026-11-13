"""
Pydantic V2 schemas for the Splic Indic Auto-Editor pipeline.
All timestamps are floating-point seconds.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


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


# ---------------------------------------------------------------------------
# Captions
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


class TransitionType(str, Enum):
    fade_black = "fade_black"
    wipe_left = "wipe_left"
    crossfade = "crossfade"
    zoom_in = "zoom_in"


class TransitionEvent(BaseModel):
    """Transition that occurs between two clips at a given timeline position."""

    at: float = Field(..., description="Timeline position in seconds")
    type: TransitionType = Field(
        default=TransitionType.fade_black,
        description="Transition style",
    )
    duration: float = Field(
        default=0.3,
        description="Transition duration in seconds",
    )


# ---------------------------------------------------------------------------
# Stickers
# ---------------------------------------------------------------------------


class StickerPosition(BaseModel):
    """Normalized (0–1) frame position for a sticker overlay."""

    x: float = Field(..., ge=0.0, le=1.0, description="Horizontal 0=left, 1=right")
    y: float = Field(..., ge=0.0, le=1.0, description="Vertical 0=top, 1=bottom")


class StickerOverlay(BaseModel):
    """Dynamic Indian-entity sticker placed on a timeline track."""

    keyword: str = Field(..., description="Detected entity keyword (e.g. 'Zomato')")
    slug: str = Field(..., description="Filesystem-safe slug for the PNG asset")
    asset_url: str = Field(..., description="URL path to the RGBA PNG sticker")
    start: float = Field(..., description="Sticker appear time in seconds")
    duration: float = Field(default=2.0, description="Sticker display duration in seconds")
    position: StickerPosition = Field(
        default_factory=lambda: StickerPosition(x=0.5, y=0.3)
    )
    scale: float = Field(default=1.0, description="Sticker scale multiplier")


# ---------------------------------------------------------------------------
# Audio SFX & Zoom
# ---------------------------------------------------------------------------


class SfxEvent(BaseModel):
    """Meme sound-effect event placed on the audio SFX track."""

    asset: str = Field(..., description="Path or URL to the audio asset")
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
        default_factory=list, description="Clip transitions after cuts"
    )
    stickers: List[StickerOverlay] = Field(
        default_factory=list, description="Dynamic sticker overlays"
    )
    sfx: List[SfxEvent] = Field(
        default_factory=list, description="Meme SFX events"
    )
    zooms: List[ZoomKeyframe] = Field(
        default_factory=list, description="Punch-in zoom keyframes"
    )

    # Pipeline diagnostics (non-fatal). All timestamps above are on the
    # ORIGINAL source clock; the frontend applies `cuts` last (ripple-delete)
    # or offsets downstream items by the total cut duration preceding them.
    director: Optional[str] = Field(
        default=None,
        description="Which engine produced the creative decisions: sarvam | groq | gemini | heuristic",
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
                    id="cap-001",
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
                    id="cap-002",
                    start=1.80,
                    end=3.30,
                    text="Zomato ke baare mein",
                    words=[
                        CaptionWord(word="Zomato", start_time=1.80, end_time=2.40),
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
                TransitionEvent(at=4.50, type=TransitionType.fade_black, duration=0.3),
            ],
            stickers=[
                StickerOverlay(
                    keyword="Zomato",
                    slug="zomato",
                    asset_url="/assets/dynamic_stickers/zomato.png",
                    start=1.80,
                    duration=2.0,
                    position=StickerPosition(x=0.5, y=0.3),
                    scale=1.0,
                ),
            ],
            sfx=[
                SfxEvent(
                    asset="/assets/sfx/cash.mp3",
                    start=1.80,
                    volume=0.8,
                    label="cash register",
                ),
            ],
            zooms=[
                ZoomKeyframe(start=1.80, end=2.40, scale=1.25),
            ],
        )
