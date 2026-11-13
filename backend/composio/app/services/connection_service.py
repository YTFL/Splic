"""Connection service orchestrating OAuth initiation for Instagram and YouTube."""

import logging
from typing import List, Optional
from app.integrations.composio.connections import ConnectionManager
from app.schemas.connection import (
    ConnectionInitiationResponse,
    ConnectionStatusResponse,
)

logger = logging.getLogger("composio.service.connection")


class ConnectionService:
    """Service handling Instagram and YouTube OAuth connection initiation."""

    def __init__(self, connection_manager: Optional[ConnectionManager] = None):
        self.connection_manager = connection_manager or ConnectionManager()

    def connect_instagram(
        self,
        user_id: str,
        redirect_url: Optional[str] = None,
        force_reconnect: bool = False
    ) -> ConnectionInitiationResponse:
        """Initiate OAuth flow for Instagram Creator / Business accounts."""
        if not force_reconnect:
            existing = self.connection_manager.check_connection_status(toolkit="instagram", user_id=user_id)
            if existing.is_active:
                logger.info(f"Active Instagram connection already exists for user '{user_id}' (account: {existing.connection_id})")

        return self.connection_manager.initiate_connection(
            toolkit="instagram",
            user_id=user_id,
            redirect_url=redirect_url
        )

    def connect_youtube(
        self,
        user_id: str,
        redirect_url: Optional[str] = None,
        force_reconnect: bool = False,
        scopes: Optional[List[str]] = None
    ) -> ConnectionInitiationResponse:
        """Initiate OAuth flow for YouTube / Google accounts."""
        if not force_reconnect:
            existing = self.connection_manager.check_connection_status(toolkit="youtube", user_id=user_id)
            if existing.is_active:
                logger.info(f"Active YouTube connection already exists for user '{user_id}' (account: {existing.connection_id})")

        return self.connection_manager.initiate_connection(
            toolkit="youtube",
            user_id=user_id,
            redirect_url=redirect_url,
            additional_params={"scopes": scopes} if scopes else None
        )

    def get_toolkit_status(self, toolkit: str, user_id: str) -> ConnectionStatusResponse:
        """Verify whether an active connection exists for the specified toolkit and user."""
        return self.connection_manager.check_connection_status(toolkit=toolkit, user_id=user_id)

