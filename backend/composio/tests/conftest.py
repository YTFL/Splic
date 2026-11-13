"""Pytest configuration and Mock Composio client fixtures."""

import os
import sys
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

try:
    import pytest
except ImportError:
    pytest = None
from starlette.testclient import TestClient

# Ensure app path is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.config import get_settings
from app.main import app
from app.auth.firebase import get_firebase_auth_manager
from app.integrations.composio.client import get_composio_client_manager
from fastapi import HTTPException, status


def mock_firebase_token_verifier(token: str, check_revoked: bool = True) -> Dict[str, Any]:
    """Mock verifier simulating Firebase ID token verification offline."""
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty or missing Firebase authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if token == "invalid_token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase ID token.",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )
    if token == "expired_token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token has expired. Please refresh your token.",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="Token expired"'},
        )
    if token == "revoked_token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token has been revoked. Please sign in again.",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="Token revoked"'},
        )

    # For valid tokens in tests, extract UID
    uid = token.replace("token_for_", "")
    return {
        "uid": uid,
        "email": f"{uid}@splic.studio",
        "auth_time": 1700000000,
        "is_dev": False,
    }


class MockConnectedAccount:
    """Mock object simulating a Composio ConnectedAccount."""

    def __init__(
        self,
        account_id: str,
        toolkit: str,
        user_id: str,
        status: str = "ACTIVE",
        account_name: Optional[str] = None,
        account_handle: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = account_id
        self.toolkit = MagicMock(slug=toolkit)
        self.user_id = user_id
        self.status = status
        self.account_name = account_name or f"{toolkit.capitalize()} User"
        self.account_handle = account_handle or f"@{toolkit}_creator"
        self.created_at = "2026-11-13T12:00:00Z"
        self.metadata = metadata or {"safe_field": "public_value"}


class MockConnectionRequest:
    """Mock connection request with authorization redirect URL."""

    def __init__(self, request_id: str, redirect_url: str):
        self.id = request_id
        self.redirect_url = redirect_url

    def wait_for_connection(self, timeout: int = 60):
        return MockConnectedAccount(
            account_id="ca_mock_123",
            toolkit="instagram",
            user_id="test_user"
        )


class MockConnectedAccountsResource:
    """Mock resource simulating composio.connected_accounts."""

    def __init__(self):
        self._accounts: Dict[str, MockConnectedAccount] = {
            "ca_insta_01": MockConnectedAccount(
                account_id="ca_insta_01",
                toolkit="instagram",
                user_id="test_user",
                status="ACTIVE",
                account_name="Food Reels",
                account_handle="@foodreels",
                metadata={"follower_count": 125000, "access_token": "SENSITIVE_SHOULD_BE_STRIPPED"},
            ),
            "ca_yt_01": MockConnectedAccount(
                account_id="ca_yt_01",
                toolkit="youtube",
                user_id="test_user",
                status="ACTIVE",
                account_name="Tech In Hinglish",
                account_handle="@techinhinglish",
                metadata={"subscriber_count": 450000, "client_secret": "SENSITIVE_SHOULD_BE_STRIPPED"},
            ),
            "ca_other_user": MockConnectedAccount(
                account_id="ca_other_user",
                toolkit="instagram",
                user_id="other_unauthorized_user",
                status="ACTIVE",
                account_name="Other Channel",
                account_handle="@other_channel",
            ),
        }

    def link(self, user_id: str, toolkit: Optional[str] = None, auth_config_id: Optional[str] = None, **kwargs):
        tk = toolkit or auth_config_id or "unknown"
        return MockConnectionRequest(
            request_id=f"req_{tk}_123",
            redirect_url=f"https://connect.composio.dev/link/{tk}?session=mock_session_123"
        )

    def list(self, user_ids: Optional[List[str]] = None, statuses: Optional[List[str]] = None):
        res = list(self._accounts.values())
        if user_ids:
            res = [acc for acc in res if acc.user_id in user_ids]
        if statuses:
            res = [acc for acc in res if acc.status in statuses]
        return res

    def get(self, account_id: str):
        if account_id in self._accounts:
            return self._accounts[account_id]
        raise KeyError(f"Connected account '{account_id}' not found.")

    def delete(self, account_id: str):
        if account_id in self._accounts:
            del self._accounts[account_id]
            return True
        raise KeyError(f"Connected account '{account_id}' not found.")


class MockToolsResource:
    """Mock resource simulating composio.tools."""

    def execute(self, slug: str, arguments: Dict[str, Any], user_id: str, **kwargs):
        return {
            "action": slug,
            "user_id": user_id,
            "status": "success",
            "mock_result": {"info": f"Executed {slug} successfully", "args": arguments},
        }


class MockComposioClient:
    """Simulated Composio SDK client for offline automated testing."""

    def __init__(self):
        self.connected_accounts = MockConnectedAccountsResource()
        self.tools = MockToolsResource()

    def create(self, user_id: str, toolkits: Optional[List[str]] = None):
        """Simulate session creation."""
        mock_session = MagicMock()
        mock_session.authorize = lambda tk, **kw: MockConnectionRequest(
            request_id=f"req_{tk}_session",
            redirect_url=f"https://connect.composio.dev/link/{tk}?session=mock_sess_abc"
        )
        return mock_session


if pytest is not None:
    @pytest.fixture
    def mock_composio_client():
        """Fixture providing a configured mock client."""
        client = MockComposioClient()
        manager = get_composio_client_manager()
        manager.set_mock_client(client)
        yield client
        manager.reset()

    @pytest.fixture
    def test_client(mock_composio_client):
        """Fixture providing Starlette TestClient with mock Composio initialized."""
        with TestClient(app) as client:
            yield client
