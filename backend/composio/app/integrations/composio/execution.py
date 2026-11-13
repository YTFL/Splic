"""Controlled Action Execution Service for Composio.

Enforces strict allowlisting, prevents publishing/mutating calls,
and executes safe read-only actions for authenticated users.
"""

import logging
from typing import Any, Dict, Optional
from .client import ComposioClientManager, get_composio_client_manager
from .toolkit_discovery import (
    ToolkitDiscoveryService,
    ALLOWLISTED_READ_ONLY_ACTIONS,
    BLOCKED_MUTATING_ACTIONS,
)
from app.schemas.action import ExecuteActionResponse

logger = logging.getLogger("composio.execution")


class ActionExecutionService:
    """Safely executes allowlisted Composio tools with boundary guards."""

    def __init__(
        self,
        client_manager: Optional[ComposioClientManager] = None,
        discovery_service: Optional[ToolkitDiscoveryService] = None
    ):
        self.client_manager = client_manager or get_composio_client_manager()
        self.discovery = discovery_service or ToolkitDiscoveryService(self.client_manager)

    def execute_action(
        self,
        action_slug: str,
        user_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        account_id: Optional[str] = None
    ) -> ExecuteActionResponse:
        """Safely execute an action after checking allowlist boundaries.
        
        Args:
            action_slug: Identifier of action (e.g. 'INSTAGRAM_GET_USER_INFO')
            user_id: Owner user identity
            parameters: Action input arguments
            account_id: Optional explicit connected account ID
        """
        slug_upper = action_slug.upper()
        params = parameters or {}

        # 1. Guard against blocked mutating/publishing actions
        if slug_upper in BLOCKED_MUTATING_ACTIONS:
            error_msg = (
                f"Action '{action_slug}' is a mutating/publishing action and is strictly "
                f"BLOCKED in this version of the backend. Automatic posting is out of scope."
            )
            logger.warning(f"Blocked forbidden action attempt by user '{user_id}': {action_slug}")
            raise PermissionError(error_msg)

        # 2. Guard against unknown or non-allowlisted actions
        if slug_upper not in ALLOWLISTED_READ_ONLY_ACTIONS:
            error_msg = (
                f"Action '{action_slug}' is not in the approved safe read-only allowlist. "
                f"Allowed actions: {sorted(list(ALLOWLISTED_READ_ONLY_ACTIONS))}"
            )
            logger.warning(f"Rejected unapproved action attempt: {action_slug}")
            raise PermissionError(error_msg)

        client = self.client_manager.get_client()

        # 3. Execute via Composio tools layer
        try:
            # Composio v3 direct tool execution
            if hasattr(client, "tools") and hasattr(client.tools, "execute"):
                exec_kwargs = {
                    "slug": slug_upper,
                    "arguments": params,
                    "user_id": user_id,
                }
                if account_id:
                    exec_kwargs["connected_account_id"] = account_id

                result = client.tools.execute(**exec_kwargs)
                return ExecuteActionResponse(
                    success=True,
                    action_slug=slug_upper,
                    data=result,
                    message=f"Action '{slug_upper}' executed successfully.",
                )

            # Legacy ToolSet: toolset.execute_action(action=..., params=..., entity_id=...)
            if hasattr(client, "execute_action"):
                result = client.execute_action(
                    action=slug_upper,
                    params=params,
                    entity_id=user_id,
                )
                return ExecuteActionResponse(
                    success=True,
                    action_slug=slug_upper,
                    data=result,
                    message=f"Action '{slug_upper}' executed successfully via legacy ToolSet.",
                )

            # Mock client execution handler
            if hasattr(client, "execute"):
                result = client.execute(slug=slug_upper, parameters=params, user_id=user_id)
                return ExecuteActionResponse(
                    success=True,
                    action_slug=slug_upper,
                    data=result,
                    message=f"Action '{slug_upper}' executed via mock client.",
                )

            raise RuntimeError("Composio client does not expose a supported tool execution method.")

        except PermissionError:
            raise
        except Exception as exc:
            logger.error(f"Error executing Composio action '{action_slug}': {exc}")
            raise RuntimeError(f"Action execution failed: {str(exc)}") from exc

