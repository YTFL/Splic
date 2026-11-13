"""Session management for Composio user contexts."""

import logging
from typing import Any, Dict, List, Optional
from .client import ComposioClientManager, get_composio_client_manager

logger = logging.getLogger("composio.sessions")


class SessionManager:
    """Manages user sessions in Composio."""

    def __init__(self, client_manager: Optional[ComposioClientManager] = None):
        self.client_manager = client_manager or get_composio_client_manager()
        self._sessions: Dict[str, Any] = {}

    def get_or_create_session(
        self,
        user_id: str,
        toolkits: Optional[List[str]] = None
    ) -> Any:
        """Create or retrieve a Composio runtime session for a given user.
        
        Args:
            user_id: Unique identifier for the user.
            toolkits: Optional list of toolkit slugs to scope this session.
        """
        cache_key = f"{user_id}:{','.join(sorted(toolkits or []))}"
        if cache_key in self._sessions:
            return self._sessions[cache_key]

        client = self.client_manager.get_client()

        # Check for Composio v3 session creation: composio.create(user_id=...)
        if hasattr(client, "create"):
            kwargs: Dict[str, Any] = {"user_id": user_id}
            if toolkits:
                kwargs["toolkits"] = toolkits
            session = client.create(**kwargs)
            self._sessions[cache_key] = session
            logger.info(f"Created Composio v3 session for user '{user_id}' with toolkits {toolkits}")
            return session

        # Fallback for legacy composio-core ToolSet: toolset.get_entity(id=...)
        if hasattr(client, "get_entity"):
            entity = client.get_entity(id=user_id)
            self._sessions[cache_key] = entity
            logger.info(f"Created legacy entity session for user '{user_id}'")
            return entity

        # Generic client object (e.g. mock object)
        self._sessions[cache_key] = client
        return client

    def clear_cache(self, user_id: Optional[str] = None) -> None:
        """Clear cached sessions for a specific user or all users."""
        if user_id:
            keys_to_remove = [k for k in self._sessions if k.startswith(f"{user_id}:")]
            for k in keys_to_remove:
                self._sessions.pop(k, None)
        else:
            self._sessions.clear()

