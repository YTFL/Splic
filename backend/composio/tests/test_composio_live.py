"""Live and integration verification tests for Composio in Splic.

Tests Composio SDK initialization, live API connectivity, multi-user isolation,
action allowlists, and credential sanitization.
"""

import os
import sys
import unittest
import httpx
from starlette.testclient import TestClient

# Ensure backend/composio is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.config import get_settings
from app.main import app
from app.auth.firebase import get_firebase_auth_manager
from app.integrations.composio.client import get_composio_client_manager
from tests.conftest import MockComposioClient, mock_firebase_token_verifier


class TestComposioIntegrationAndLive(unittest.TestCase):
    """Composio SDK lifecycle, live API connectivity, and isolation verification."""

    def setUp(self):
        self.settings = get_settings()
        self.client = TestClient(app)
        self.client_manager = get_composio_client_manager()
        self.firebase_mgr = get_firebase_auth_manager()
        self.firebase_mgr.set_mock_verifier(mock_firebase_token_verifier)

    def tearDown(self):
        self.client_manager.reset()
        self.firebase_mgr.reset_mock_verifier()

    def test_composio_sdk_installed_and_version(self):
        """Verify Composio SDK package is installed and matches modern version."""
        import importlib.metadata
        try:
            ver = importlib.metadata.version("composio")
        except Exception:
            ver = importlib.metadata.version("composio-core")
        self.assertTrue(bool(ver), "Composio package must be installed.")
        from composio import Composio
        self.assertIsNotNone(Composio)

    def test_composio_client_initialization_with_env_key(self):
        """Verify Composio client initializes from root .env.local without errors."""
        self.client_manager.reset()
        client = self.client_manager.get_client()
        self.assertIsNotNone(client)
        from composio import Composio
        self.assertIsInstance(client, Composio)

        health = self.client_manager.get_health_status()
        self.assertTrue(health["sdk_installed"])
        self.assertTrue(health["is_configured"])
        self.assertIsNone(health["error"])
        # Ensure static shared identity is removed
        self.assertNotIn("default_user_id", health)

    def test_env_resolution_and_key_exact_delivery(self):
        """Verify .env.local path resolution and exact credential delivery to SDK."""
        from dotenv import dotenv_values
        from pathlib import Path
        root_path = Path(self.settings.root_env_file)
        self.assertTrue(root_path.is_file())
        self.assertEqual(root_path.name, ".env.local")

        # Compare directly with raw file content to confirm no truncation or corruption
        raw_vals = dotenv_values(root_path)
        raw_key = raw_vals.get("COMPOSIO_API_KEY")
        self.assertIsNotNone(raw_key)
        self.assertEqual(self.settings.COMPOSIO_API_KEY, raw_key)

        # Confirm Composio client receives the exact key unaltered
        self.client_manager.reset()
        client = self.client_manager.get_client()
        self.assertEqual(client.client._auth.credential, self.settings.COMPOSIO_API_KEY)

    def test_static_user_id_completely_removed(self):
        """Verify COMPOSIO_USER_ID is completely removed from Settings and dependencies."""
        self.assertFalse(hasattr(self.settings, "COMPOSIO_USER_ID"))
        health = self.client_manager.get_health_status()
        self.assertNotIn("default_user_id", health)

    def test_live_authentication_and_toolkit_discovery(self):
        """Confirm that live authentication against Composio returns 200 OK and discovers toolkits."""
        try:
            httpx.get("https://backend.composio.dev", timeout=3.0)
        except Exception:
            raise unittest.SkipTest("External network access blocked; skipping live Composio network call.")

        url = "https://backend.composio.dev/api/v3.1/toolkits"
        resp = httpx.get(url, headers={"x-api-key": self.settings.COMPOSIO_API_KEY}, params={"limit": 5}, timeout=10.0)
        self.assertEqual(resp.status_code, 200)
        resp_json = resp.json()
        items = resp_json.get("items", [])
        self.assertGreater(len(items), 0)
        slugs = [item.get("slug") for item in items]
        self.assertTrue(any(s for s in slugs if s))

    def test_composio_live_api_connectivity_and_oauth_initiation(self):
        """Perform genuine live calls to Composio for SDK toolkit listing and OAuth link generation."""
        self.client_manager.reset()
        client = self.client_manager.get_client()

        try:
            httpx.get("https://backend.composio.dev", timeout=3.0)
        except Exception:
            raise unittest.SkipTest("External network access blocked; skipping live Composio network call.")

        # Test live toolkit listing via SDK
        toolkits = client.toolkits.list(limit=5)
        self.assertIsNotNone(toolkits)
        items = getattr(toolkits, "items", toolkits)
        self.assertGreater(len(items), 0)

        # Test live OAuth initiation without completing OAuth
        from app.integrations.composio.connections import ConnectionManager
        cm = ConnectionManager()
        test_uid = "firebase_live_test_user_verify"
        for tk in ["instagram", "youtube"]:
            init_res = cm.initiate_connection(toolkit=tk, user_id=test_uid)
            self.assertEqual(init_res.status, "INITIATED")
            self.assertEqual(init_res.user_id, test_uid)
            self.assertTrue(init_res.redirect_url.startswith("https://"))

    def test_firebase_uid_mapping_and_isolation(self):
        """Verify multi-tenant isolation: Creator A and Creator B have strictly isolated sessions."""
        mock = MockComposioClient()
        self.client_manager.set_mock_client(mock)

        creator_a = "firebase_creator_alpha_uid"
        creator_b = "firebase_creator_beta_uid"

        # Creator A initiates Instagram connection
        res_a = self.client.post(
            "/api/v1/composio/connect/instagram",
            json={"redirect_url": "http://localhost:3000/callback"},
            headers={"Authorization": f"Bearer {creator_a}"}
        )
        self.assertEqual(res_a.status_code, 200)
        data_a = res_a.json()
        self.assertEqual(data_a["user_id"], creator_a)

        # Creator B initiates YouTube connection
        res_b = self.client.post(
            "/api/v1/composio/connect/youtube",
            json={"redirect_url": "http://localhost:3000/callback"},
            headers={"Authorization": f"Bearer {creator_b}"}
        )
        self.assertEqual(res_b.status_code, 200)
        data_b = res_b.json()
        self.assertEqual(data_b["user_id"], creator_b)

        # Creator A lists accounts -> sees only their accounts
        accs_a = self.client.get(
            "/api/v1/composio/accounts",
            headers={"Authorization": f"Bearer {creator_a}"}
        ).json()
        self.assertEqual(accs_a["user_id"], creator_a)

        # Creator B cannot access Creator A's account details
        forbidden_get = self.client.get(
            "/api/v1/composio/accounts/ca_insta_01",
            headers={"Authorization": f"Bearer {creator_b}"}
        )
        self.assertEqual(forbidden_get.status_code, 403)

        # Creator B cannot disconnect Creator A's account
        forbidden_del = self.client.delete(
            "/api/v1/composio/accounts/ca_insta_01",
            headers={"Authorization": f"Bearer {creator_b}"}
        )
        self.assertEqual(forbidden_del.status_code, 403)

    def test_read_only_allowlist_and_mutation_blocking(self):
        """Verify read-only actions are permitted while publishing and uploads are strictly blocked."""
        mock = MockComposioClient()
        self.client_manager.set_mock_client(mock)
        uid = "firebase_creator_safe_uid"

        # Permitted read-only action: INSTAGRAM_GET_USER_INFO
        res_read = self.client.post(
            "/api/v1/composio/execute",
            json={"action_slug": "INSTAGRAM_GET_USER_INFO", "parameters": {}},
            headers={"Authorization": f"Bearer {uid}"}
        )
        self.assertEqual(res_read.status_code, 200)
        self.assertTrue(res_read.json()["success"])

        # Permitted read-only action: YOUTUBE_LIST_MY_CHANNELS
        res_yt_read = self.client.post(
            "/api/v1/composio/execute",
            json={"action_slug": "YOUTUBE_LIST_MY_CHANNELS", "parameters": {}},
            headers={"Authorization": f"Bearer {uid}"}
        )
        self.assertEqual(res_yt_read.status_code, 200)
        self.assertTrue(res_yt_read.json()["success"])

        # Blocked mutating action: INSTAGRAM_CREATE_POST (403)
        res_insta_post = self.client.post(
            "/api/v1/composio/execute",
            json={"action_slug": "INSTAGRAM_CREATE_POST", "parameters": {"caption": "Test"}},
            headers={"Authorization": f"Bearer {uid}"}
        )
        self.assertEqual(res_insta_post.status_code, 403)
        self.assertIn("BLOCKED", res_insta_post.json()["detail"])

        # Blocked mutating action: YOUTUBE_UPLOAD_VIDEO (403)
        res_yt_upload = self.client.post(
            "/api/v1/composio/execute",
            json={"action_slug": "YOUTUBE_UPLOAD_VIDEO", "parameters": {"title": "Test"}},
            headers={"Authorization": f"Bearer {uid}"}
        )
        self.assertEqual(res_yt_upload.status_code, 403)
        self.assertIn("BLOCKED", res_yt_upload.json()["detail"])

    def test_secret_sanitization(self):
        """Verify private keys, tokens, and service account contents are never returned."""
        uid = "firebase_creator_safe_uid"
        res = self.client.get(
            "/api/v1/composio/status",
            headers={"Authorization": f"Bearer {uid}"}
        )
        self.assertEqual(res.status_code, 200)
        body_str = res.text
        self.assertNotIn("COMPOSIO_API_KEY", body_str)
        self.assertNotIn("FIREBASE_SERVICE_ACCOUNT_JSON", body_str)
        self.assertNotIn("private_key", body_str)
        if self.settings.COMPOSIO_API_KEY:
            self.assertNotIn(self.settings.COMPOSIO_API_KEY, body_str)


if __name__ == "__main__":
    unittest.main()

