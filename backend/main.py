"""
main.py — FastAPI Backend for Splic (Indic Video Auto-Editor)
Integrated with TinyDB in user local storage (~/.splic/db.json) and transparent stickers (~/.splic/stickers/).
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Query, Response, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, ValidationError

from config import (
    PORT,
    DB_PATH,
    SPLIC_DIR,
    STICKERS_DIR,
    TIMELINE_STUDIO_STICKERS_DIR,
    TIMELINE_STUDIO_SFX_DIR,
)

from schemas import EditPlan
from audio_utils import AudioDecodeError, prepare_audio, has_ffmpeg
from silence_detector import detect_silences, _PYDUB_AVAILABLE
from sarvam_client import transcribe_audio, direct_video_edit, is_mock_enabled
from plan_builder import build_edit_plan, heuristic_director, normalize_words

from db import (
    create_project,
    get_project,
    list_projects,
    update_project,
    delete_project,
    record_sticker,
    get_project_stickers,
    get_all_stickers,
)

from scraper import (
    fetch_and_make_sticker,
    get_sticker_path,
    HAS_REMBG,
)
from scraper.sticker_engine import find_static_fallback

logger = logging.getLogger("splic.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure user storage directories are ready on startup
    SPLIC_DIR.mkdir(parents=True, exist_ok=True)
    STICKERS_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Splic Backend API",
    version="1.3.0",
    description="Video auto-cut backend with TinyDB local document storage and sticker synthesis.",
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


# Read-only mount of existing default stickers from Timeline Studio (read-only reference)
if TIMELINE_STUDIO_STICKERS_DIR.exists():
    app.mount(
        "/assets/stickers",
        StaticFiles(directory=str(TIMELINE_STUDIO_STICKERS_DIR)),
        name="default_static_stickers",
    )

# Read-only mount of bundled sound effects referenced by EditPlan.sfx[].asset
if TIMELINE_STUDIO_SFX_DIR.exists():
    app.mount(
        "/assets/sound-effects",
        StaticFiles(directory=str(TIMELINE_STUDIO_SFX_DIR)),
        name="default_sound_effects",
    )


# ============================================================================
# Pydantic Schemas
# ============================================================================

class ProjectCreateRequest(BaseModel):
    name: str
    project_id: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    edit_plan: Optional[Dict[str, Any]] = None


class StickerScrapeRequest(BaseModel):
    keyword: str
    project_id: Optional[str] = None
    timeout: Optional[float] = 4.0


class BatchStickerScrapeRequest(BaseModel):
    keywords: List[str]
    project_id: Optional[str] = None
    timeout: Optional[float] = 4.0


class StickerResponse(BaseModel):
    keyword: str
    slug: str
    filename: str
    asset_url: str
    save_path: Optional[str] = None
    size_bytes: int = 0
    cached: bool
    fallback: bool
    project_id: Optional[str] = "global"


class BatchStickerResponse(BaseModel):
    stickers: List[StickerResponse]
    failed: List[str]


# ============================================================================
# Health & Storage Info
# ============================================================================

@app.get("/")
@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": "splic-backend",
        "port": PORT,
        "storage": {
            "splic_dir": str(SPLIC_DIR),
            "db_path": str(DB_PATH),
            "stickers_dir": str(STICKERS_DIR),
        },
        "features": {
            "tinydb_nosql": True,
            "user_local_storage": True,
            "rembg": HAS_REMBG,
            "ffmpeg": has_ffmpeg(),
            "pydub": _PYDUB_AVAILABLE,
            "use_mock": is_mock_enabled(),
            "sarvam_key_configured": os.getenv("SARVAM_API_KEY", "").strip()
            not in ("", "your_sarvam_api_subscription_key"),
            "fallback_provider": os.getenv("FALLBACK_PROVIDER", "none"),
        },
    }


# ============================================================================
# Projects Endpoints (TinyDB)
# ============================================================================

@app.post("/api/projects", status_code=201)
async def create_new_project(req: ProjectCreateRequest):
    """Create a new video editing project document in TinyDB."""
    doc = create_project(
        name=req.name,
        project_id=req.project_id,
        settings=req.settings,
    )
    return doc


@app.get("/api/projects")
async def get_all_projects():
    """List all projects stored in TinyDB."""
    return {"projects": list_projects()}


@app.get("/api/projects/{project_id}")
async def get_single_project(project_id: str):
    """Get project details and metadata by ID."""
    doc = get_project(project_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return doc


@app.patch("/api/projects/{project_id}")
async def update_single_project(project_id: str, req: ProjectUpdateRequest):
    """Update project status, settings, or edit plan in TinyDB."""
    updates = req.model_dump(exclude_unset=True)
    updated = update_project(project_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return updated


@app.delete("/api/projects/{project_id}")
async def delete_single_project(project_id: str):
    """Delete a project and its associated sticker references from TinyDB."""
    deleted = delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return {"status": "deleted", "project_id": project_id}


# ============================================================================
# Sticker Scraper & Asset Endpoints (TinyDB + ~/.splic/stickers/)
# ============================================================================

@app.get("/api/stickers/scrape", response_model=StickerResponse)
async def scrape_sticker_get(
    keyword: str = Query(..., description="Entity keyword, e.g. 'Zomato', 'Biryani'"),
    project_id: Optional[str] = Query(None, description="Optional project ID to associate with"),
    timeout: float = Query(4.0, description="Fetch timeout in seconds"),
):
    """Search, background-strip, save into ~/.splic/stickers/, and record in TinyDB."""
    res = fetch_and_make_sticker(keyword, timeout=timeout)
    if not res:
        raise HTTPException(status_code=404, detail=f"No sticker could be found or generated for '{keyword}'")

    # Record in TinyDB
    if not res.get("fallback") and res.get("save_path"):
        record_sticker(
            keyword=res["keyword"],
            slug=res["slug"],
            filename=res["filename"],
            save_path=res["save_path"],
            asset_url=res["asset_url"],
            size_bytes=res.get("size_bytes", 0),
            project_id=project_id,
        )

    res["project_id"] = project_id or "global"
    return res


@app.post("/api/stickers/scrape", response_model=StickerResponse)
@app.post("/api/projects/{project_id}/stickers/scrape", response_model=StickerResponse)
async def scrape_sticker_post(
    req: StickerScrapeRequest,
    project_id: Optional[str] = None,
):
    """POST endpoint to scrape, save sticker into user storage, and index in TinyDB."""
    target_project = project_id or req.project_id
    res = fetch_and_make_sticker(req.keyword, timeout=req.timeout or 4.0)
    if not res:
        raise HTTPException(status_code=404, detail=f"No sticker could be found or generated for '{req.keyword}'")

    if not res.get("fallback") and res.get("save_path"):
        record_sticker(
            keyword=res["keyword"],
            slug=res["slug"],
            filename=res["filename"],
            save_path=res["save_path"],
            asset_url=res["asset_url"],
            size_bytes=res.get("size_bytes", 0),
            project_id=target_project,
        )

    res["project_id"] = target_project or "global"
    return res


@app.post("/api/stickers/batch", response_model=BatchStickerResponse)
async def scrape_stickers_batch(req: BatchStickerScrapeRequest):
    """Batch-scrape stickers and index all successful results in TinyDB."""
    stickers = []
    failed = []

    for kw in req.keywords:
        kw = kw.strip()
        if not kw:
            continue
        res = fetch_and_make_sticker(kw, timeout=req.timeout or 4.0)
        if res:
            if not res.get("fallback") and res.get("save_path"):
                record_sticker(
                    keyword=res["keyword"],
                    slug=res["slug"],
                    filename=res["filename"],
                    save_path=res["save_path"],
                    asset_url=res["asset_url"],
                    size_bytes=res.get("size_bytes", 0),
                    project_id=req.project_id,
                )
            res["project_id"] = req.project_id or "global"
            stickers.append(res)
        else:
            failed.append(kw)

    return {"stickers": stickers, "failed": failed}


@app.get("/api/stickers")
async def list_all_cataloged_stickers():
    """List all stickers recorded in TinyDB."""
    return {"total": len(get_all_stickers()), "stickers": get_all_stickers()}


@app.get("/api/projects/{project_id}/stickers")
async def list_stickers_for_project(project_id: str):
    """List all stickers associated with a project in TinyDB."""
    stickers = get_project_stickers(project_id)
    return {"project_id": project_id, "total": len(stickers), "stickers": stickers}


@app.api_route("/api/stickers/{filename}", methods=["GET", "HEAD"])
async def serve_sticker(filename: str):
    """Serve a transparent sticker PNG directly from ~/.splic/stickers/ with CORP headers."""
    file_path = get_sticker_path(filename)
    if not file_path:
        raise HTTPException(status_code=404, detail=f"Sticker '{filename}' not found in user storage")

    return FileResponse(
        path=str(file_path),
        media_type="image/png",
        headers={
            "Cross-Origin-Resource-Policy": "cross-origin",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ============================================================================
# Sarvam Auto-Edit Pipeline
# ============================================================================

_STICKER_TIMEOUT = 4.0          # per-sticker scrape budget (AGENTS.md Rule 6)
_STICKER_BATCH_DEADLINE = 10.0  # wall-clock cap for all stickers together


def _sticker_fetch_enabled() -> bool:
    return os.getenv("STICKER_FETCH", "true").strip().lower() in ("1", "true", "yes", "on")


def _offline_sticker(keyword: str, slug: str) -> Optional[Dict[str, Any]]:
    """Resolve a sticker from disk cache or bundled static icons only (no network)."""
    cached = get_sticker_path(slug)
    if cached:
        return {"asset_url": f"/api/stickers/{cached.name}", "fallback": False}
    static = find_static_fallback(keyword)
    if static:
        return {"asset_url": static, "fallback": True}
    return None


def _synthesize_stickers(
    stickers: List[Dict[str, Any]],
    project_id: Optional[str],
    allow_network: bool,
    warnings: List[str],
) -> List[Dict[str, Any]]:
    """Ensure every sticker points at a real PNG; skip the ones that cannot be resolved."""
    if not stickers:
        return []

    results: Dict[int, Optional[Dict[str, Any]]] = {}
    if allow_network:
        pool = ThreadPoolExecutor(max_workers=min(4, len(stickers)))
        futures = {
            pool.submit(fetch_and_make_sticker, s["keyword"], _STICKER_TIMEOUT): i
            for i, s in enumerate(stickers)
        }
        done, _pending = wait(futures, timeout=_STICKER_BATCH_DEADLINE)
        for fut in done:
            try:
                results[futures[fut]] = fut.result()
            except Exception as exc:  # the scraper must never crash the pipeline
                logger.warning("Sticker synthesis failed: %s", exc)
        pool.shutdown(wait=False, cancel_futures=True)

    out = []
    skipped = []
    for i, s in enumerate(stickers):
        res = results.get(i) or _offline_sticker(s["keyword"], s["slug"])
        if not res or not res.get("asset_url"):
            skipped.append(s["keyword"])
            continue
        s = dict(s, asset_url=res["asset_url"])
        if not res.get("fallback") and res.get("save_path"):
            try:
                record_sticker(
                    keyword=res["keyword"],
                    slug=res["slug"],
                    filename=res["filename"],
                    save_path=res["save_path"],
                    asset_url=res["asset_url"],
                    size_bytes=res.get("size_bytes", 0),
                    project_id=project_id,
                )
            except Exception as exc:
                logger.warning("Could not index sticker '%s': %s", s["keyword"], exc)
        out.append(s)
    if skipped:
        warnings.append("No sticker image available for: " + ", ".join(skipped))
    return out


@app.post("/api/sarvam-auto-edit", response_model=EditPlan)
def sarvam_auto_edit(
    file: UploadFile = File(..., description="Audio (WAV/MP3/M4A...) or video (MP4/MOV/WEBM...) file"),
    project_id: Optional[str] = Form(None),
    language_code: str = Form("hi-IN"),
    use_mock: Optional[bool] = Form(None, description="Override USE_MOCK for this request"),
    fetch_stickers: bool = Form(True, description="Allow web sticker scraping (DuckDuckGo + rembg)"),
):
    """
    Full Indic Auto-Edit pipeline:
    1. Decode upload -> 16 kHz mono WAV (bundled ffmpeg handles video containers)
    2. Local silence detection (zero API cost)
    3. Sarvam Saaras v4 STT (transliteration mode, word timestamps)
    4. Sarvam-105B Video Director LLM (JSON mode) with Groq/Gemini/heuristic fallback
    5. plan_builder: merge + sanitise everything onto one consistent source clock
    6. Dynamic sticker synthesis (cache -> DuckDuckGo + rembg -> static icon -> skip)

    Returns a validated EditPlan. All timestamps are on the ORIGINAL source clock.
    Sync handler: FastAPI runs it in a worker thread, so blocking HTTP / ffmpeg
    calls never stall the event loop.
    """
    mock = is_mock_enabled() if use_mock is None else bool(use_mock)
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    filename = file.filename or "upload.wav"
    warnings: List[str] = []

    try:
        if mock:
            stt = transcribe_audio(b"", filename, language_code, mock=True)
            raw_plan = direct_video_edit(stt["transcript"], stt["words"], [], language_code, mock=True)
            silence_cuts: List[Dict[str, Any]] = []
            duration = raw_plan.get("duration")
            director = "mock"
        else:
            try:
                prepared = prepare_audio(data, filename)
            except AudioDecodeError as exc:
                raise HTTPException(status_code=415, detail=str(exc))
            duration = prepared.duration

            try:
                silence_cuts = detect_silences(prepared.wav_bytes)
            except Exception as exc:
                silence_cuts = []
                warnings.append(f"Silence detection failed: {exc}")

            try:
                stt = transcribe_audio(prepared.wav_bytes, filename, language_code, mock=False)
            except (RuntimeError, httpx.HTTPError) as exc:
                raise HTTPException(status_code=502, detail=f"Speech-to-text failed: {exc}")
            if not stt.get("words"):
                warnings.append("Speech-to-text returned no words; only dead-air cuts were generated")

            try:
                raw_plan = direct_video_edit(
                    stt["transcript"], stt["words"], silence_cuts, language_code,
                    duration=duration, mock=False,
                )
                director = raw_plan.get("director")
            except RuntimeError as exc:
                logger.warning("Director unavailable, using heuristic director: %s", exc)
                raw_plan = heuristic_director(normalize_words(stt["words"]))
                director = "heuristic"
                warnings.append("Director LLM unavailable; used offline heuristics for stickers/SFX/zooms")

        detected_lang = stt.get("language_code")
        plan_dict = build_edit_plan(
            raw_plan,
            transcript=stt.get("transcript", ""),
            words=stt.get("words"),
            silence_cuts=silence_cuts,
            duration=duration,
            language_code=detected_lang if detected_lang and detected_lang != "unknown" else language_code,
            project_id=project_id,
            director=director,
            warnings=warnings,
        )
        plan_dict["stickers"] = _synthesize_stickers(
            plan_dict["stickers"],
            project_id,
            allow_network=fetch_stickers and _sticker_fetch_enabled(),
            warnings=plan_dict["warnings"],
        )

        plan = EditPlan.model_validate(plan_dict)

        if project_id and get_project(project_id):
            update_project(project_id, {
                "status": "auto_edited",
                "edit_plan": plan.model_dump(mode="json"),
            })
        return plan
    except HTTPException:
        raise
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False))
    except Exception as exc:
        logger.exception("Auto-edit pipeline failed")
        raise HTTPException(status_code=500, detail=f"Auto-edit pipeline failed: {exc}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
