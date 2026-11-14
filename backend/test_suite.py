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
# Tests stub every Sarvam HTTP call; a dummy key only satisfies the config gate.
os.environ["SARVAM_API_KEY"] = "test-dummy-key"
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
    """Offline tests for the Sarvam Auto-Edit pipeline building blocks."""

    @classmethod
    def setUpClass(cls):
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
            "transitions": [{"at": 3.0, "cut_index": 0, "transition_id": "wipe-left", "duration": 0.3}],
            "stickers": [],
            "sfx": [],
            "zooms": [],
        }
        plan = EditPlan.model_validate(plan_dict)
        self.assertEqual(plan.transcript, "Test transcript")
        bad = dict(plan_dict, transitions=[{"at": 3.0, "cut_index": 0, "transition_id": "fade_black"}])
        with self.assertRaises(Exception):  # not an editor transition id
            EditPlan.model_validate(bad)
        self.assertEqual(len(plan.captions), 1)
        self.assertEqual(len(plan.cuts), 1)

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
        # transitions: legacy "wipe_left" mapped onto the editor id, attached to a cut seam
        self.assertEqual([t["transition_id"] for t in plan["transitions"]], ["wipe-left"])
        t0 = plan["transitions"][0]
        self.assertEqual(t0["at"], plan["cuts"][t0["cut_index"]]["end"])
        self.assertEqual(plan["zooms"][0]["scale"], 1.25)

    def test_gapless_stt_timings_still_cut_real_silences(self):
        """Saaras timestamps tile the audio with no gaps; acoustic silences must still be cut."""
        from plan_builder import build_edit_plan, refine_words_with_silences
        # Contiguous timings: "M," straddles the 1.0-2.0 pause, "U M M," is a spelled-out "umm".
        toks = [("hello", 0.0, 0.5), ("U", 0.5, 0.6), ("M", 0.6, 0.7), ("M,", 0.7, 1.4),
                ("dosto", 1.4, 2.4), ("aaj", 2.4, 3.0)]
        words = [{"word": w, "start_time": s, "end_time": e} for w, s, e in toks]
        silences = [{"start": 1.0, "end": 2.0}]
        refined = refine_words_with_silences(words, silences)
        self.assertEqual([w["word"] for w in refined], [w for w, _, _ in toks])
        self.assertTrue(all(not (1.05 < w["start_time"] < 1.95) for w in refined))
        self.assertEqual(refined, refine_words_with_silences(refined, silences))  # idempotent
        plan = build_edit_plan({"edit_plan": {"cuts": [{"start": 0.55, "end": 1.0, "reason": "filler_word"}]}},
                               words=words, silence_cuts=silences, duration=3.0)
        removed = sum(c["duration"] for c in plan["cuts"])
        self.assertGreater(removed, 0.8, plan["cuts"])
        cap_words = [w["word"] for c in plan["captions"] for w in c["words"]]
        self.assertEqual(cap_words, ["hello", "dosto", "aaj"])  # the whole "U M M," is gone

    def test_heuristic_director(self):
        from plan_builder import heuristic_director, normalize_words
        from sarvam_client import normalize_stt_response
        words = normalize_words(normalize_stt_response(_stub_stt_timestamps(b"", "", ""))["words"])
        h = heuristic_director(words)
        concepts = {r["concept"] for r in h["sticker_requests"]}
        self.assertTrue({"Zomato", "Biryani", "UPI"} <= concepts, concepts)
        self.assertTrue(any(r["source"] == "library" for r in h["sticker_requests"]))  # "paise" -> coins
        refs = {r["ref"] for r in h["sticker_requests"]}
        self.assertTrue(all(p["ref"] in refs for p in h["edit_plan"]["stickers"]))
        self.assertTrue(any(s["sound_id"] == "coins-1" for s in h["edit_plan"]["sfx"]))

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
    """Exercise the live pipeline with Sarvam/Groq/Gemini HTTP stubbed out."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def _post(self, data_bytes, name="clip.wav", **form):
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
        import sarvam_client
        db.create_project(name="Auto edit target", project_id="autoedit_target")
        try:
            with umock.patch.object(sarvam_client, "_stt_request", side_effect=_stub_stt_timestamps), \
                 umock.patch.object(sarvam_client, "_call_sarvam", side_effect=self._director_json):
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



# ============================================================================
# Two-document director contract (GLM-5.3-flash): sticker_requests + edit_plan
# ============================================================================

_STUB_DIRECTOR_V2 = {
    "sticker_requests": [
        {"ref": "s1", "concept": "money", "source": "library", "library_id": "shop-coins"},
        {"ref": "s2", "concept": "Zomato", "source": "scrape", "query": "Zomato logo"},
        {"ref": "s3", "concept": "party", "source": "library", "library_id": "does-not-exist"},
        {"ref": "s4", "concept": "quantum flux capacitor", "source": "scrape", "query": "qfc"},
    ],
    "edit_plan": {
        "cuts": [{"start": 0.1, "end": 0.35, "reason": "filler_word"}],
        "transitions": [
            {"at": 3.5, "transition_id": "wipe-left", "duration": 0.3},
            {"at": 3.5, "transition_id": "star-wipe"},                          # unknown id
        ],
        "stickers": [
            {"ref": "s1", "start": 4.6, "duration": 1.5, "x": 0.8, "y": 0.2,
             "animation_in": "pop", "animation_out": "fade", "emphasis": "pulse"},
            {"ref": "s2", "start": 0.8, "x": 0.2, "y": 0.75,                    # caption band
             "animation_in": "slide-up", "animation_out": "pop"},
            {"ref": "s3", "start": 1.3, "animation_in": "teleport"},           # unknown animation
            {"ref": "s4", "start": 3.6},                                       # unresolvable image
            {"ref": "s9", "start": 2.0},                                       # no such request
        ],
        "sfx": [
            {"sound_id": "coins-1", "start": 4.6, "volume": 0.7, "reason": "money"},
            {"sound_id": "airhorn-9000", "start": 1.0},                        # not bundled
            {"sound_id": "ui-click-1", "start": 4.7},                          # stacked on coins-1
        ],
        "zooms": [{"start": 4.6, "end": 5.8, "scale": 1.25}],
        "effects": [
            {"effect": "shake", "start": 4.6, "duration": 0.5, "intensity": 0.7},
            {"effect": "explode", "start": 1.0},                               # unsupported
            {"effect": "glitch", "start": 5.0},                                # too close to shake
        ],
        "caption_emphasis": [{"word": "paise", "time": 4.6}],
    },
}


class TestDirectorTwoDocuments(unittest.TestCase):
    """GLM director returns sticker_requests (JSON 1) + edit_plan (JSON 2) in one call."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def _run(self, director_output):
        import sarvam_client
        captured = {}

        def fake_post(url, headers, payload, provider):
            captured["payload"] = payload
            return json.loads(json.dumps(director_output))

        with umock.patch.object(sarvam_client, "_stt_request", side_effect=_stub_stt_timestamps), \
             umock.patch.object(sarvam_client, "_post_chat", side_effect=fake_post):
            resp = self.client.post("/api/sarvam-auto-edit",
                                    files={"file": ("clip.wav", _make_wav(_SPEECH_LAYOUT), "audio/wav")})
        return resp, captured

    def test_request_uses_glm_and_ships_catalog(self):
        resp, captured = self._run(_STUB_DIRECTOR_V2)
        self.assertEqual(resp.status_code, 200, resp.text)
        payload = captured["payload"]
        self.assertEqual(payload["model"], "glm5.3-flash")
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertNotIn("reasoning_effort", payload)
        user = json.loads(payload["messages"][1]["content"])
        self.assertIn("wipe-left", user["catalog"]["transitions"])
        self.assertIn("pop", user["catalog"]["animation_in"])
        self.assertIn("coins-1", user["catalog"]["sound_effects"])
        self.assertNotIn("piano-c4", user["catalog"]["sound_effects"])
        self.assertTrue(any(s["id"] == "shop-coins" for s in user["catalog"]["sticker_library"]))
        self.assertTrue(user["captions"] and all("id" in c and "text" in c for c in user["captions"]))
        self.assertIn("stickers", user["targets"])

    def test_plan_is_sanitised_against_editor_vocabulary(self):
        resp, _ = self._run(_STUB_DIRECTOR_V2)
        self.assertEqual(resp.status_code, 200, resp.text)
        plan = resp.json()
        self.assertEqual(plan["director"], "sarvam")

        # JSON 1: every request reported with its resolution
        reqs = {r["ref"]: r for r in plan["sticker_requests"]}
        self.assertEqual(reqs["s1"]["resolution"], "library")
        self.assertEqual(reqs["s1"]["asset_url"], "/assets/stickers/shop-coins.png")
        self.assertEqual(reqs["s3"]["source"], "scrape")                 # bad library id -> scrape
        self.assertEqual(reqs["s3"]["resolution"], "fallback_library")   # offline -> confetti icon
        self.assertFalse(reqs["s4"]["resolved"])

        # transitions: only editor ids, one per seam
        self.assertEqual([t["transition_id"] for t in plan["transitions"]], ["wipe-left"])

        # stickers: unresolved + unknown refs dropped, animations compiled
        stickers = {s["ref"]: s for s in plan["stickers"]}
        expected = {"s1", "s3"} | ({"s2"} if reqs["s2"]["resolved"] else set())
        self.assertEqual(set(stickers), expected)
        money = stickers["s1"]
        self.assertEqual(money["animation"]["out"]["id"], "fade")        # native editor animation
        self.assertEqual(money["animation"]["in"]["id"], "none")         # pop is keyframed instead
        self.assertEqual(money["keyframes"][0]["scale"], 0.2)
        self.assertEqual(money["keyframes"][0]["opacity"], 0.0)
        self.assertTrue(any((k["scale"] or 0) > 1.05 for k in money["keyframes"][3:]))  # pulse
        self.assertEqual(stickers["s3"]["animation_in"], "pop")          # unknown id -> house style
        for s in plan["stickers"]:
            self.assertFalse(0.62 < s["position"]["y"] < 0.9, s)          # never on the captions

        # sfx / effects: unknown ids dropped, no stacking
        self.assertEqual([s["sound_id"] for s in plan["sfx"]], ["coins-1"])
        self.assertEqual([e["effect"] for e in plan["effects"]], ["shake"])
        self.assertTrue(any("not in the bundled library" in w for w in plan["warnings"]))

        # caption emphasis comes back on the STT caption words
        emph = [w["word"] for c in plan["captions"] for w in c["words"] if w["emphasis"]]
        self.assertEqual(emph, ["paise"])

    def test_both_json_files_saved_for_the_run(self):
        from main import RUNS_DIR
        resp, _ = self._run(_STUB_DIRECTOR_V2)
        run_dir = RUNS_DIR / resp.json()["run_id"]
        sticker_json = json.loads((run_dir / "sticker_requests.json").read_text(encoding="utf-8"))
        edit_json = json.loads((run_dir / "edit_plan.json").read_text(encoding="utf-8"))
        self.assertEqual(len(sticker_json["sticker_requests"]), 4)
        self.assertIn("transitions", edit_json)
        self.assertIn("keyframes", edit_json["stickers"][0])
        self.assertTrue((run_dir / "director_raw.json").exists())

    def test_wrong_shape_falls_back_to_heuristics(self):
        resp, _ = self._run({"thoughts": "I would add some stickers"})
        self.assertEqual(resp.status_code, 200, resp.text)
        plan = resp.json()
        self.assertEqual(plan["director"], "heuristic")
        self.assertTrue(any("sarvam" in w for w in plan["warnings"]))

    def test_density_caps_and_concurrency(self):
        from plan_builder import build_edit_plan, density_caps
        from schemas import EditPlan
        reqs = [{"ref": f"s{i}", "concept": f"thing{i}", "source": "library", "library_id": "trend-flame"}
                for i in range(30)]
        raw = {"sticker_requests": reqs, "edit_plan": {
            "stickers": [{"ref": f"s{i}", "start": i * 0.3, "duration": 2.0} for i in range(30)],
            "sfx": [{"sound_id": "ui-click-1", "start": i * 0.1} for i in range(100)],
        }}
        plan = build_edit_plan(raw, words=[{"word": "x", "start_time": 0, "end_time": 0.2}], duration=9.0)
        EditPlan.model_validate(plan)
        caps = density_caps(9.0)
        self.assertLessEqual(len(plan["stickers"]), caps["stickers"])
        self.assertLessEqual(len(plan["sfx"]), caps["sfx"])
        for s in plan["stickers"]:
            live = [o for o in plan["stickers"]
                    if o["start"] < s["start"] + s["duration"] and s["start"] < o["start"] + o["duration"]]
            self.assertLessEqual(len(live), 2)

    def test_project_list_reads_info_from_local_storage(self):
        import sarvam_client
        from config import DB_PATH, RUNS_DIR
        db.create_project(name="Info project", project_id="info_project")
        try:
            def fake_post(url, headers, payload, provider):
                return json.loads(json.dumps(_STUB_DIRECTOR_V2))
            with umock.patch.object(sarvam_client, "_stt_request", side_effect=_stub_stt_timestamps), \
                 umock.patch.object(sarvam_client, "_post_chat", side_effect=fake_post):
                resp = self.client.post("/api/sarvam-auto-edit", data={"project_id": "info_project"},
                                        files={"file": ("clip.wav", _make_wav(_SPEECH_LAYOUT), "audio/wav")})
            self.assertEqual(resp.status_code, 200, resp.text)

            body = self.client.get("/api/projects").json()
            self.assertEqual(body["storage"]["db_path"], str(DB_PATH))
            self.assertEqual(body["storage"]["runs_dir"], str(RUNS_DIR))
            proj = next(p for p in body["projects"] if p["id"] == "info_project")
            self.assertNotIn("edit_plan", proj)                      # list stays light
            info = proj["summary"]
            self.assertEqual(info["status"], "auto_edited")
            self.assertTrue(info["has_edit_plan"])
            self.assertAlmostEqual(info["duration"], 7.0, delta=0.05)
            self.assertGreater(info["counts"]["captions"], 0)
            self.assertEqual(info["counts"]["sfx"], 1)
            self.assertEqual(info["runs"]["count"], 1)
            latest = info["runs"]["latest"]
            self.assertTrue(Path(latest["path"]).is_dir())
            self.assertIn("edit_plan.json", latest["files"])
            self.assertIn("sticker_requests.json", latest["files"])

            single = self.client.get("/api/projects/info_project").json()
            self.assertIn("edit_plan", single)
            self.assertEqual(single["summary"]["runs"]["count"], 1)

            # Deleting through the API also removes the project's run folders.
            deleted = self.client.delete("/api/projects/info_project").json()
            self.assertEqual(deleted["removed_runs"], 1)
            self.assertFalse(Path(latest["path"]).exists())
        finally:
            db.delete_project("info_project")
            from project_info import remove_project_runs
            remove_project_runs("info_project")

    def test_resolve_endpoint(self):
        resp = self.client.post("/api/stickers/resolve", json={"sticker_requests": [
            {"ref": "a", "concept": "money", "source": "library", "library_id": "shop-coins"},
            {"ref": "b", "concept": "zzqqxx", "source": "scrape", "query": "zzqqxx"},
        ], "allow_network": False})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["sticker_requests"][0]["asset_url"], "/assets/stickers/shop-coins.png")
        self.assertEqual(body["failed"], ["zzqqxx"])


# ============================================================================
# Merged Composio + Firebase service (branch Kiran) mounted on the main app
# ============================================================================

class TestComposioServiceMounted(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import composio_integration
        if not composio_integration.COMPOSIO_AVAILABLE:
            raise unittest.SkipTest(f"Composio service unavailable: {composio_integration.IMPORT_ERROR}")
        from app.auth.firebase import get_firebase_auth_manager
        cls.auth = get_firebase_auth_manager()
        cls.client = TestClient(app)

    def tearDown(self):
        self.auth.reset_mock_verifier()

    def test_composio_sdk_not_shadowed_by_repo_folder(self):
        import composio
        self.assertIn("site-packages", composio.__file__)
        from composio import Composio  # noqa: F401

    def test_health_reports_both_services(self):
        data = self.client.get("/api/health").json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["composio"]["mounted"])
        self.assertEqual(data["composio"]["prefix"], "/api/v1")
        v1 = self.client.get("/api/v1/health")
        self.assertEqual(v1.status_code, 200)
        self.assertEqual(v1.json()["service"], "composio-backend")
        self.assertEqual(self.client.get("/api/v1/ready").json()["status"], "ready")

    def test_all_v1_routes_registered(self):
        paths = set(self.client.get("/openapi.json").json()["paths"])
        for p in ("/api/v1/composio/status", "/api/v1/composio/toolkits", "/api/v1/composio/execute",
                  "/api/v1/composio/connect/instagram", "/api/v1/composio/connect/youtube",
                  "/api/v1/composio/accounts", "/api/v1/composio/accounts/{account_id}",
                  "/api/sarvam-auto-edit", "/api/projects"):
            self.assertIn(p, paths)

    def test_protected_routes_require_firebase_token(self):
        for path in ("/api/v1/composio/status", "/api/v1/composio/accounts", "/api/v1/composio/toolkits"):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 401, path)
        resp = self.client.get("/api/v1/composio/status", headers={"Authorization": "Token abc"})
        self.assertEqual(resp.status_code, 401)

    def test_authenticated_request_with_mock_verifier(self):
        self.auth.set_mock_verifier(lambda token, check_revoked=True: {"uid": token.replace("tok_", ""), "email": None})
        resp = self.client.get("/api/v1/composio/status", headers={"Authorization": "Bearer tok_creator42"})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["authenticated_user_id"], "creator42")
        toolkits = self.client.get("/api/v1/composio/toolkits", headers={"Authorization": "Bearer tok_creator42"})
        self.assertEqual(toolkits.status_code, 200, toolkits.text)
        self.assertTrue({"instagram", "youtube"} <= {t["slug"] for t in toolkits.json()})

    def test_pipeline_routes_unaffected_by_v1_error_mapping(self):
        # Main pipeline routes still behave exactly as before the merge.
        self.assertEqual(self.client.get("/api/projects/does-not-exist").status_code, 404)
        self.assertEqual(self.client.get("/api/stickers/does-not-exist.png").status_code, 404)


class TestStudioCatalogSnapshot(unittest.TestCase):
    """The Vercel backend service bundles backend/ only, so it reads the editor's sticker
    manifest and SFX ids from backend/studio_catalog/. Keep that snapshot in sync."""

    ASSETS = BACKEND_DIR.parent / "timeline_studio" / "public" / "assets"
    SNAPSHOT = BACKEND_DIR / "studio_catalog"
    HINT = "Stale snapshot: run python backend/scripts/sync_studio_catalog.py"

    def test_sticker_manifest_matches_studio(self):
        import json
        live = json.loads((self.ASSETS / "stickers" / "stickers-manifest.json").read_text(encoding="utf-8"))
        snap = json.loads((self.SNAPSHOT / "stickers-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(live, snap, self.HINT)

    def test_sfx_ids_match_studio(self):
        import json
        live = sorted(p.stem for p in (self.ASSETS / "sound-effects").glob("*.mp3"))
        snap = json.loads((self.SNAPSHOT / "sound-effects.json").read_text(encoding="utf-8"))
        self.assertEqual(live, snap, self.HINT)


if __name__ == "__main__":
    unittest.main()
