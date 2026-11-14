"""
composio_integration.py — Mounts the Composio + Firebase Auth service
(``backend/composio/app``, merged from branch ``Kiran``) into the main Splic
FastAPI app, so ONE server on one port serves:

  * the Sarvam auto-edit pipeline, projects, and stickers  (/api/...)
  * Composio OAuth, accounts, and toolkits, guarded by Firebase ID tokens  (/api/v1/...)

``backend/composio/`` can still run on its own (``uvicorn app.main:app`` from
inside that folder); this module only reuses its routers, startup hook, and
error mapping.

Configuration for this part comes from the repository-root ``.env.local``
(see the root ``.env.example``): COMPOSIO_API_KEY, FIREBASE_PROJECT_ID and
FIREBASE_SERVICE_ACCOUNT_JSON. If they are missing, the routes still mount:
health endpoints report "UNCONFIGURED" and protected routes return 401/400/500
with a clear message instead of crashing the server.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger("splic.composio_integration")

COMPOSIO_SERVICE_DIR = Path(__file__).resolve().parent / "composio"
API_V1_PREFIX = "/api/v1"

# Kiran's service is the top-level package ``app`` inside backend/composio/.
# NOTE: backend/composio/ deliberately has no __init__.py. With one, the folder
# would shadow the installed ``composio`` SDK whenever backend/ is on sys.path.
if COMPOSIO_SERVICE_DIR.is_dir() and str(COMPOSIO_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(COMPOSIO_SERVICE_DIR))

IMPORT_ERROR: Optional[str] = None
try:
    from app.api.routes import (  # type: ignore  # noqa: E402
        accounts_router,
        composio_router,
        health_router,
        instagram_router,
        publish_router,
        youtube_router,
    )
    from app.auth.firebase import initialize_firebase_admin  # type: ignore  # noqa: E402
    from app.config import get_settings as get_composio_settings  # type: ignore  # noqa: E402
    from app.integrations.composio.client import get_composio_client_manager  # type: ignore  # noqa: E402

    COMPOSIO_AVAILABLE = True
except Exception as exc:  # missing deps (pydantic-settings, firebase-admin, ...) or missing folder
    COMPOSIO_AVAILABLE = False
    IMPORT_ERROR = f"{type(exc).__name__}: {exc}"
    logger.warning("Composio/Firebase service not mounted: %s", IMPORT_ERROR)


def _is_v1(request: Request) -> bool:
    return request.url.path.startswith(API_V1_PREFIX)


def register(app: FastAPI) -> bool:
    """Include the Composio routers under /api/v1 and install scoped error mapping."""
    if not COMPOSIO_AVAILABLE:
        return False

    for router in (
        health_router,
        composio_router,
        instagram_router,
        youtube_router,
        accounts_router,
        publish_router,
    ):
        app.include_router(router, prefix=API_V1_PREFIX)

    # Serve staged renders so Instagram's servers can fetch them by public URL.
    try:
        media_dir = get_composio_settings().media_root
        media_dir.mkdir(parents=True, exist_ok=True)
        app.mount("/media", StaticFiles(directory=str(media_dir)), name="splic_media")
    except Exception as exc:  # never block the main server on a media directory issue
        logger.warning("Could not mount the publishing media directory: %s", exc)

    # Same exception -> status mapping as backend/composio/app/main.py, applied
    # ONLY to /api/v1 routes so the pipeline routes keep FastAPI's defaults.
    def _fallback(request: Request, exc: Exception) -> PlainTextResponse:
        logger.error("Unhandled %s on %s %s: %s", type(exc).__name__, request.method, request.url.path, exc,
                     exc_info=exc)
        return PlainTextResponse("Internal Server Error", status_code=500)

    @app.exception_handler(PermissionError)
    async def _permission_error(request: Request, exc: PermissionError):
        if not _is_v1(request):
            return _fallback(request, exc)
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN,
                            content={"detail": str(exc), "error_type": "PermissionDenied"})

    @app.exception_handler(KeyError)
    async def _not_found(request: Request, exc: KeyError):
        if not _is_v1(request):
            return _fallback(request, exc)
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"detail": str(exc).strip("'"), "error_type": "NotFound"})

    @app.exception_handler(ValueError)
    async def _value_error(request: Request, exc: ValueError):
        if not _is_v1(request):
            return _fallback(request, exc)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"detail": str(exc), "error_type": "ValidationError"})

    logger.info("Mounted Composio/Firebase routes under %s", API_V1_PREFIX)
    return True


def startup() -> None:
    """Initialise Firebase Admin (no-op with a warning if credentials are absent)."""
    if not COMPOSIO_AVAILABLE:
        return
    try:
        initialize_firebase_admin()
        if not get_composio_client_manager().get_health_status()["is_configured"]:
            logger.warning("COMPOSIO_API_KEY not configured in root .env.local; OAuth routes will return errors.")
    except Exception as exc:  # never block the main server
        logger.warning("Composio/Firebase startup check failed: %s", exc)


def status_summary() -> Dict[str, Any]:
    """Compact status block for /api/health."""
    if not COMPOSIO_AVAILABLE:
        return {"mounted": False, "error": IMPORT_ERROR}
    try:
        settings = get_composio_settings()
        composio = get_composio_client_manager().get_health_status()
        return {
            "mounted": True,
            "prefix": API_V1_PREFIX,
            "composio_configured": bool(composio.get("is_configured")),
            "composio_sdk_installed": bool(composio.get("sdk_installed")),
            "firebase_configured": bool(settings.is_firebase_configured),
            "env_file": str(settings.root_env_file),
            "env_file_present": bool(settings.is_root_env_present),
        }
    except Exception as exc:
        return {"mounted": True, "error": str(exc)}
