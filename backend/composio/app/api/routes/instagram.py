"""Instagram OAuth connection and account routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import AuthenticatedUser, get_current_user, get_connection_service, get_account_service
from app.schemas.account import AccountListResponse
from app.schemas.connection import (
    ConnectInstagramRequest,
    ConnectionInitiationResponse,
    ConnectionStatusResponse,
)
from app.services.account_service import AccountService
from app.services.connection_service import ConnectionService

router = APIRouter(prefix="/composio", tags=["Instagram Integration"])


@router.post(
    "/connect/instagram",
    response_model=ConnectionInitiationResponse,
    summary="Initiate Instagram Connection",
)
def connect_instagram(
    payload: ConnectInstagramRequest = ConnectInstagramRequest(),
    connection_service: ConnectionService = Depends(get_connection_service),
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> ConnectionInitiationResponse:
    """Initiate an OAuth connection link for an Instagram Professional / Creator account.
    
    Returns a secure Composio-hosted redirect URL. The frontend should direct the
    user to this URL to grant consent.
    """
    try:
        return connection_service.connect_instagram(
            user_id=current_user.id,
            redirect_url=payload.redirect_url,
            force_reconnect=payload.force_reconnect,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Instagram connection: {str(exc)}"
        )


@router.get(
    "/accounts/instagram",
    response_model=AccountListResponse,
    summary="List Connected Instagram Accounts",
)
def list_instagram_accounts(
    account_service: AccountService = Depends(get_account_service),
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> AccountListResponse:
    """Retrieve all Instagram accounts connected by the authenticated user."""
    try:
        return account_service.get_user_accounts(user_id=current_user.id, toolkit="instagram")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Instagram accounts: {str(exc)}"
        )


@router.get(
    "/connect/instagram/status",
    response_model=ConnectionStatusResponse,
    summary="Check Instagram Connection Status",
)
def check_instagram_status(
    connection_service: ConnectionService = Depends(get_connection_service),
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> ConnectionStatusResponse:
    """Verify whether the authenticated user has an active Instagram connection."""
    try:
        return connection_service.get_toolkit_status(toolkit="instagram", user_id=current_user.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify Instagram connection status: {str(exc)}"
        )

