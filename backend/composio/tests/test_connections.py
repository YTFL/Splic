"""Tests for Instagram and YouTube OAuth connection initiation, account listing, and ownership enforcement."""

import os
import sys
import unittest

# Ensure backend/composio is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from starlette.testclient import TestClient
from app.main import app
from app.auth.firebase import get_firebase_auth_manager
from app.integrations.composio.client import get_composio_client_manager
from tests.conftest import MockComposioClient, mock_firebase_token_verifier


class TestConnectionFlows(unittest.TestCase):
    """Test suite for social connections and account security."""

    def setUp(self):
        self.client = TestClient(app)
        self.client_manager = get_composio_client_manager()
        self.mock_composio = MockComposioClient()
        self.client_manager.set_mock_client(self.mock_composio)
        self.firebase_mgr = get_firebase_auth_manager()
        self.firebase_mgr.set_mock_verifier(mock_firebase_token_verifier)

    def tearDown(self):
        self.client_manager.reset()
        self.firebase_mgr.reset_mock_verifier()

    def test_initiate_instagram_connection(self):
        """Verify initiating Instagram OAuth returns a valid redirect URL."""
        payload = {
            "redirect_url": "http://localhost:5173/auth/callback/instagram",
            "force_reconnect": True,
        }
        response = self.client.post(
            "/api/v1/composio/connect/instagram",
            json=payload,
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["toolkit"], "instagram")
        self.assertIn("https://connect.composio.dev", data["redirect_url"])
        self.assertIn("connection_request_id", data)
        self.assertEqual(data["status"], "INITIATED")

    def test_initiate_youtube_connection(self):
        """Verify initiating YouTube OAuth returns a valid redirect URL."""
        payload = {
            "redirect_url": "http://localhost:5173/auth/callback/youtube",
            "scopes": ["https://www.googleapis.com/auth/youtube.readonly"],
        }
        response = self.client.post(
            "/api/v1/composio/connect/youtube",
            json=payload,
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["toolkit"], "youtube")
        self.assertIn("https://connect.composio.dev", data["redirect_url"])

    def test_list_all_accounts_for_user(self):
        """Verify listing all connected accounts for the current user."""
        response = self.client.get(
            "/api/v1/composio/accounts",
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["user_id"], "test_user")
        self.assertEqual(data["total"], 2)
        toolkits = [acc["toolkit"] for acc in data["accounts"]]
        self.assertIn("instagram", toolkits)
        self.assertIn("youtube", toolkits)

    def test_filter_accounts_by_toolkit(self):
        """Verify dedicated Instagram and YouTube accounts endpoints."""
        # Instagram dedicated route
        insta_res = self.client.get(
            "/api/v1/composio/accounts/instagram",
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(insta_res.status_code, 200)
        insta_data = insta_res.json()
        self.assertEqual(insta_data["total"], 1)
        self.assertEqual(insta_data["accounts"][0]["toolkit"], "instagram")

        # YouTube dedicated route
        yt_res = self.client.get(
            "/api/v1/composio/accounts/youtube",
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(yt_res.status_code, 200)
        yt_data = yt_res.json()
        self.assertEqual(yt_data["total"], 1)
        self.assertEqual(yt_data["accounts"][0]["toolkit"], "youtube")

    def test_security_sensitive_tokens_are_stripped(self):
        """Verify that access tokens and client secrets are stripped from responses."""
        response = self.client.get(
            "/api/v1/composio/accounts/ca_insta_01",
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        meta = data.get("metadata", {})

        # Ensure no token leaks
        for key in meta:
            self.assertNotIn("token", key.lower())
            self.assertNotIn("secret", key.lower())
            self.assertNotIn("password", key.lower())

    def test_ownership_validation_get_account(self):
        """Verify that a user cannot access an account belonging to another user (403 Forbidden)."""
        # test_user attempts to access ca_other_user
        response = self.client.get(
            "/api/v1/composio/accounts/ca_other_user",
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("does not belong to user", response.json()["detail"])

    def test_get_nonexistent_account_returns_404(self):
        """Verify that requesting a missing account ID returns 404."""
        response = self.client.get(
            "/api/v1/composio/accounts/ca_nonexistent_999",
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(response.status_code, 404)

    def test_ownership_validation_disconnect_account(self):
        """Verify that a user cannot disconnect another user's account (403 Forbidden)."""
        response = self.client.delete(
            "/api/v1/composio/accounts/ca_other_user",
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(response.status_code, 403)

    def test_disconnect_own_account_succeeds(self):
        """Verify disconnecting a user's own account succeeds."""
        response = self.client.delete(
            "/api/v1/composio/accounts/ca_insta_01",
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["account_id"], "ca_insta_01")

    def test_connection_status_checks(self):
        """Verify checking connection status returns correct active state."""
        insta_status = self.client.get(
            "/api/v1/composio/connect/instagram/status",
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(insta_status.status_code, 200)
        self.assertTrue(insta_status.json()["is_active"])

        # Status for user with no accounts
        empty_status = self.client.get(
            "/api/v1/composio/connect/instagram/status",
            headers={"Authorization": "Bearer new_user_without_accounts"}
        )
        self.assertEqual(empty_status.status_code, 200)
        self.assertFalse(empty_status.json()["is_active"])


if __name__ == "__main__":
    unittest.main()

