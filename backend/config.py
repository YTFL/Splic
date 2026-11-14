"""
config.py — Centralized configuration for user local storage paths and settings.
Resolves ~/.splic/ for database and downloaded stickers (decoupled from the git repo).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base user application storage directory (~/.splic or env override)
DEFAULT_USER_DIR = Path.home() / ".splic"
SPLIC_DIR = Path(os.getenv("SPLIC_DATA_DIR", str(DEFAULT_USER_DIR)))

# Storage subpaths
DB_PATH = SPLIC_DIR / "db.json"
STICKERS_DIR = SPLIC_DIR / "stickers"
RUNS_DIR = SPLIC_DIR / "runs"          # per Auto-Cut run: sticker_requests.json + edit_plan.json

# Ensure user storage directories exist
SPLIC_DIR.mkdir(parents=True, exist_ok=True)
STICKERS_DIR.mkdir(parents=True, exist_ok=True)

# Server port
PORT = int(os.getenv("PORT", 8000))

# Project root references (read-only)
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
_STUDIO_DIR = PROJECT_ROOT / "timeline_studio" if (PROJECT_ROOT / "timeline_studio").exists() else PROJECT_ROOT / "timeline studio"
TIMELINE_STUDIO_STICKERS_DIR = _STUDIO_DIR / "public" / "assets" / "stickers"
TIMELINE_STUDIO_MANIFEST = TIMELINE_STUDIO_STICKERS_DIR / "stickers-manifest.json"
TIMELINE_STUDIO_SFX_DIR = _STUDIO_DIR / "public" / "assets" / "sound-effects"
