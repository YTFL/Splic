"""Health and readiness endpoints."""

from typing import Any, Dict
from fastapi import APIRouter
from app.config import get_settings
from app.integrations.composio.client import get_composio_client_manager

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=Dict[str, Any], summary="Service Health Check")
def health_check() -> Dict[str, Any]:
    """Check service status, environment, and Composio SDK integration readiness."""
    settings = get_settings()
    composio_health = get_composio_client_manager().get_health_status()

    return {
        "status": "healthy",
        "service": "composio-backend",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "composio": composio_health,
    }


@router.get("/ready", response_model=Dict[str, Any], summary="Service Readiness Probe")
def readiness_check() -> Dict[str, Any]:
    """Verify backend readiness for accepting requests."""
    return {
        "status": "ready",
        "service": "composio-backend",
    }

