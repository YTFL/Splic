"""Main FastAPI Application Entrypoint.

Initializes CORS, middleware, global error handling, and API routes under /api/v1.
"""

import sys
from pathlib import Path

# Ensure backend/composio is in sys.path
_base_dir = Path(__file__).resolve().parent.parent
if str(_base_dir) not in sys.path:
    sys.path.insert(0, str(_base_dir))

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.config import get_settings
from app.api.routes import (
    health_router,
    composio_router,
    instagram_router,
    youtube_router,
    accounts_router,
    publish_router,
)
from app.auth.firebase import initialize_firebase_admin
from app.integrations.composio.client import get_composio_client_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("composio.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for application startup and shutdown."""
    settings = get_settings()
    logger.info(f"Starting Splic Composio Backend [env={settings.ENVIRONMENT}, port={settings.PORT}]")
    
    # Initialize Firebase Admin SDK
    initialize_firebase_admin()

    # Introspect Composio status without logging credentials
    client_status = get_composio_client_manager().get_health_status()
    if client_status["is_configured"]:
        logger.info("Composio API credentials configured successfully.")
    else:
        logger.warning(
            "COMPOSIO_API_KEY is not configured or in development mode. "
            "Live OAuth calls will require credentials or mock injection."
        )

    yield

    logger.info("Shutting down Splic Composio Backend.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title="Splic Composio Integration API",
        description=(
            "Autonomous OAuth connection manager for Instagram and YouTube via Composio. "
            "Part of the Splic Indic Video Auto-Editor platform."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS
    allowed_origins = settings.cors_origins
    logger.info(f"Configuring CORS with origins: {allowed_origins}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
    )

    # Global Exception Handlers
    @app.exception_handler(PermissionError)
    async def permission_error_handler(request: Request, exc: PermissionError) -> JSONResponse:
        logger.warning(f"Permission denied: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc), "error_type": "PermissionDenied"},
        )

    @app.exception_handler(KeyError)
    async def not_found_handler(request: Request, exc: KeyError) -> JSONResponse:
        logger.info(f"Resource not found: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc).strip("'"), "error_type": "NotFound"},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        logger.info(f"Validation error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc), "error_type": "ValidationError"},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(f"Unhandled exception during {request.method} {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal server error occurred. Please verify backend logs.",
                "error_type": "InternalServerError",
            },
        )

    # Register Routers under /api/v1
    api_prefix = "/api/v1"
    app.include_router(health_router, prefix=api_prefix)
    app.include_router(composio_router, prefix=api_prefix)
    app.include_router(instagram_router, prefix=api_prefix)
    app.include_router(youtube_router, prefix=api_prefix)
    app.include_router(accounts_router, prefix=api_prefix)
    app.include_router(publish_router, prefix=api_prefix)

    # Serve staged renders so Instagram's servers can fetch them by URL.
    media_dir = settings.media_root
    media_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(media_dir)), name="splic_media")

    # Root health convenience redirects
    @app.get("/health", include_in_schema=False)
    def root_health():
        return {"status": "healthy", "service": "composio-backend"}

    @app.get("/", include_in_schema=False)
    def root():
        return {
            "name": "Splic Composio Backend",
            "version": "1.0.0",
            "docs": "/docs",
            "api_v1": "/api/v1",
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.ENVIRONMENT == "development"),
        log_level=settings.LOG_LEVEL.lower(),
    )

