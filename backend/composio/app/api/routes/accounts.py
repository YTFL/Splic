"""User account management routes (list, details, disconnect)."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.dependencies import AuthenticatedUser, get_current_user, get_account_service
from app.schemas.account import (
    AccountListResponse,
    AccountDetailResponse,
    AccountDisconnectResponse,
)
from app.services.account_service import AccountService

router = APIRouter(prefix="/composio/accounts", tags=["Account Management"])


@router.get("", response_model=AccountListResponse, summary="List All Connected Accounts")
def list_all_accounts(
    toolkit: Optional[str] = Query(None, description="Optional filter by toolkit (e.g. 'instagram', 'youtube')"),
    status_filter: Optional[str] = Query(None, alias="status", description="Optional filter by status (e.g. 'ACTIVE')"),
    account_service: AccountService = Depends(get_account_service),
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> AccountListResponse:
    """Retrieve all social media accounts connected by the authenticated user across all toolkits."""
    try:
        return account_service.get_user_accounts(
            user_id=current_user.id,
            toolkit=toolkit,
            status=status_filter,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch connected accounts: {str(exc)}"
        )


@router.get("/{account_id}", response_model=AccountDetailResponse, summary="Get Account Details")
def get_account_details(
    account_id: str,
    account_service: AccountService = Depends(get_account_service),
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> AccountDetailResponse:
    """Retrieve sanitized details for a specific connected account.
    
    Security: Strictly verifies that the requested account belongs to the current user.
    """
    try:
        return account_service.get_account_by_id(account_id=account_id, user_id=current_user.id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving account {account_id}: {str(exc)}"
        )


@router.delete("/{account_id}", response_model=AccountDisconnectResponse, summary="Disconnect Account")
def disconnect_account(
    account_id: str,
    account_service: AccountService = Depends(get_account_service),
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> AccountDisconnectResponse:
    """Disconnect and revoke access for a connected account.
    
    Security: Enforces ownership before performing disconnection.
    """
    try:
        return account_service.disconnect_account(account_id=account_id, user_id=current_user.id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect account {account_id}: {str(exc)}"
        )

