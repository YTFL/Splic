"""Tests for Composio configuration, toolkit discovery, and controlled execution."""

import os
import sys
import unittest

# Ensure backend/composio is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from starlette.testclient import TestClient
from app.main import app
from app.config import Settings
from app.auth.firebase import get_firebase_auth_manager
from app.integrations.composio.client import get_composio_client_manager
from tests.conftest import MockComposioClient, mock_firebase_token_verifier


class TestComposioCore(unittest.TestCase):
    """Test suite for Composio initialization, toolkits, actions, and execution safety."""

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

    def test_settings_cors_and_validation(self):
        """Test configuration origin parsing and key validation."""
        s = Settings(
            COMPOSIO_API_KEY="test_valid_key_12345",
            FRONTEND_URL="http://localhost:5173, https://app.splic.studio",
        )
        self.assertTrue(s.is_composio_configured)
        self.assertEqual(len(s.cors_origins), 2)
        self.assertIn("http://localhost:5173", s.cors_origins)
        self.assertIn("https://app.splic.studio", s.cors_origins)

        # Unconfigured key
        s_unconf = Settings(COMPOSIO_API_KEY=None)
        self.assertFalse(s_unconf.is_composio_configured)

    def test_root_env_path_resolution(self):
        """Verify that root .env.local path resolves to project root deterministically."""
        s = Settings()
        self.assertEqual(s.root_env_file.name, ".env.local")
        self.assertEqual(s.root_env_file.parent.name, "Splic")
        # Ensure path is absolute
        self.assertTrue(s.root_env_file.is_absolute())

    def test_missing_required_variables_produce_clean_errors(self):
        """Verify that unconfigured credentials produce clean errors without secrets."""
        s_unconf = Settings(COMPOSIO_API_KEY=None)
        with self.assertRaises(ValueError) as ctx:
            s_unconf.validate_composio_credentials()
        error_msg = str(ctx.exception)
        self.assertIn("COMPOSIO_API_KEY is not configured", error_msg)
        self.assertIn(".env.local", error_msg)
        self.assertNotIn("secret", error_msg.lower())

        s_no_fb = Settings(FIREBASE_PROJECT_ID="")
        with self.assertRaises(ValueError) as ctx_fb:
            s_no_fb.validate_firebase_credentials()
        fb_msg = str(ctx_fb.exception)
        self.assertIn("FIREBASE_PROJECT_ID is not configured", fb_msg)
        self.assertIn(".env.local", fb_msg)

    def test_composio_status_endpoint(self):
        """Verify GET /api/v1/composio/status returns configuration details."""
        response = self.client.get(
            "/api/v1/composio/status",
            headers={"Authorization": "Bearer test_creator_99"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["authenticated_user_id"], "test_creator_99")
        self.assertIn("composio", data)

    def test_list_toolkits(self):
        """Verify GET /api/v1/composio/toolkits lists Instagram and YouTube."""
        response = self.client.get(
            "/api/v1/composio/toolkits",
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(response.status_code, 200)
        toolkits = response.json()
        slugs = [tk["slug"] for tk in toolkits]
        self.assertIn("instagram", slugs)
        self.assertIn("youtube", slugs)

    def test_discover_instagram_actions(self):
        """Verify action discovery and allowlist marking for Instagram."""
        response = self.client.get(
            "/api/v1/composio/actions/instagram",
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(response.status_code, 200)
        actions = response.json()
        slugs = [a["slug"] for a in actions]
        self.assertIn("INSTAGRAM_GET_USER_INFO", slugs)
        self.assertIn("INSTAGRAM_CREATE_POST", slugs)

        # Check permissions marking
        for a in actions:
            if a["slug"] == "INSTAGRAM_GET_USER_INFO":
                self.assertTrue(a["is_allowed"])
                self.assertTrue(a["is_read_only"])
            elif a["slug"] == "INSTAGRAM_CREATE_POST":
                self.assertFalse(a["is_allowed"])
                self.assertFalse(a["is_read_only"])

    def test_discover_youtube_actions(self):
        """Verify action discovery and allowlist marking for YouTube."""
        response = self.client.get(
            "/api/v1/composio/actions/youtube",
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(response.status_code, 200)
        actions = response.json()
        slugs = [a["slug"] for a in actions]
        self.assertIn("YOUTUBE_LIST_MY_CHANNELS", slugs)
        self.assertIn("YOUTUBE_UPLOAD_VIDEO", slugs)

        # Check permissions marking
        for a in actions:
            if a["slug"] == "YOUTUBE_LIST_MY_CHANNELS":
                self.assertTrue(a["is_allowed"])
            elif a["slug"] == "YOUTUBE_UPLOAD_VIDEO":
                self.assertFalse(a["is_allowed"])

    def test_discover_unknown_toolkit_returns_404(self):
        """Verify requesting an unsupported toolkit returns 404."""
        response = self.client.get(
            "/api/v1/composio/actions/nonexistent_toolkit",
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(response.status_code, 404)

    def test_controlled_execution_allowed_action(self):
        """Verify executing an allowlisted read-only action succeeds."""
        payload = {
            "action_slug": "INSTAGRAM_GET_USER_INFO",
            "parameters": {"fields": "id,username"},
        }
        response = self.client.post(
            "/api/v1/composio/execute",
            json=payload,
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["action_slug"], "INSTAGRAM_GET_USER_INFO")

    def test_controlled_execution_blocked_publishing_action(self):
        """Verify that attempting to publish or mutate content is strictly blocked (403 Forbidden)."""
        payload = {
            "action_slug": "INSTAGRAM_CREATE_POST",
            "parameters": {"caption": "Hello world"},
        }
        response = self.client.post(
            "/api/v1/composio/execute",
            json=payload,
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("BLOCKED", response.json()["detail"])

        # Also test YouTube upload
        yt_payload = {
            "action_slug": "YOUTUBE_UPLOAD_VIDEO",
            "parameters": {"title": "Test Video"},
        }
        yt_response = self.client.post(
            "/api/v1/composio/execute",
            json=yt_payload,
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(yt_response.status_code, 403)

    def test_controlled_execution_non_allowlisted_action(self):
        """Verify that unverified actions not on the allowlist are rejected."""
        payload = {
            "action_slug": "SOME_UNKNOWN_ACTION",
            "parameters": {},
        }
        response = self.client.post(
            "/api/v1/composio/execute",
            json=payload,
            headers={"Authorization": "Bearer test_user"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("allowlist", response.json()["detail"])
        self.assertEqual(response.status_code, 403)
        self.assertIn("allowlist", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()

