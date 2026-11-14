"""API Routes subpackage."""

from .health import router as health_router
from .composio import router as composio_router
from .instagram import router as instagram_router
from .youtube import router as youtube_router
from .accounts import router as accounts_router
from .publish import router as publish_router

__all__ = [
    "health_router",
    "composio_router",
    "instagram_router",
    "youtube_router",
    "accounts_router",
    "publish_router",
]
