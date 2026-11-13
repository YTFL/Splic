"""Tests for service health, readiness, and lifecycle."""

import os
import sys
import unittest

# Ensure backend/composio is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from starlette.testclient import TestClient
from app.main import app
from app.config import get_settings
from app.integrations.composio.client import get_composio_client_manager
from tests.conftest import MockComposioClient


class TestHealthEndpoints(unittest.TestCase):
    """Test health, readiness, and diagnostic endpoints."""

    def setUp(self):
        self.client = TestClient(app)
        self.client_manager = get_composio_client_manager()
        self.mock_composio = MockComposioClient()
        self.client_manager.set_mock_client(self.mock_composio)

    def tearDown(self):
        self.client_manager.reset()

    def test_root_endpoint(self):
        """Verify GET / returns service information."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("name", data)
        self.assertEqual(data["name"], "Splic Composio Backend")
        self.assertEqual(data["docs"], "/docs")

    def test_health_endpoint(self):
        """Verify GET /api/v1/health returns healthy status."""
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "composio-backend")
        self.assertIn("composio", data)
        self.assertEqual(data["composio"]["status"], "MOCK")

    def test_readiness_endpoint(self):
        """Verify GET /api/v1/ready returns ready status."""
        response = self.client.get("/api/v1/ready")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ready")

    def test_unconfigured_composio_status_reporting(self):
        """Verify that an unconfigured client reports status gracefully without crashing."""
        self.client_manager.reset()
        status_info = self.client_manager.get_health_status()
        self.assertIn("status", status_info)
        # Should be UNCONFIGURED when no key is set
        self.assertFalse(status_info["is_mock"])


if __name__ == "__main__":
    unittest.main()

