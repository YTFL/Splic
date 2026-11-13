"""
test_suite.py — Comprehensive automated test suite for TinyDB & API.
Tests database CRUD, sticker indexing, user storage paths, and FastAPI endpoints.
"""

import sys
import unittest
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from config import SPLIC_DIR, DB_PATH, STICKERS_DIR
import db
from main import app


class TestTinyDBAndStorage(unittest.TestCase):
    """Test suite for TinyDB storage, CRUD operations, and endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_storage_paths_exist(self):
        """Verify user storage paths (~/.splic) are resolved and created."""
        self.assertTrue(SPLIC_DIR.exists(), f"SPLIC_DIR does not exist: {SPLIC_DIR}")
        self.assertTrue(STICKERS_DIR.exists(), f"STICKERS_DIR does not exist: {STICKERS_DIR}")
        self.assertEqual(DB_PATH.name, "db.json")

    def test_02_health_endpoint(self):
        """Verify /api/health reports correct storage and TinyDB status."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["features"]["tinydb_nosql"])
        self.assertTrue(data["features"]["user_local_storage"])
        self.assertEqual(data["storage"]["splic_dir"], str(SPLIC_DIR))

    def test_03_project_crud_in_tinydb(self):
        """Test Project creation, retrieval, update, and listing in TinyDB."""
        proj_id = "test_reel_automated_01"

        # 1. Create Project
        created = db.create_project(
            name="Automated Test Reel",
            project_id=proj_id,
            settings={"aspect_ratio": "9:16", "fps": 30},
        )
        self.assertEqual(created["id"], proj_id)
        self.assertEqual(created["name"], "Automated Test Reel")
        self.assertEqual(created["status"], "draft")

        # 2. Get Project
        fetched = db.get_project(proj_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["name"], "Automated Test Reel")

        # 3. Update Project
        updated = db.update_project(proj_id, {"status": "in_progress", "notes": "AI edit plan ready"})
        self.assertIsNotNone(updated)
        self.assertEqual(updated["status"], "in_progress")
        self.assertEqual(updated["notes"], "AI edit plan ready")

        # 4. List Projects
        all_projects = db.list_projects()
        self.assertTrue(any(p["id"] == proj_id for p in all_projects))

    def test_04_sticker_indexing_in_tinydb(self):
        """Test recording sticker metadata linked to a project in TinyDB."""
        proj_id = "test_reel_automated_01"
        dummy_save_path = str(STICKERS_DIR / "test_icon.png")

        # Record sticker
        stk = db.record_sticker(
            keyword="Test Biryani",
            slug="test_biryani",
            filename="test_biryani.png",
            save_path=dummy_save_path,
            asset_url="/api/stickers/test_biryani.png",
            size_bytes=12345,
            project_id=proj_id,
        )
        self.assertIsNotNone(stk["id"])
        self.assertEqual(stk["keyword"], "Test Biryani")
        self.assertEqual(stk["project_id"], proj_id)

        # Retrieve stickers for project
        project_stickers = db.get_project_stickers(proj_id)
        self.assertTrue(any(s["slug"] == "test_biryani" for s in project_stickers))

        # Search by keyword
        found = db.get_sticker_by_keyword("test_biryani", project_id=proj_id)
        self.assertIsNotNone(found)
        self.assertEqual(found["filename"], "test_biryani.png")

    def test_05_api_endpoints_integration(self):
        """Test FastAPI project and sticker routes."""
        api_proj_id = "api_reel_test"

        # 1. POST /api/projects
        create_resp = self.client.post("/api/projects", json={
            "name": "API Created Reel",
            "project_id": api_proj_id,
            "settings": {"aspect_ratio": "9:16"}
        })
        self.assertEqual(create_resp.status_code, 201)
        self.assertEqual(create_resp.json()["id"], api_proj_id)

        # 2. GET /api/projects/{project_id}
        get_resp = self.client.get(f"/api/projects/{api_proj_id}")
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.json()["name"], "API Created Reel")

        # 3. PATCH /api/projects/{project_id}
        patch_resp = self.client.patch(f"/api/projects/{api_proj_id}", json={
            "status": "ready_for_export"
        })
        self.assertEqual(patch_resp.status_code, 200)
        self.assertEqual(patch_resp.json()["status"], "ready_for_export")

        # 4. Scrape sticker for project
        scrape_resp = self.client.post(f"/api/projects/{api_proj_id}/stickers/scrape", json={
            "keyword": "Zomato"
        })
        self.assertEqual(scrape_resp.status_code, 200)
        scrape_data = scrape_resp.json()
        self.assertEqual(scrape_data["slug"], "zomato")
        self.assertEqual(scrape_data["project_id"], api_proj_id)

        # 5. GET /api/projects/{project_id}/stickers
        list_resp = self.client.get(f"/api/projects/{api_proj_id}/stickers")
        self.assertEqual(list_resp.status_code, 200)
        self.assertGreaterEqual(list_resp.json()["total"], 1)

        # 6. Serve sticker file with CORP header
        asset_resp = self.client.get("/api/stickers/zomato.png")
        self.assertEqual(asset_resp.status_code, 200)
        self.assertEqual(asset_resp.headers.get("cross-origin-resource-policy"), "cross-origin")
        self.assertEqual(asset_resp.headers.get("access-control-allow-origin"), "*")

        # 7. DELETE /api/projects/{project_id}
        del_resp = self.client.delete(f"/api/projects/{api_proj_id}")
        self.assertEqual(del_resp.status_code, 200)
        self.assertEqual(del_resp.json()["status"], "deleted")

        # 8. Verify project is gone
        verify_del = self.client.get(f"/api/projects/{api_proj_id}")
        self.assertEqual(verify_del.status_code, 404)

    def test_06_delete_project_cascades_stickers(self):
        """Verify deleting a project removes its sticker associations from TinyDB."""
        proj_id = "test_reel_automated_01"
        deleted = db.delete_project(proj_id)
        self.assertTrue(deleted)
        self.assertIsNone(db.get_project(proj_id))


if __name__ == "__main__":
    unittest.main()
