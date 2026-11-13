"""Dedicated tests for Firebase Authentication in Splic Composio Backend."""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure backend/composio is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from starlette.testclient import TestClient
from app.main import app
from app.config import Settings, ROOT_ENV_LOCAL_PATH
from app.auth.firebase import (
    get_firebase_auth_manager,
    FirebaseAuthManager,
    verify_firebase_id_token,
)
from app.integrations.composio.client import get_composio_client_manager
from tests.conftest import MockComposioClient, mock_firebase_token_verifier


class TestFirebaseAuth(unittest.TestCase):
    """Test suite covering Firebase ID token verification, multi-tenant UID mapping, and edge cases."""

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

    def test_missing_authorization_header_returns_401(self):
        """Verify requests without Authorization header are rejected with 401."""
        response = self.client.get("/api/v1/composio/accounts")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Authentication required", response.json()["detail"])
        self.assertIn("WWW-Authenticate", response.headers)

    def test_invalid_header_scheme_returns_401(self):
        """Verify non-Bearer schemes (e.g. Basic, Token) return 401."""
        response = self.client.get(
            "/api/v1/composio/accounts",
            headers={"Authorization": "Basic dXNlcjpwYXNz"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("Expected 'Bearer <FIREBASE_ID_TOKEN>'", response.json()["detail"])

    def test_empty_bearer_token_returns_401(self):
        """Verify empty 'Bearer ' string returns 401."""
        response = self.client.get(
            "/api/v1/composio/accounts",
            headers={"Authorization": "Bearer "}
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("Missing token", response.json()["detail"])

    def test_invalid_firebase_token_returns_401(self):
        """Verify invalid Firebase ID token returns 401 with standard error header."""
        response = self.client.get(
            "/api/v1/composio/accounts",
            headers={"Authorization": "Bearer invalid_token"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid Firebase ID token", response.json()["detail"])

    def test_expired_firebase_token_returns_401(self):
        """Verify expired Firebase ID token returns 401 with token expired message."""
        response = self.client.get(
            "/api/v1/composio/accounts",
            headers={"Authorization": "Bearer expired_token"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("expired", response.json()["detail"])

    def test_revoked_firebase_token_returns_401(self):
        """Verify revoked Firebase ID token returns 401 with token revoked message."""
        response = self.client.get(
            "/api/v1/composio/accounts",
            headers={"Authorization": "Bearer revoked_token"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("revoked", response.json()["detail"])

    def test_successful_token_verification_extracts_uid(self):
        """Verify valid Firebase token resolves UID and allows account access."""
        firebase_uid = "fb_creator_verified_77"
        response = self.client.get(
            "/api/v1/composio/status",
            headers={"Authorization": f"Bearer {firebase_uid}"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["authenticated_user_id"], firebase_uid)

    def test_different_firebase_users_receive_distinct_identities(self):
        """Verify multi-tenant isolation: user A and user B get independent identities."""
        user_a = "fb_user_alpha"
        user_b = "fb_user_beta"

        res_a = self.client.get(
            "/api/v1/composio/accounts",
            headers={"Authorization": f"Bearer {user_a}"}
        )
        self.assertEqual(res_a.status_code, 200)
        self.assertEqual(res_a.json()["user_id"], user_a)

        res_b = self.client.get(
            "/api/v1/composio/accounts",
            headers={"Authorization": f"Bearer {user_b}"}
        )
        self.assertEqual(res_b.status_code, 200)
        self.assertEqual(res_b.json()["user_id"], user_b)
        self.assertNotEqual(res_a.json()["user_id"], res_b.json()["user_id"])

    def test_cross_tenant_ownership_enforcement(self):
        """Verify that user_b cannot access an account belonging to user_a."""
        # ca_insta_01 belongs to test_user
        res_forbidden = self.client.get(
            "/api/v1/composio/accounts/ca_insta_01",
            headers={"Authorization": "Bearer attacker_firebase_uid"}
        )
        self.assertEqual(res_forbidden.status_code, 403)
        self.assertIn("does not belong to user", res_forbidden.json()["detail"])

    def test_cross_tenant_disconnection_blocked(self):
        """Verify that user_b cannot disconnect user_a's account."""
        res_disconnect = self.client.delete(
            "/api/v1/composio/accounts/ca_insta_01",
            headers={"Authorization": "Bearer unauthorized_uid"}
        )
        self.assertEqual(res_disconnect.status_code, 403)

    def test_instagram_oauth_initiation_uses_firebase_uid(self):
        """Verify Instagram connection initiation binds to the verified Firebase UID."""
        custom_uid = "firebase_desi_creator_01"
        payload = {"redirect_url": "http://localhost:3000/auth/callback"}
        response = self.client.post(
            "/api/v1/composio/connect/instagram",
            json=payload,
            headers={"Authorization": f"Bearer {custom_uid}"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["user_id"], custom_uid)
        self.assertEqual(data["toolkit"], "instagram")

    def test_youtube_oauth_initiation_uses_firebase_uid(self):
        """Verify YouTube connection initiation binds to the verified Firebase UID."""
        custom_uid = "firebase_desi_creator_02"
        payload = {"redirect_url": "http://localhost:3000/auth/callback"}
        response = self.client.post(
            "/api/v1/composio/connect/youtube",
            json=payload,
            headers={"Authorization": f"Bearer {custom_uid}"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["user_id"], custom_uid)
        self.assertEqual(data["toolkit"], "youtube")

    def test_action_execution_uses_firebase_uid(self):
        """Verify action execution binds to the verified Firebase UID."""
        custom_uid = "firebase_desi_creator_03"
        payload = {
            "action_slug": "INSTAGRAM_GET_USER_INFO",
            "parameters": {"fields": "id,username"},
        }
        response = self.client.post(
            "/api/v1/composio/execute",
            json=payload,
            headers={"Authorization": f"Bearer {custom_uid}"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    def test_mutating_action_blocked_for_firebase_user(self):
        """Verify mutating action remains strictly blocked (403 Forbidden)."""
        payload = {
            "action_slug": "YOUTUBE_UPLOAD_VIDEO",
            "parameters": {"title": "New Reel"},
        }
        response = self.client.post(
            "/api/v1/composio/execute",
            json=payload,
            headers={"Authorization": "Bearer firebase_any_user"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("BLOCKED", response.json()["detail"])


class TestFirebaseAdminConfigAndInit(unittest.TestCase):
    """Test suite covering root .env.local resolution, service-account JSON parsing,
    field validation, error handling, project ID consistency, and Firebase Admin initialization."""

    def setUp(self):
        self.valid_sa_dict = {
            "type": "service_account",
            "project_id": "test-splic-proj",
            "private_key_id": "pk_12345",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n",
            "client_email": "firebase-adminsdk@test-splic-proj.iam.gserviceaccount.com",
            "client_id": "999888777",
        }
        self.valid_sa_json = json.dumps(self.valid_sa_dict)

    def test_root_env_local_resolved_independently_of_working_directory(self):
        """Verify root .env.local is resolved relative to the module file, not cwd."""
        s = Settings()
        self.assertEqual(s.root_env_file, ROOT_ENV_LOCAL_PATH)
        self.assertTrue(str(s.root_env_file).endswith(".env.local"))
        self.assertIn("Splic", str(s.root_env_file))

    def test_service_account_json_parses_and_validates_correctly(self):
        """Verify valid service account JSON parses correctly and matches project ID."""
        s = Settings(
            FIREBASE_PROJECT_ID="test-splic-proj",
            FIREBASE_SERVICE_ACCOUNT_JSON=self.valid_sa_json,
        )
        parsed = s.parse_and_validate_service_account()
        self.assertIsInstance(parsed, dict)
        self.assertEqual(parsed["project_id"], "test-splic-proj")
        self.assertEqual(parsed["client_email"], self.valid_sa_dict["client_email"])
        self.assertTrue(s.is_firebase_configured)

    def test_missing_credentials_produce_safe_errors(self):
        """Verify missing FIREBASE_SERVICE_ACCOUNT_JSON produces safe ValueError without secrets."""
        s_none = Settings(
            FIREBASE_PROJECT_ID="test-splic-proj",
            FIREBASE_SERVICE_ACCOUNT_JSON=None,
        )
        with self.assertRaises(ValueError) as ctx:
            s_none.parse_and_validate_service_account()
        self.assertIn("FIREBASE_SERVICE_ACCOUNT_JSON is not configured", str(ctx.exception))

        s_empty = Settings(
            FIREBASE_PROJECT_ID="test-splic-proj",
            FIREBASE_SERVICE_ACCOUNT_JSON="   ",
        )
        with self.assertRaises(ValueError) as ctx:
            s_empty.parse_and_validate_service_account()
        self.assertIn("FIREBASE_SERVICE_ACCOUNT_JSON is not configured", str(ctx.exception))

    def test_malformed_json_produces_safe_errors(self):
        """Verify malformed JSON produces safe error without leaking raw input string."""
        s_malformed = Settings(
            FIREBASE_PROJECT_ID="test-splic-proj",
            FIREBASE_SERVICE_ACCOUNT_JSON="{'bad_json': true,",
        )
        with self.assertRaises(ValueError) as ctx:
            s_malformed.parse_and_validate_service_account()
        self.assertIn("invalid or malformed JSON", str(ctx.exception))

        s_not_dict = Settings(
            FIREBASE_PROJECT_ID="test-splic-proj",
            FIREBASE_SERVICE_ACCOUNT_JSON='"just a string"',
        )
        with self.assertRaises(ValueError) as ctx:
            s_not_dict.parse_and_validate_service_account()
        self.assertIn("must be a valid JSON object dictionary", str(ctx.exception))

    def test_missing_required_fields_produce_safe_errors(self):
        """Verify missing required service account fields are reported safely."""
        incomplete_dict = {"type": "service_account", "project_id": "test-splic-proj"}
        s_incomplete = Settings(
            FIREBASE_PROJECT_ID="test-splic-proj",
            FIREBASE_SERVICE_ACCOUNT_JSON=json.dumps(incomplete_dict),
        )
        with self.assertRaises(ValueError) as ctx:
            s_incomplete.parse_and_validate_service_account()
        self.assertIn("missing required fields", str(ctx.exception))
        self.assertIn("private_key", str(ctx.exception))
        self.assertIn("client_email", str(ctx.exception))

    def test_missing_firebase_project_id_fails(self):
        """Verify missing FIREBASE_PROJECT_ID fails without silent fallback to splic-app."""
        s_no_pid = Settings(
            FIREBASE_PROJECT_ID=None,
            FIREBASE_SERVICE_ACCOUNT_JSON=self.valid_sa_json,
        )
        with self.assertRaises(ValueError) as ctx:
            s_no_pid.parse_and_validate_service_account()
        self.assertIn("FIREBASE_PROJECT_ID is not configured", str(ctx.exception))

    def test_mismatched_project_ids_are_rejected(self):
        """Verify mismatch between FIREBASE_PROJECT_ID and JSON project_id is rejected."""
        s_mismatch = Settings(
            FIREBASE_PROJECT_ID="expected-project-id",
            FIREBASE_SERVICE_ACCOUNT_JSON=self.valid_sa_json,  # Contains "test-splic-proj"
        )
        with self.assertRaises(ValueError) as ctx:
            s_mismatch.parse_and_validate_service_account()
        self.assertIn("does not match", str(ctx.exception))
        self.assertIn("expected-project-id", str(ctx.exception))
        self.assertIn("test-splic-proj", str(ctx.exception))

    @patch("firebase_admin.credentials.Certificate")
    @patch("firebase_admin.initialize_app")
    @patch("firebase_admin.get_app")
    def test_firebase_admin_initialization_with_mocked_credentials(
        self, mock_get_app, mock_init_app, mock_cert
    ):
        """Verify Firebase Admin initialization passes parsed dictionary to Certificate."""
        mock_get_app.side_effect = ValueError("No app initialized")
        mock_cert_obj = MagicMock()
        mock_cert.return_value = mock_cert_obj
        mock_app_instance = MagicMock()
        mock_init_app.return_value = mock_app_instance

        s = Settings(
            FIREBASE_PROJECT_ID="test-splic-proj",
            FIREBASE_SERVICE_ACCOUNT_JSON=self.valid_sa_json,
        )
        auth_mgr = FirebaseAuthManager(settings=s)
        auth_mgr.initialize(raise_on_error=True)

        mock_cert.assert_called_once()
        called_arg = mock_cert.call_args[0][0]
        self.assertEqual(called_arg["project_id"], "test-splic-proj")
        mock_init_app.assert_called_once_with(mock_cert_obj, options={"projectId": "test-splic-proj"})
        self.assertTrue(auth_mgr._is_initialized)


if __name__ == "__main__":
    unittest.main()

