from typing import List, Optional
from pydantic import BaseModel, Field


class WordTimestamp(BaseModel):
    word: str
    start_time: float
    end_time: float


class CutSegment(BaseModel):
    start: float
    end: float
    reason: str = "silence"


class Position2D(BaseModel):
    x: float = Field(default=0.5, ge=0.0, le=1.0)
    y: float = Field(default=0.3, ge=0.0, le=1.0)


class StickerOverlay(BaseModel):
    keyword: str
    asset: Optional[str] = None
    start: float
    duration: float = 2.0
    position: Position2D = Field(default_factory=Position2D)


class SfxEvent(BaseModel):
    asset: str
    start: float
    volume: float = Field(default=0.8, ge=0.0, le=1.0)


class ZoomKeyframe(BaseModel):
    start: float
    end: float
    scale: float = Field(default=1.25, ge=1.0, le=2.0)


class EditPlan(BaseModel):
    transcript: str
    words: List[WordTimestamp]
    cuts: List[CutSegment] = Field(default_factory=list)
    stickers: List[StickerOverlay] = Field(default_factory=list)
    sfx: List[SfxEvent] = Field(default_factory=list)
    zooms: List[ZoomKeyframe] = Field(default_factory=list)
