"""
project_info.py — Builds each project's info from Splic's local storage.

Everything is read from the configured user storage (config.py, ~/.splic by
default or SPLIC_DATA_DIR):
  * db.json             TinyDB: project documents (status, settings, edit_plan) + sticker index
  * stickers/<slug>.png scraped transparent stickers referenced by the sticker index
  * runs/<run_id>/      per Auto-Cut run: sticker_requests.json, edit_plan.json, director_raw.json
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import DB_PATH, RUNS_DIR, SPLIC_DIR, STICKERS_DIR

logger = logging.getLogger("splic.project_info")

PLAN_COUNT_KEYS = ("cuts", "captions", "stickers", "sfx", "transitions", "zooms", "effects")


def storage_paths() -> Dict[str, str]:
    return {
        "splic_dir": str(SPLIC_DIR),
        "db_path": str(DB_PATH),
        "stickers_dir": str(STICKERS_DIR),
        "runs_dir": str(RUNS_DIR),
    }


def plan_counts(plan: Optional[Dict[str, Any]]) -> Dict[str, int]:
    plan = plan if isinstance(plan, dict) else {}
    return {key: len(plan.get(key) or []) for key in PLAN_COUNT_KEYS}


def _iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def index_runs() -> Dict[str, List[Dict[str, Any]]]:
    """project_id -> its Auto-Cut runs (newest first), read from runs/<run_id>/edit_plan.json."""
    by_project: Dict[str, List[Dict[str, Any]]] = {}
    if not RUNS_DIR.exists():
        return by_project
    for run_dir in RUNS_DIR.iterdir():
        plan_file = run_dir / "edit_plan.json"
        if not run_dir.is_dir() or not plan_file.is_file():
            continue
        try:
            plan = json.loads(plan_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.warning("Skipping unreadable run %s: %s", run_dir.name, exc)
            continue
        project_id = plan.get("project_id")
        if not project_id:
            continue  # ad-hoc runs that were not tied to a project
        by_project.setdefault(project_id, []).append({
            "run_id": run_dir.name,
            "path": str(run_dir),
            "created_at": _iso_mtime(plan_file),
            "director": plan.get("director"),
            "duration": plan.get("duration"),
            "counts": plan_counts(plan),
            "files": sorted(p.name for p in run_dir.iterdir() if p.is_file()),
        })
    for runs in by_project.values():
        runs.sort(key=lambda run: run["created_at"], reverse=True)
    return by_project


def project_summary(
    doc: Dict[str, Any],
    runs_by_project: Dict[str, List[Dict[str, Any]]],
    stickers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Project info for the Projects screen, from db.json + stickers/ + runs/."""
    project_id = doc.get("id")
    plan = doc.get("edit_plan") if isinstance(doc.get("edit_plan"), dict) else None
    runs = runs_by_project.get(project_id, [])
    own_stickers = [s for s in stickers if s.get("project_id") == project_id]
    sticker_files = [s for s in own_stickers if s.get("save_path") and Path(s["save_path"]).is_file()]
    latest = runs[0] if runs else None
    return {
        "status": doc.get("status") or "draft",
        "duration": (plan or {}).get("duration") or (latest or {}).get("duration") or 0,
        "language_code": (plan or {}).get("language_code"),
        "director": (plan or {}).get("director") or (latest or {}).get("director"),
        "counts": plan_counts(plan) if plan else (latest or {}).get("counts") or plan_counts(None),
        "has_edit_plan": bool(plan),
        "stickers": {
            "indexed": len(own_stickers),
            "on_disk": len(sticker_files),
            "thumbnail": sticker_files[0].get("asset_url") if sticker_files else None,
        },
        "runs": {
            "count": len(runs),
            "latest": latest,
        },
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


def list_project_infos(docs: List[Dict[str, Any]], stickers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Project documents without the heavy edit_plan body, each with a `summary`."""
    runs_by_project = index_runs()
    out = []
    for doc in docs:
        light = {k: v for k, v in doc.items() if k != "edit_plan"}
        light["summary"] = project_summary(doc, runs_by_project, stickers)
        out.append(light)
    out.sort(key=lambda d: d.get("updated_at") or "", reverse=True)
    return out


def remove_project_runs(project_id: str) -> int:
    """Delete runs/<run_id>/ folders belonging to a project. Returns how many were removed."""
    removed = 0
    runs_root = RUNS_DIR.resolve()
    for run in index_runs().get(project_id, []):
        path = Path(run["path"]).resolve()
        if path.parent != runs_root:  # never touch anything outside runs/
            continue
        try:
            shutil.rmtree(path)
            removed += 1
        except OSError as exc:
            logger.warning("Could not remove run folder %s: %s", path, exc)
    return removed
