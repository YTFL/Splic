"""Composio integration metadata, toolkit discovery, and controlled execution routes."""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import (
    AuthenticatedUser,
    get_current_user,
    get_discovery_service,
    get_execution_service,
)
from app.integrations.composio.client import get_composio_client_manager
from app.integrations.composio.toolkit_discovery import ToolkitDiscoveryService
from app.integrations.composio.execution import ActionExecutionService
from app.schemas.action import (
    ToolkitSummary,
    ActionSummary,
    ExecuteActionRequest,
    ExecuteActionResponse,
)

router = APIRouter(prefix="/composio", tags=["Composio Core"])


@router.get("/status", response_model=Dict[str, Any], summary="Get Composio SDK Status")
def get_composio_status(
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """Retrieve detailed Composio configuration, SDK status, and user session context."""
    client_status = get_composio_client_manager().get_health_status()
    return {
        "composio": client_status,
        "authenticated_user_id": current_user.id,
        "is_dev_user": current_user.is_development_fallback,
    }


@router.get("/toolkits", response_model=List[ToolkitSummary], summary="List Supported Toolkits")
def list_toolkits(
    discovery_service: ToolkitDiscoveryService = Depends(get_discovery_service),
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> List[ToolkitSummary]:
    """List supported social media toolkits (Instagram, YouTube) with action metrics."""
    return discovery_service.list_supported_toolkits()


@router.get("/actions/{toolkit}", response_model=List[ActionSummary], summary="Discover Toolkit Actions")
def list_toolkit_actions(
    toolkit: str,
    discovery_service: ToolkitDiscoveryService = Depends(get_discovery_service),
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> List[ActionSummary]:
    """Discover available actions for a specific toolkit and verify allowlist permissions."""
    try:
        return discovery_service.list_actions(toolkit_slug=toolkit, user_id=current_user.id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover actions for {toolkit}: {str(exc)}"
        )


@router.post("/execute", response_model=ExecuteActionResponse, summary="Execute Controlled Action")
def execute_action(
    request: ExecuteActionRequest,
    execution_service: ActionExecutionService = Depends(get_execution_service),
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> ExecuteActionResponse:
    """Execute an approved, allowlisted action for the authenticated user.
    
    Security note:
    Mutating and publishing actions (e.g. creating posts, uploading videos) are
    strictly rejected with 403 Forbidden. Only safe read-only operations are permitted.
    """
    try:
        return execution_service.execute_action(
            action_slug=request.action_slug,
            user_id=current_user.id,
            parameters=request.parameters,
            account_id=request.account_id,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution error: {str(exc)}"
        )

