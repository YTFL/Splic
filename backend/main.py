"""
main.py — FastAPI Backend for Splic (Indic Video Auto-Editor)
Integrated with TinyDB in user local storage (~/.splic/db.json) and transparent stickers (~/.splic/stickers/).
"""

import json
import logging
import os
import uuid
from datetime import datetime
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
from sarvam_client import transcribe_audio, direct_video_edit, is_sarvam_configured
from plan_builder import (
    build_captions,
    build_edit_plan,
    heuristic_director,
    normalize_sticker_requests,
    normalize_words,
    refine_words_with_silences,
    split_director_output,
)

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
    resolve_sticker_requests,
    HAS_REMBG,
)

import composio_integration

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("splic.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure user storage directories are ready on startup
    SPLIC_DIR.mkdir(parents=True, exist_ok=True)
    STICKERS_DIR.mkdir(parents=True, exist_ok=True)
    composio_integration.startup()
    yield


app = FastAPI(
    title="Splic Backend API",
    version="1.5.0",
    description=(
        "Splic backend: Sarvam AI Auto-Cut pipeline, TinyDB projects, and sticker synthesis "
        "(/api/...), plus Composio OAuth for Instagram/YouTube behind Firebase Auth (/api/v1/...)."
    ),
    lifespan=lifespan,
)

# Composio + Firebase Auth service (merged from branch Kiran) -> /api/v1/*
composio_integration.register(app)

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
@app.get("/health")
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
            "sarvam_key_configured": is_sarvam_configured(),
            "director_model": os.getenv("SARVAM_LLM_MODEL", "glm5.3-flash"),
            "fallback_provider": os.getenv("FALLBACK_PROVIDER", "none"),
        },
        "composio": composio_integration.status_summary(),
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


class StickerRequestsBody(BaseModel):
    """JSON 1 (sticker_requests) as produced by the director, sent straight to the scraper."""

    sticker_requests: List[Dict[str, Any]]
    project_id: Optional[str] = None
    allow_network: bool = True


@app.post("/api/stickers/resolve")
def resolve_stickers_json(req: StickerRequestsBody):
    """Resolve a director sticker_requests JSON into PNG assets.

    Body: {"sticker_requests": [{"ref": "s1", "concept": "money", "source": "library",
           "library_id": "shop-coins"}, {"ref": "s2", "concept": "Swiggy", "source": "scrape",
           "query": "Swiggy logo"}], "project_id": "optional"}
    Returns the normalised requests with resolved / resolution / asset_url filled in.
    """
    requests = normalize_sticker_requests(req.sticker_requests, None)
    assets = resolve_sticker_requests(
        requests,
        allow_network=req.allow_network and _sticker_fetch_enabled(),
        on_scraped=lambda res: _index_sticker(res, req.project_id),
    )
    out = []
    for r in requests:
        asset = assets.get(r["ref"]) or {}
        out.append({**r, "resolved": bool(asset), "resolution": asset.get("resolution", "unresolved"),
                    "asset_url": asset.get("asset_url")})
    return {"sticker_requests": out, "failed": [r["concept"] for r in out if not r["resolved"]]}


@app.get("/api/projects/{project_id}/stickers")
async def list_stickers_for_project(project_id: str):
    """List all stickers associated with a project in TinyDB."""
    stickers = get_project_stickers(project_id)
    return {"project_id": project_id, "total": len(stickers), "stickers": stickers}


@app.get("/api/stickers/{filename}")
@app.head("/api/stickers/{filename}", include_in_schema=False)
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

RUNS_DIR = SPLIC_DIR / "runs"


def _sticker_fetch_enabled() -> bool:
    return os.getenv("STICKER_FETCH", "true").strip().lower() in ("1", "true", "yes", "on")


def _index_sticker(res: Dict[str, Any], project_id: Optional[str]) -> None:
    """Record a scraped / cached sticker PNG in TinyDB."""
    record_sticker(
        keyword=res["keyword"],
        slug=res["slug"],
        filename=res["filename"],
        save_path=res["save_path"],
        asset_url=res["asset_url"],
        size_bytes=res.get("size_bytes", 0),
        project_id=project_id,
    )


def _save_run(project_id: Optional[str], files: Dict[str, Any], warnings: List[str]) -> Optional[str]:
    """Persist the director's JSON documents under ~/.splic/runs/<run_id>/ for inspection / replay."""
    run_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{(project_id or 'adhoc')[:40]}-{uuid.uuid4().hex[:6]}"
    run_id = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in run_id)
    try:
        run_dir = RUNS_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            (run_dir / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return run_id
    except Exception as exc:
        warnings.append(f"Could not save run files: {exc}")
        return None


@app.post("/api/sarvam-auto-edit", response_model=EditPlan)
def sarvam_auto_edit(
    file: UploadFile = File(..., description="Audio (WAV/MP3/M4A...) or video (MP4/MOV/WEBM...) file"),
    project_id: Optional[str] = Form(None),
    language_code: str = Form("hi-IN"),
    fetch_stickers: bool = Form(True, description="Allow web sticker scraping (DuckDuckGo + rembg)"),
):
    """
    Full Indic Auto-Edit pipeline:
    1. Decode upload -> 16 kHz mono WAV (bundled ffmpeg handles video containers)
    2. Local silence detection (zero API cost)
    3. Sarvam Saaras v4 STT (transliteration mode, word timestamps)
    4. Karaoke captions built from the STT word timestamps (the "script")
    5. GLM-5.3-flash director on Sarvam (one JSON call) returns two documents:
         sticker_requests -> sticker scraper / library     (JSON 1)
         edit_plan        -> cuts, transitions, stickers + animations, sfx, zooms, effects (JSON 2)
       with Groq/Gemini/heuristic fallback
    6. Sticker resolution for JSON 1 (library -> cache -> DuckDuckGo + rembg -> bundled icon -> skip)
    7. plan_builder: sanitise JSON 2 against the editor's real ids, attach resolved stickers,
       compile sticker animations, keep everything on one source clock
    8. Save sticker_requests.json + edit_plan.json under ~/.splic/runs/<run_id>/

    Returns a validated EditPlan. All timestamps are on the ORIGINAL source clock.
    Sync handler: FastAPI runs it in a worker thread, so blocking HTTP / ffmpeg
    calls never stall the event loop.
    """
    if not is_sarvam_configured():
        raise HTTPException(
            status_code=503,
            detail="SARVAM_API_KEY is not configured. Add it to backend/.env and restart the backend.",
        )
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    filename = file.filename or "upload.wav"
    warnings: List[str] = []

    try:
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
            stt = transcribe_audio(prepared.wav_bytes, filename, language_code)
        except (RuntimeError, httpx.HTTPError) as exc:
            raise HTTPException(status_code=502, detail=f"Speech-to-text failed: {exc}")
        if not stt.get("words"):
            warnings.append("Speech-to-text returned no words; only dead-air cuts were generated")

        # The script the director reads: STT captions before any cut.
        # STT word timings are corrected against acoustic silences first.
        words = refine_words_with_silences(normalize_words(stt["words"]), silence_cuts)
        script_captions = build_captions(words, [], None)

        try:
            raw_plan = direct_video_edit(
                stt["transcript"], words, silence_cuts, language_code,
                duration=duration, captions=script_captions,
            )
            director = raw_plan.get("director")
        except RuntimeError as exc:
            logger.warning("Director unavailable, using heuristic director: %s", exc)
            raw_plan = heuristic_director(words)
            director = "heuristic"
            warnings.append(
                f"Director LLM unavailable; used offline heuristics for stickers/SFX/zooms ({str(exc)[:300]})"
            )

        # JSON 1 -> sticker scraper
        raw_requests, edit = split_director_output(raw_plan)
        sticker_requests = normalize_sticker_requests(raw_requests, edit.get("stickers"))
        sticker_assets = resolve_sticker_requests(
            sticker_requests,
            allow_network=fetch_stickers and _sticker_fetch_enabled(),
            on_scraped=lambda res: _index_sticker(res, project_id),
        )

        # JSON 2 -> sanitised edit plan with resolved stickers
        detected_lang = stt.get("language_code")
        plan_dict = build_edit_plan(
            raw_plan,
            transcript=stt.get("transcript", ""),
            words=words,
            silence_cuts=silence_cuts,
            duration=duration,
            language_code=detected_lang if detected_lang and detected_lang != "unknown" else language_code,
            project_id=project_id,
            director=director,
            warnings=warnings,
            sticker_requests=sticker_requests,
            sticker_assets=sticker_assets,
        )

        plan = EditPlan.model_validate(plan_dict)
        plan.run_id = _save_run(project_id, {
            "sticker_requests.json": {"sticker_requests": [r.model_dump(mode="json") for r in plan.sticker_requests]},
            "edit_plan.json": plan.model_dump(mode="json", exclude={"words", "transcript"}),
            "director_raw.json": raw_plan,
        }, plan.warnings)

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
