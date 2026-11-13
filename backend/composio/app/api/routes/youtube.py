"""YouTube OAuth connection and account routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import AuthenticatedUser, get_current_user, get_connection_service, get_account_service
from app.schemas.account import AccountListResponse
from app.schemas.connection import (
    ConnectYouTubeRequest,
    ConnectionInitiationResponse,
    ConnectionStatusResponse,
)
from app.services.account_service import AccountService
from app.services.connection_service import ConnectionService

router = APIRouter(prefix="/composio", tags=["YouTube Integration"])


@router.post(
    "/connect/youtube",
    response_model=ConnectionInitiationResponse,
    summary="Initiate YouTube Connection",
)
def connect_youtube(
    payload: ConnectYouTubeRequest = ConnectYouTubeRequest(),
    connection_service: ConnectionService = Depends(get_connection_service),
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> ConnectionInitiationResponse:
    """Initiate an OAuth connection link for a YouTube channel.
    
    Returns a secure Composio-hosted redirect URL. The frontend should direct the
    user to this URL to authorize channel access.
    """
    try:
        return connection_service.connect_youtube(
            user_id=current_user.id,
            redirect_url=payload.redirect_url,
            force_reconnect=payload.force_reconnect,
            scopes=payload.scopes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate YouTube connection: {str(exc)}"
        )


@router.get(
    "/accounts/youtube",
    response_model=AccountListResponse,
    summary="List Connected YouTube Accounts",
)
def list_youtube_accounts(
    account_service: AccountService = Depends(get_account_service),
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> AccountListResponse:
    """Retrieve all YouTube accounts/channels connected by the authenticated user."""
    try:
        return account_service.get_user_accounts(user_id=current_user.id, toolkit="youtube")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch YouTube accounts: {str(exc)}"
        )


@router.get(
    "/connect/youtube/status",
    response_model=ConnectionStatusResponse,
    summary="Check YouTube Connection Status",
)
def check_youtube_status(
    connection_service: ConnectionService = Depends(get_connection_service),
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> ConnectionStatusResponse:
    """Verify whether the authenticated user has an active YouTube connection."""
    try:
        return connection_service.get_toolkit_status(toolkit="youtube", user_id=current_user.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify YouTube connection status: {str(exc)}"
        )

