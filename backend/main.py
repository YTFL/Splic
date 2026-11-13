"""
main.py — FastAPI Backend for Splic (Indic Video Auto-Editor)
Integrated with TinyDB in user local storage (~/.splic/db.json) and transparent stickers (~/.splic/stickers/).
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import (
    PORT,
    DB_PATH,
    SPLIC_DIR,
    STICKERS_DIR,
    TIMELINE_STUDIO_STICKERS_DIR,
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
    HAS_REMBG,
)


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
