"""Live Firebase Authentication and Protected Endpoint Verification Tests.

Runs genuine, non-mocked tests against the live Firebase project configured
in the repository root .env.local file.
"""

import json
import os
import sys
import time
import unittest
import uuid
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
from tests.conftest import MockComposioClient


class TestFirebaseLiveIntegration(unittest.TestCase):
    """Live verification against genuine Firebase Admin SDK and Google Identity Toolkit."""

    @classmethod
    def setUpClass(cls):
        cls.settings = get_settings()
        cls.firebase_mgr = get_firebase_auth_manager()
        # Reset any test mock verifier to ensure live Firebase Admin SDK is tested
        cls.firebase_mgr.reset_mock_verifier()

        # Check if live credentials exist
        if not cls.settings.is_firebase_configured:
            raise unittest.SkipTest("Live Firebase credentials not configured in root .env.local.")

        # Test live network reachability to Google servers
        try:
            httpx.get("https://oauth2.googleapis.com", timeout=3.0)
        except Exception:
            raise unittest.SkipTest("External network access blocked; skipping live Firebase network tests.")

        # Initialize live Firebase Admin SDK
        try:
            cls.firebase_mgr.initialize(raise_on_error=True)
            import firebase_admin
            from firebase_admin import auth
            cls.fb_auth = auth
        except Exception as exc:
            raise unittest.SkipTest(f"Failed to initialize live Firebase Admin SDK: {exc}")

    def setUp(self):
        self.client = TestClient(app)
        # Mock only Composio tool calls (as required: do not touch Composio, focus on Firebase)
        self.client_manager = get_composio_client_manager()
        self.mock_composio = MockComposioClient()
        self.client_manager.set_mock_client(self.mock_composio)
        self.created_test_uids = []

    def tearDown(self):
        self.client_manager.reset()
        # Clean up any test users created in live Firebase
        for uid in self.created_test_uids:
            try:
                self.fb_auth.delete_user(uid)
            except Exception:
                pass

    def _create_test_user_and_acquire_id_token(self) -> tuple[str, str]:
        """Helper to create a temporary test user and acquire a genuine Firebase ID token."""
        test_uid = f"live-test-{uuid.uuid4().hex[:8]}"
        self.fb_auth.create_user(uid=test_uid, email=f"{test_uid}@example.com")
        self.created_test_uids.append(test_uid)

        # Mint custom token
        custom_token = self.fb_auth.create_custom_token(test_uid)
        if isinstance(custom_token, bytes):
            custom_token = custom_token.decode("utf-8")

        # Exchange custom token for a genuine Firebase ID token via Identity Toolkit REST API
        api_key = os.environ.get("NEXT_PUBLIC_FIREBASE_API_KEY")
        if not api_key:
            # Fallback to web config if in settings
            api_key = getattr(self.settings, "FIREBASE_WEB_API_KEY", None)

        self.assertTrue(bool(api_key), "NEXT_PUBLIC_FIREBASE_API_KEY must be configured in .env.local")

        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={api_key}"
        resp = httpx.post(url, json={"token": custom_token, "returnSecureToken": True}, timeout=10.0)
        self.assertEqual(resp.status_code, 200, f"Failed to acquire genuine ID token: {resp.text}")

        id_token = resp.json()["idToken"]
        return test_uid, id_token

    def test_live_firebase_admin_initialization(self):
        """Verify Firebase Admin SDK initialized successfully with real project ID."""
        import firebase_admin
        default_app = firebase_admin.get_app()
        self.assertIsNotNone(default_app)
        self.assertEqual(default_app.project_id, self.settings.FIREBASE_PROJECT_ID)

    def test_live_genuine_token_verification(self):
        """Verify a genuine Firebase ID token with signature, issuer, and audience validation."""
        test_uid, id_token = self._create_test_user_and_acquire_id_token()

        # Verify token using official Firebase Admin SDK directly
        decoded = self.fb_auth.verify_id_token(id_token, check_revoked=True)
        self.assertEqual(decoded["uid"], test_uid)
        self.assertEqual(decoded["aud"], self.settings.FIREBASE_PROJECT_ID)
        self.assertEqual(decoded["iss"], f"https://securetoken.google.com/{self.settings.FIREBASE_PROJECT_ID}")
        self.assertIn("exp", decoded)
        self.assertIn("auth_time", decoded)

    def test_live_fastapi_protected_endpoint_authentication(self):
        """Verify FastAPI dependency verifies genuine token and extracts authenticated UID."""
        test_uid, id_token = self._create_test_user_and_acquire_id_token()

        response = self.client.get(
            "/api/v1/composio/status",
            headers={"Authorization": f"Bearer {id_token}"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["authenticated_user_id"], test_uid)

    def test_live_identity_spoofing_prevention(self):
        """Verify client-supplied user parameters cannot override genuine Firebase UID."""
        test_uid, id_token = self._create_test_user_and_acquire_id_token()

        # Attacker attempts to pass a spoofed X-User-ID or query param
        response = self.client.get(
            "/api/v1/composio/accounts?user_id=spoofed_victim_uid",
            headers={
                "Authorization": f"Bearer {id_token}",
                "X-User-ID": "spoofed_victim_uid",
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Identity must remain strictly the verified Firebase UID
        self.assertEqual(data["user_id"], test_uid)
        self.assertNotEqual(data["user_id"], "spoofed_victim_uid")

    def test_live_missing_authorization_header(self):
        """Verify missing header is rejected with 401."""
        response = self.client.get("/api/v1/composio/status")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Authentication required", response.json()["detail"])

    def test_live_malformed_bearer_token(self):
        """Verify malformed bearer token is rejected with 401."""
        response = self.client.get(
            "/api/v1/composio/status",
            headers={"Authorization": "Bearer not.a.valid.jwt"}
        )
        self.assertEqual(response.status_code, 401)

    def test_live_invalid_signature_token(self):
        """Verify token with forged/tampered signature is rejected."""
        _, id_token = self._create_test_user_and_acquire_id_token()
        # Tamper with the signature bytes at the end of the JWT
        parts = id_token.split(".")
        tampered_token = f"{parts[0]}.{parts[1]}.tampered_signature_payload"

        response = self.client.get(
            "/api/v1/composio/status",
            headers={"Authorization": f"Bearer {tampered_token}"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid Firebase ID token", response.json()["detail"])

    def test_live_revoked_token_rejection(self):
        """Verify that revoked Firebase tokens are strictly rejected when check_revoked=True."""
        test_uid, id_token = self._create_test_user_and_acquire_id_token()

        # Verify it works initially
        initial_resp = self.client.get(
            "/api/v1/composio/status",
            headers={"Authorization": f"Bearer {id_token}"}
        )
        self.assertEqual(initial_resp.status_code, 200)

        # Revoke tokens for the user in Firebase Auth
        self.fb_auth.revoke_refresh_tokens(test_uid)
        time.sleep(1)  # Clock boundary

        # Call endpoint with check_revoked=True
        revoked_resp = self.client.get(
            "/api/v1/composio/status",
            headers={"Authorization": f"Bearer {id_token}"}
        )
        self.assertEqual(revoked_resp.status_code, 401)
        self.assertIn("revoked", revoked_resp.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()

