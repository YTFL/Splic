"""Account service orchestrating connected account management and ownership checks."""

import logging
from typing import Optional
from app.integrations.composio.connections import ConnectionManager
from app.schemas.account import (
    AccountListResponse,
    AccountDetailResponse,
    AccountDisconnectResponse,
)

logger = logging.getLogger("composio.service.account")


class AccountService:
    """Service handling account retrieval, detail queries, and disconnection."""

    def __init__(self, connection_manager: Optional[ConnectionManager] = None):
        self.connection_manager = connection_manager or ConnectionManager()

    def get_user_accounts(
        self,
        user_id: str,
        toolkit: Optional[str] = None,
        status: Optional[str] = None
    ) -> AccountListResponse:
        """Fetch all connected accounts for a given user, optionally filtered by toolkit."""
        accounts = self.connection_manager.list_connected_accounts(
            user_id=user_id,
            toolkit=toolkit,
            status=status
        )
        return AccountListResponse(
            accounts=accounts,
            total=len(accounts),
            user_id=user_id,
            toolkit_filter=toolkit,
        )

    def get_account_by_id(self, account_id: str, user_id: str) -> AccountDetailResponse:
        """Fetch a specific connected account and enforce user ownership."""
        return self.connection_manager.get_account_detail(account_id=account_id, user_id=user_id)

    def disconnect_account(self, account_id: str, user_id: str) -> AccountDisconnectResponse:
        """Disconnect and revoke an account with ownership validation."""
        success = self.connection_manager.disconnect_account(account_id=account_id, user_id=user_id)
        return AccountDisconnectResponse(
            success=success,
            account_id=account_id,
            message=f"Account '{account_id}' was successfully disconnected."
        )

