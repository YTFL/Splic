"""
test_suite.py — Comprehensive automated test suite for TinyDB & API.
Tests database CRUD, sticker indexing, user storage paths, and FastAPI endpoints.
"""

import sys
import unittest
import io
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

import os
os.environ.setdefault("SPLIC_DATA_DIR", str(BACKEND_DIR / ".splic_test"))
os.environ.setdefault("USE_MOCK", "true")
# Pipeline tests never scrape the web; stickers resolve from cache / bundled icons.
os.environ.setdefault("STICKER_FETCH", "false")

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


class TestSarvamAutoEditPipeline(unittest.TestCase):
    """Tests for the Sarvam Auto-Edit pipeline (always runs in USE_MOCK=true mode)."""

    @classmethod
    def setUpClass(cls):
        import os
        os.environ["USE_MOCK"] = "true"
        cls.client = TestClient(app)

    def test_schemas_edit_plan_validation(self):
        """EditPlan schema validates a correct dict."""
        from schemas import EditPlan, CaptionChunk, CutSegment
        plan_dict = {
            "transcript": "Test transcript",
            "language_code": "hi-IN",
            "duration": 10.0,
            "words": [{"word": "Test", "start_time": 0.0, "end_time": 0.5}],
            "captions": [{
                "id": "cap_1", "start": 0.0, "end": 1.5, "text": "Test transcript",
                "words": [{"word": "Test", "start_time": 0.0, "end_time": 0.5}],
                "highlight_color": "#FFD600", "position": {"x": 50, "y": 75}
            }],
            "cuts": [{"start": 2.0, "end": 3.0, "duration": 1.0, "reason": "dead_air"}],
            "transitions": [{"at": 3.0, "type": "fade_black", "duration": 0.3}],
            "stickers": [],
            "sfx": [],
            "zooms": [],
        }
        plan = EditPlan.model_validate(plan_dict)
        self.assertEqual(plan.transcript, "Test transcript")
        self.assertEqual(len(plan.captions), 1)
        self.assertEqual(len(plan.cuts), 1)

    def test_auto_edit_endpoint_mock(self):
        """POST /api/sarvam-auto-edit with mock WAV returns valid EditPlan."""
        import struct
        sample_rate = 16000
        num_samples = sample_rate  # 1 second
        wav_bytes = io.BytesIO()
        data_size = num_samples * 2
        wav_bytes.write(b"RIFF")
        wav_bytes.write(struct.pack("<I", 36 + data_size))
        wav_bytes.write(b"WAVE")
        wav_bytes.write(b"fmt ")
        wav_bytes.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
        wav_bytes.write(b"data")
        wav_bytes.write(struct.pack("<I", data_size))
        wav_bytes.write(b"\x00" * data_size)
        wav_bytes.seek(0)

        resp = self.client.post(
            "/api/sarvam-auto-edit",
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("transcript", data)
        self.assertIn("captions", data)
        self.assertIn("cuts", data)
        self.assertIn("stickers", data)
        self.assertTrue(isinstance(data["captions"], list))

    def test_silence_detector_synthetic(self):
        """Silence detector finds gaps in a synthetic WAV with known silence."""
        import struct
        from silence_detector import detect_silences
        sr = 16000
        loud = struct.pack(f"<{sr}h", *([1000] * sr))
        quiet = b"\x00" * (sr * 2)
        pcm = loud + quiet + loud + quiet + loud
        data_size = len(pcm)
        header = (b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE" +
                  b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16) +
                  b"data" + struct.pack("<I", data_size))
        wav_bytes = header + pcm
        cuts = detect_silences(wav_bytes, min_silence_ms=500, silence_thresh_dbfs=-30.0)
        self.assertGreaterEqual(len(cuts), 1)
        for cut in cuts:
            self.assertIn("start", cut)
            self.assertIn("end", cut)
            self.assertGreater(cut["end"], cut["start"])



# ============================================================================
# Extended pipeline tests — every network call is stubbed (AGENTS.md Rule 2)
# ============================================================================

import json
import math
import struct
import tempfile
import subprocess
from unittest import mock as umock


def _make_wav(segments, sr=16000, channels=1, amp=8000):
    """segments: list of (seconds, loud: bool). Returns RIFF WAV bytes (16-bit)."""
    frames = []
    t = 0
    for secs, loud in segments:
        n = int(secs * sr)
        for i in range(n):
            v = int(amp * math.sin(2 * math.pi * 220 * (t + i) / sr)) if loud else 0
            frames.extend([v] * channels)
        t += n
    pcm = struct.pack(f"<{len(frames)}h", *frames)
    header = (b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVE" +
              b"fmt " + struct.pack("<IHHIIHH", 16, 1, channels, sr, sr * 2 * channels, 2 * channels, 16) +
              b"data" + struct.pack("<I", len(pcm)))
    return header + pcm


# Speech in [0,2.0], silence [2.0,3.5], speech [3.5,6.0], silence [6.0,7.0]
_SPEECH_LAYOUT = [(2.0, True), (1.5, False), (2.5, True), (1.0, False)]


def _stub_stt_timestamps(wav_bytes, filename, language_code):
    """Sarvam-style response using the parallel-array `timestamps` shape."""
    return {
        "request_id": "stub",
        "transcript": "arre bhai Zomato se biryani mangwayi UPI se paise diye",
        "language_code": "hi-IN",
        "timestamps": {
            "words": ["arre bhai", "Zomato se", "biryani mangwayi", "UPI se", "paise diye"],
            "start_time_seconds": [0.1, 0.8, 1.3, 3.6, 4.6],
            "end_time_seconds": [0.7, 1.25, 1.95, 4.4, 5.8],
        },
    }


_STUB_DIRECTOR = {
    "cuts": [
        {"start": 0.1, "end": 0.35, "reason": "filler_word"},     # "arre" -> allowed (filler)
        {"start": 0.8, "end": 1.9, "reason": "bad idea"},         # real speech -> must be dropped
    ],
    "transitions": [{"at": 3.4, "type": "wipe_left", "duration": 0.3}],
    "captions": [{"text": "this does not match the words"}],     # invalid -> rebuilt
    "stickers": [
        {"keyword": "Zomato", "start": 0.9, "position": {"x": 80, "y": 20}},
        {"keyword": "Zomato", "start": 1.0},                       # duplicate -> dropped
        {"keyword": "UPI", "start": 2.5, "duration": 2},           # 2.5 is inside a cut -> snapped to mention
    ],
    "sfx": [
        {"asset": "/assets/sfx/cash.mp3", "start": 4.6, "volume": 3},
        {"asset": "boom", "start": 2.6},                           # inside the dead-air cut -> pushed out
    ],
    "zooms": [{"start": 4.6, "end": 5.8}],
}


class TestPlanBuilderAndClient(unittest.TestCase):

    def test_sample_plan_internally_consistent(self):
        from schemas import EditPlan
        from config import TIMELINE_STUDIO_SFX_DIR
        plan = EditPlan.model_validate(json.loads((BACKEND_DIR / "sample_edit_plan.json").read_text(encoding="utf-8")))
        self.assertGreater(len(plan.captions), 0)
        spoken = [w.word for w in plan.words]
        self.assertEqual([w.word for c in plan.captions for w in c.words], spoken)
        for c in plan.captions:
            self.assertTrue(1 <= len(c.words) <= 4, c.text)
            for cut in plan.cuts:
                self.assertFalse(c.start < cut.start < c.end, f"{c.id} straddles a cut")
        for item in list(plan.stickers) + list(plan.sfx):
            self.assertFalse(any(cut.start <= item.start < cut.end for cut in plan.cuts))
        for s in plan.sfx:
            self.assertTrue((TIMELINE_STUDIO_SFX_DIR / s.asset.rsplit("/", 1)[-1]).exists(), s.asset)
        self.assertEqual(len(plan.transitions), len(plan.cuts))

    def test_sarvam_client_mock_makes_no_network_calls(self):
        import sarvam_client
        with umock.patch.object(sarvam_client.httpx, "Client", side_effect=AssertionError("network used")):
            stt = sarvam_client.transcribe_audio(b"x", "a.wav", mock=True)
            plan = sarvam_client.direct_video_edit(stt["transcript"], stt["words"], [], mock=True)
        self.assertTrue(stt["words"])
        self.assertEqual(plan["director"], "mock")

    def test_normalize_stt_response_shapes(self):
        from sarvam_client import normalize_stt_response
        a = normalize_stt_response({"transcript": "a b", "words": [
            {"word": "a", "start_time": 0, "end_time": 0.5}, {"word": "b", "start_time": 0.5, "end_time": 1}]})
        self.assertEqual(len(a["words"]), 2)
        b = normalize_stt_response(_stub_stt_timestamps(b"", "", ""), offset=10.0)
        self.assertEqual(len(b["words"]), 10)  # phrase entries split into words
        self.assertEqual(b["words"][0]["word"], "arre")
        self.assertAlmostEqual(b["words"][0]["start_time"], 10.1, places=3)
        self.assertAlmostEqual(b["words"][1]["end_time"], 10.7, places=3)

    def test_extract_json_object_tolerates_wrappers(self):
        from sarvam_client import extract_json_object
        self.assertEqual(extract_json_object('<think>hmm {x}</think>```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(extract_json_object('Sure! {"b": [1]} hope this helps'), {"b": [1]})
        with self.assertRaises(Exception):
            extract_json_object("no json here")

    def test_plan_builder_guards(self):
        from plan_builder import build_edit_plan
        from sarvam_client import normalize_stt_response
        from schemas import EditPlan
        words = normalize_stt_response(_stub_stt_timestamps(b"", "", ""))["words"]
        silences = [{"start": 2.0, "end": 3.5}]
        plan = build_edit_plan(json.loads(json.dumps(_STUB_DIRECTOR)), words=words,
                               silence_cuts=silences, duration=7.0, director="sarvam")
        EditPlan.model_validate(plan)
        reasons = [c["reason"] for c in plan["cuts"]]
        self.assertIn("filler_word", reasons)
        self.assertIn("dead_air", reasons)
        self.assertTrue(any("non-filler" in w for w in plan["warnings"]))
        for c in plan["cuts"]:  # no cut may touch a non-filler word
            for w in words:
                if w["word"] != "arre":
                    self.assertFalse(c["start"] < w["end_time"] and w["start_time"] < c["end"], (c, w))
        # "arre" was cut, so it is not captioned; others are, in 1-4 word chunks
        cap_words = [w["word"] for c in plan["captions"] for w in c["words"]]
        self.assertNotIn("arre", cap_words)
        self.assertEqual(cap_words, [w["word"] for w in words if w["word"] != "arre"])
        self.assertTrue(all(1 <= len(c["words"]) <= 4 for c in plan["captions"]))
        # stickers: deduped, percent position normalised, snapped to mention
        self.assertEqual([s["slug"] for s in plan["stickers"]], ["zomato", "upi"])
        self.assertEqual(plan["stickers"][0]["position"], {"x": 0.8, "y": 0.2})
        self.assertEqual(plan["stickers"][1]["start"], 3.6)
        # sfx: alias mapping, volume clamp, pushed out of the 2.0-3.5 dead-air cut
        assets = {s["asset"] for s in plan["sfx"]}
        self.assertEqual(assets, {"/assets/sound-effects/coins-1.mp3", "/assets/sound-effects/soft-thud.mp3"})
        self.assertTrue(all(s["volume"] <= 1.0 for s in plan["sfx"]))
        for s in plan["sfx"]:
            self.assertFalse(any(c["start"] <= s["start"] < c["end"] for c in plan["cuts"]))
        # transitions: one per interior cut, honouring the director's hint
        self.assertIn("wipe_left", [t["type"] for t in plan["transitions"]])
        self.assertEqual(plan["zooms"][0]["scale"], 1.25)

    def test_heuristic_director(self):
        from plan_builder import heuristic_director, normalize_words
        from sarvam_client import normalize_stt_response
        words = normalize_words(normalize_stt_response(_stub_stt_timestamps(b"", "", ""))["words"])
        h = heuristic_director(words)
        self.assertEqual({s["keyword"] for s in h["stickers"]}, {"Zomato", "Biryani", "UPI"})
        self.assertTrue(any(s["asset"] == "cash" for s in h["sfx"]))

    def test_audio_utils_stereo_resample(self):
        from audio_utils import prepare_audio, split_wav
        wav = _make_wav([(0.5, True), (0.5, False)], sr=44100, channels=2)
        prepared = prepare_audio(wav, "stereo.wav")
        self.assertAlmostEqual(prepared.duration, 1.0, delta=0.02)
        self.assertEqual(prepared.wav_bytes[22:24], b"\x01\x00")  # mono
        self.assertEqual(struct.unpack("<I", prepared.wav_bytes[24:28])[0], 16000)
        pieces = split_wav(_make_wav([(60, False)]), 25)
        self.assertEqual([round(o) for o, _ in pieces], [0, 25, 50])

    def test_silence_detector_boundaries(self):
        from silence_detector import detect_silences
        cuts = detect_silences(_make_wav(_SPEECH_LAYOUT))
        self.assertEqual(len(cuts), 2)
        self.assertAlmostEqual(cuts[0]["start"], 2.04, delta=0.03)
        self.assertAlmostEqual(cuts[0]["end"], 3.46, delta=0.03)


class TestLivePipelineStubbed(unittest.TestCase):
    """Exercise the USE_MOCK=false code path with Sarvam/Groq/Gemini HTTP stubbed out."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def _post(self, data_bytes, name="clip.wav", **form):
        form.setdefault("use_mock", "false")
        return self.client.post("/api/sarvam-auto-edit", data=form,
                                files={"file": (name, data_bytes, "application/octet-stream")})

    def _director_json(self, *_a, **_k):
        return json.loads(json.dumps(_STUB_DIRECTOR))

    def test_live_path_sarvam(self):
        import sarvam_client
        with umock.patch.object(sarvam_client, "_stt_request", side_effect=_stub_stt_timestamps), \
             umock.patch.object(sarvam_client, "_call_sarvam", side_effect=self._director_json):
            resp = self._post(_make_wav(_SPEECH_LAYOUT))
        self.assertEqual(resp.status_code, 200, resp.text)
        plan = resp.json()
        self.assertEqual(plan["director"], "sarvam")
        self.assertAlmostEqual(plan["duration"], 7.0, delta=0.05)
        dead = [c for c in plan["cuts"] if "dead_air" in c["reason"]]
        self.assertTrue(any(c["start"] < 2.5 < c["end"] for c in dead))      # acoustic gap cut
        self.assertTrue(any(c["end"] >= 6.9 for c in dead))                  # trailing silence trimmed
        self.assertGreater(len(plan["captions"]), 0)
        for s in plan["stickers"]:  # every surviving sticker points at a real asset
            self.assertTrue(s["asset_url"].startswith(("/api/stickers/", "/assets/stickers/")))

    def test_fallback_provider_gemini(self):
        import sarvam_client
        with umock.patch.dict(os.environ, {"FALLBACK_PROVIDER": "gemini"}), \
             umock.patch.object(sarvam_client, "_stt_request", side_effect=_stub_stt_timestamps), \
             umock.patch.object(sarvam_client, "_call_sarvam", side_effect=RuntimeError("timeout")), \
             umock.patch.object(sarvam_client, "_call_gemini", side_effect=self._director_json):
            resp = self._post(_make_wav(_SPEECH_LAYOUT))
        self.assertEqual(resp.status_code, 200, resp.text)
        plan = resp.json()
        self.assertEqual(plan["director"], "gemini")
        self.assertTrue(any("sarvam" in w for w in plan["warnings"]))

    def test_total_director_failure_uses_heuristics(self):
        import sarvam_client
        with umock.patch.dict(os.environ, {"FALLBACK_PROVIDER": "none"}), \
             umock.patch.object(sarvam_client, "_stt_request", side_effect=_stub_stt_timestamps), \
             umock.patch.object(sarvam_client, "_call_sarvam", side_effect=RuntimeError("down")):
            resp = self._post(_make_wav(_SPEECH_LAYOUT))
        self.assertEqual(resp.status_code, 200, resp.text)
        plan = resp.json()
        self.assertEqual(plan["director"], "heuristic")
        self.assertTrue(plan["captions"])
        self.assertTrue(plan["sfx"])

    def test_stt_failure_returns_502(self):
        import sarvam_client
        with umock.patch.object(sarvam_client, "_stt_request", side_effect=RuntimeError("HTTP 401")):
            resp = self._post(_make_wav(_SPEECH_LAYOUT))
        self.assertEqual(resp.status_code, 502)

    def test_long_audio_is_chunked_for_stt(self):
        import sarvam_client
        calls = []

        def stt(wav, fn, lang):
            calls.append(fn)
            return {"transcript": "haan", "words": [{"word": "haan", "start_time": 1.0, "end_time": 1.4}]}

        with umock.patch.object(sarvam_client, "_stt_request", side_effect=stt), \
             umock.patch.object(sarvam_client, "_call_sarvam", side_effect=lambda m: {}):
            resp = self._post(_make_wav([(55, False)]))
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(len(calls), 3)
        starts = [w["start_time"] for w in resp.json()["words"]]
        self.assertEqual(starts, [1.0, 26.0, 51.0])

    def test_bad_uploads(self):
        self.assertEqual(self._post(b"").status_code, 400)
        self.assertEqual(self._post(b"this is not media at all" * 50, name="x.mp4").status_code, 415)

    def test_mp4_video_upload(self):
        from audio_utils import find_ffmpeg
        import sarvam_client
        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            self.skipTest("ffmpeg not available")
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "clip.mp4")
            # 9:16 video; audio = 2s tone, 1.5s silence, 2.5s tone, 1s silence
            expr = "if(lt(t,2)+between(t,3.5,6),0.3*sin(2*PI*220*t),0)"
            subprocess.run([
                ffmpeg, "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", "color=c=blue:s=360x640:d=7:r=15",
                "-f", "lavfi", "-i", f"aevalsrc='{expr}':s=44100:d=7",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out,
            ], check=True, capture_output=True, timeout=120)
            with open(out, "rb") as fh:
                mp4 = fh.read()
        with umock.patch.object(sarvam_client, "_stt_request", side_effect=_stub_stt_timestamps), \
             umock.patch.object(sarvam_client, "_call_sarvam", side_effect=self._director_json):
            resp = self._post(mp4, name="clip.mp4")
        self.assertEqual(resp.status_code, 200, resp.text)
        plan = resp.json()
        self.assertAlmostEqual(plan["duration"], 7.0, delta=0.15)
        self.assertTrue(any(c["start"] < 2.5 < c["end"] for c in plan["cuts"]))

    def test_plan_saved_to_project(self):
        import db
        db.create_project(name="Auto edit target", project_id="autoedit_target")
        try:
            resp = self.client.post("/api/sarvam-auto-edit", data={"project_id": "autoedit_target"},
                                    files={"file": ("a.wav", _make_wav([(0.2, True)]), "audio/wav")})
            self.assertEqual(resp.status_code, 200, resp.text)
            proj = db.get_project("autoedit_target")
            self.assertEqual(proj["status"], "auto_edited")
            self.assertEqual(proj["edit_plan"]["project_id"], "autoedit_target")
        finally:
            db.delete_project("autoedit_target")

    def test_sfx_assets_served_with_corp(self):
        resp = self.client.get("/assets/sound-effects/coins-1.mp3")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("cross-origin-resource-policy"), "cross-origin")


if __name__ == "__main__":
    unittest.main()
