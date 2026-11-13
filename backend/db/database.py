"""
db/database.py — TinyDB Local NoSQL Database Manager.
Stores projects, timeline state, and sticker metadata in ~/.splic/db.json.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path

from tinydb import TinyDB, Query

from config import DB_PATH

logger = logging.getLogger("db")
logger.setLevel(logging.INFO)

# Global or lazily-loaded DB instance
_db_instance: Optional[TinyDB] = None


def _now_iso() -> str:
    """Generate ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


def get_db() -> TinyDB:
    """Get or initialize the TinyDB instance."""
    global _db_instance
    if _db_instance is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _db_instance = TinyDB(str(DB_PATH), indent=2)
        logger.info(f"Connected to TinyDB at: {DB_PATH}")
    return _db_instance


def close_db():
    """Close the TinyDB instance."""
    global _db_instance
    if _db_instance is not None:
        _db_instance.close()
        _db_instance = None


# ============================================================================
# Projects CRUD
# ============================================================================

def create_project(
    name: str,
    project_id: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a new project document."""
    db = get_db()
    table = db.table("projects")
    Project = Query()

    p_id = (project_id or f"proj_{uuid.uuid4().hex[:10]}").strip()

    # Check if project_id already exists
    existing = table.get(Project.id == p_id)
    if existing:
        return existing

    now = _now_iso()
    doc = {
        "id": p_id,
        "name": name,
        "created_at": now,
        "updated_at": now,
        "status": "draft",
        "settings": settings or {"aspect_ratio": "9:16", "target_duration": 30},
        "edit_plan": None,
    }

    table.insert(doc)
    logger.info(f"Created project in TinyDB: {p_id} ('{name}')")
    return doc


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a project document by its ID."""
    db = get_db()
    table = db.table("projects")
    Project = Query()
    return table.get(Project.id == project_id)


def list_projects() -> List[Dict[str, Any]]:
    """List all project documents."""
    db = get_db()
    table = db.table("projects")
    return table.all()


def update_project(project_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update fields on a project document."""
    db = get_db()
    table = db.table("projects")
    Project = Query()

    existing = table.get(Project.id == project_id)
    if not existing:
        return None

    updates["updated_at"] = _now_iso()
    # Do not allow modifying the primary ID
    updates.pop("id", None)

    table.update(updates, Project.id == project_id)
    return table.get(Project.id == project_id)


def delete_project(project_id: str) -> bool:
    """Delete a project and its associated sticker references."""
    db = get_db()
    projects_table = db.table("projects")
    stickers_table = db.table("stickers")
    Project = Query()
    Sticker = Query()

    removed = projects_table.remove(Project.id == project_id)
    if removed:
        stickers_table.remove(Sticker.project_id == project_id)
        logger.info(f"Deleted project '{project_id}' and associated sticker links from TinyDB")
        return True
    return False


# ============================================================================
# Stickers Metadata CRUD
# ============================================================================

def record_sticker(
    keyword: str,
    slug: str,
    filename: str,
    save_path: str,
    asset_url: str,
    size_bytes: int = 0,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Record a downloaded transparent sticker into TinyDB."""
    db = get_db()
    table = db.table("stickers")
    Sticker = Query()

    target_proj = project_id or "global"
    existing = table.get((Sticker.slug == slug) & (Sticker.project_id == target_proj))
    if existing:
        return existing

    doc_id = f"stk_{slug}_{uuid.uuid4().hex[:6]}"
    doc = {
        "id": doc_id,
        "project_id": target_proj,
        "keyword": keyword,
        "slug": slug,
        "filename": filename,
        "save_path": str(save_path),
        "asset_url": asset_url,
        "size_bytes": size_bytes,
        "created_at": _now_iso(),
    }

    table.insert(doc)
    logger.info(f"Indexed sticker in TinyDB: '{slug}' for project '{target_proj}'")
    return doc


def get_project_stickers(project_id: str) -> List[Dict[str, Any]]:
    """Get all stickers associated with a project (and global stickers)."""
    db = get_db()
    table = db.table("stickers")
    Sticker = Query()
    return table.search((Sticker.project_id == project_id) | (Sticker.project_id == "global"))


def get_all_stickers() -> List[Dict[str, Any]]:
    """Get all cataloged stickers in TinyDB."""
    db = get_db()
    table = db.table("stickers")
    return table.all()


def get_sticker_by_keyword(keyword: str, project_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Search for a sticker document by keyword."""
    db = get_db()
    table = db.table("stickers")
    Sticker = Query()
    kw_lower = keyword.lower().strip()

    if project_id:
        res = table.get((Sticker.project_id == project_id) & (Sticker.slug == kw_lower))
        if res:
            return res

    return table.get(Sticker.slug == kw_lower)
