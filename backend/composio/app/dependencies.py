"""FastAPI dependencies for authentication, user identity, and service injection."""

import logging
from typing import Optional
from fastapi import Header, HTTPException, status
from pydantic import BaseModel, Field
from app.config import Settings, get_settings
from app.auth.firebase import verify_firebase_id_token
from app.integrations.composio.client import get_composio_client_manager
from app.integrations.composio.connections import ConnectionManager
from app.integrations.composio.toolkit_discovery import ToolkitDiscoveryService
from app.integrations.composio.execution import ActionExecutionService
from app.services.account_service import AccountService
from app.services.connection_service import ConnectionService
from app.services.publish_service import PublishService

logger = logging.getLogger("composio.dependencies")


class AuthenticatedUser(BaseModel):
    """User identity representation derived strictly from verified Firebase Authentication."""
    id: str = Field(..., description="Unique Firebase User ID (UID)")
    email: Optional[str] = Field(None, description="User email address if available")
    is_development_fallback: bool = Field(False, description="Flag indicating if test/dev mode was used")


def get_current_user(
    authorization: Optional[str] = Header(
        None,
        description="Firebase ID token passed as 'Bearer <FIREBASE_ID_TOKEN>'"
    ),
) -> AuthenticatedUser:
    """Resolve the authenticated user identity via Firebase ID token verification.
    
    Security rules:
    - Never trust arbitrary user IDs from client headers (e.g. X-User-ID) or query params.
    - Token must be a valid, signed Firebase ID token.
    - Expiration and revocation checks are strictly enforced.
    - Extracts the verified Firebase UID as the canonical user identity.
    """
    settings: Settings = get_settings()

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide 'Authorization: Bearer <FIREBASE_ID_TOKEN>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <FIREBASE_ID_TOKEN>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split("Bearer ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token in Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify ID token via Firebase Admin SDK
    decoded_claims = verify_firebase_id_token(token, check_revoked=True)
    uid = decoded_claims.get("uid") or decoded_claims.get("sub") or decoded_claims.get("user_id")

    if not uid:
        logger.error(f"Verified Firebase token claims missing 'uid': {decoded_claims}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims: missing user identifier (UID).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthenticatedUser(
        id=str(uid),
        email=decoded_claims.get("email"),
        is_development_fallback=decoded_claims.get("is_dev", False),
    )


def get_connection_manager() -> ConnectionManager:
    """Dependency provider for ConnectionManager."""
    return ConnectionManager(get_composio_client_manager())


def get_account_service() -> AccountService:
    """Dependency provider for AccountService."""
    return AccountService(get_connection_manager())


def get_connection_service() -> ConnectionService:
    """Dependency provider for ConnectionService."""
    return ConnectionService(get_connection_manager())


def get_discovery_service() -> ToolkitDiscoveryService:
    """Dependency provider for ToolkitDiscoveryService."""
    return ToolkitDiscoveryService(get_composio_client_manager())


def get_publish_service() -> PublishService:
    """Dependency provider for the social publishing service."""
    return PublishService(get_composio_client_manager())


def get_execution_service() -> ActionExecutionService:
    """Dependency provider for ActionExecutionService."""
    client_mgr = get_composio_client_manager()
    discovery = ToolkitDiscoveryService(client_mgr)
    return ActionExecutionService(client_mgr, discovery)
