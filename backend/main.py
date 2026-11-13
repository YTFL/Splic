"""
main.py — FastAPI Backend for Splic (Indic Video Auto-Editor)
Modular orchestrator importing from dedicated submodules (e.g. scraper).
"""

import os
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from scraper import (
    fetch_and_make_sticker,
    list_downloaded_stickers,
    get_sticker_path,
    DOWNLOADS_DIR,
    HAS_REMBG,
)

load_dotenv()
PORT = int(os.getenv("PORT", 8000))

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
TIMELINE_STUDIO_STICKERS_DIR = PROJECT_ROOT / "timeline studio" / "public" / "assets" / "stickers"

@asynccontextmanager
async def lifespan(app: FastAPI):
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    yield

app = FastAPI(
    title="Splic Backend API",
    version="1.2.0",
    description="FastAPI service for video auto-cut pipeline and dynamic asset discovery.",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Cross-Origin Asset Safety (COEP / CORP) Middleware
@app.middleware("http")
async def add_corp_headers(request, call_next):
    response: Response = await call_next(request)
    response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


# Read-only mount of existing default stickers from Timeline Studio
if TIMELINE_STUDIO_STICKERS_DIR.exists():
    app.mount(
        "/assets/stickers",
        StaticFiles(directory=str(TIMELINE_STUDIO_STICKERS_DIR)),
        name="default_static_stickers",
    )


# Schemas
class StickerScrapeRequest(BaseModel):
    keyword: str
    timeout: Optional[float] = 4.0


class BatchStickerScrapeRequest(BaseModel):
    keywords: List[str]
    timeout: Optional[float] = 4.0


class StickerResponse(BaseModel):
    keyword: str
    slug: str
    filename: str
    asset_url: str
    local_path: Optional[str] = None
    size_bytes: int = 0
    cached: bool
    fallback: bool


class BatchStickerResponse(BaseModel):
    stickers: List[StickerResponse]
    failed: List[str]


class StickerItem(BaseModel):
    filename: str
    slug: str
    size_bytes: int
    asset_url: str
    modified_at: str


class StickerListResponse(BaseModel):
    total: int
    stickers: List[StickerItem]


# Endpoints
@app.get("/")
@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": "splic-backend",
        "port": PORT,
        "features": {
            "scraper_module": True,
            "rembg": HAS_REMBG,
            "mock_mode": os.getenv("USE_MOCK", "true").lower() == "true",
        },
    }


@app.get("/api/stickers/scrape", response_model=StickerResponse)
async def scrape_sticker_get(
    keyword: str = Query(..., description="Entity keyword, e.g. 'Zomato', 'Biryani'"),
    timeout: float = Query(4.0, description="Fetch timeout in seconds"),
):
    """GET endpoint to search, process, and download a transparent sticker."""
    res = fetch_and_make_sticker(keyword, timeout=timeout)
    if not res:
        raise HTTPException(status_code=404, detail=f"No sticker could be found or generated for '{keyword}'")
    return res


@app.post("/api/stickers/scrape", response_model=StickerResponse)
async def scrape_sticker_post(req: StickerScrapeRequest):
    """POST endpoint to search, process, and download a transparent sticker."""
    res = fetch_and_make_sticker(req.keyword, timeout=req.timeout or 4.0)
    if not res:
        raise HTTPException(status_code=404, detail=f"No sticker could be found or generated for '{req.keyword}'")
    return res


@app.post("/api/stickers/batch", response_model=BatchStickerResponse)
async def scrape_stickers_batch(req: BatchStickerScrapeRequest):
    """Batch-scrape or retrieve cached stickers for a list of entity keywords."""
    stickers = []
    failed = []

    for kw in req.keywords:
        kw = kw.strip()
        if not kw:
            continue
        res = fetch_and_make_sticker(kw, timeout=req.timeout or 4.0)
        if res:
            stickers.append(res)
        else:
            failed.append(kw)

    return {"stickers": stickers, "failed": failed}


@app.get("/api/stickers", response_model=StickerListResponse)
async def list_stickers():
    """List all downloaded stickers in the scraper module."""
    items = list_downloaded_stickers()
    return {
        "total": len(items),
        "stickers": items,
    }


@app.api_route("/api/stickers/{filename}", methods=["GET", "HEAD"])
async def serve_sticker(filename: str):
    """Serve a transparent sticker PNG directly with CORP headers."""
    file_path = get_sticker_path(filename)
    if not file_path:
        raise HTTPException(status_code=404, detail="Sticker not found")

    return FileResponse(
        path=str(file_path),
        media_type="image/png",
        headers={
            "Cross-Origin-Resource-Policy": "cross-origin",
            "Access-Control-Allow-Origin": "*",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
