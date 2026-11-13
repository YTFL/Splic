# AGENTS.md — Agentic Development Instructions

This file defines the operating rules, architecture boundaries, and verification steps for AI coding agents working in this repository. Read `GEMINI.md` alongside this file before making changes.

---

## 1. Core Mission & Scope

We are extending **Timeline Studio** (`MartinDelophy/ai-video-editor`) into a **1-click Indic Short-Form Video Auto-Editor** powered by **Sarvam AI**.

**Do NOT rebuild the video editor.** Timeline Studio already handles multi-track rendering, canvas preview, WebCodecs MP4 export, and timeline scrubbing. Your job as a coding agent is to:
1. Build and maintain the Python FastAPI backend (`backend/`) that orchestrates Sarvam AI + dynamic sticker generation.
2. Add the **"⚡ Desi Auto-Cut"** trigger and JSON-to-Timeline dispatcher in the React/TypeScript frontend (`src/`).
3. Keep the edit experience 100% human-in-the-loop (all AI edits land as editable tracks on the timeline).

---

## 2. Environment & Run Commands

### Frontend (Timeline Studio)
```bash
npm install
npm run dev          # Starts Next.js dev server (preserves COOP/COEP headers)
npm run build        # Production bundle check
```

### Backend (FastAPI + Sarvam + rembg)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Required Environment Variables (`backend/.env`)
```env
SARVAM_API_KEY=your_sarvam_api_subscription_key
USE_MOCK=true               # Set to false only for integration tests & live demo
FALLBACK_PROVIDER=none      # Optional: "groq" | "gemini" if Sarvam times out
GROQ_API_KEY=               # Optional fallback
```

---

## 3. Agentic Coding Rules & Guardrails

### Rule 1: Surgical Frontend Edits Only
- **DO NOT** refactor Timeline Studio's core WebCodecs encoder, WebGPU shaders, color wheels, or depth-map pipelines.
- **DO** inspect the existing timeline store (`src/store` or `src/features/timeline`) and `.agent/skills/edit-timeline-studio` to reuse existing track-mutation actions (splitting clips, adding text/caption tracks, adding overlay/PiP images, adding audio tracks).
- **DO** keep all new UI additions minimal and cohesive (one **"⚡ Desi Auto-Cut"** button, loading state indicator, and optional language/caption-style toggle: *Romanized Hinglish* vs *Dual Hinglish + English*).

### Rule 2: Never Burn Sarvam Credits in Automated Tests
- Unit tests and frontend integration tests **MUST** run with `USE_MOCK=true`, reading from `backend/sample_edit_plan.json`.
- Never write an automated test loop that calls `https://api.sarvam.ai/speech-to-text` or `/v2/chat/completions` repeatedly.

### Rule 3: Strict JSON & Timestamp Discipline
- All timestamps across the backend and frontend must be **floating-point seconds** (e.g., `1.25`, not `"00:01:25"`).
- When `cuts` are applied via ripple-delete, ensure downstream `captions`, `stickers`, `sfx`, and `zooms` timestamps are either:
  - Applied **before** ripple-cutting (so Timeline Studio's ripple-delete shifts them automatically), OR
  - Offset mathematically in the dispatcher to match the post-cut timeline clock.
  *(Verify which behavior Timeline Studio's split/delete action uses before wiring the dispatcher!)*

### Rule 4: Cross-Origin Asset Safety (COEP)
- Because Timeline Studio runs with `Cross-Origin-Embedder-Policy: require-corp`, any sticker PNG or SFX MP3 served from `http://localhost:8000` will be blocked by the browser unless FastAPI sets:
  ```python
  response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
  ```
- Alternatively, configure a Next.js rewrite proxy (`/api` and `/dynamic_stickers` -> `http://localhost:8000`) in `next.config.mjs` so all assets appear same-origin to the browser. **Prefer the Next.js rewrite proxy approach.**

### Rule 5: No Emojis in UI — Lucide React Icons Only
- **NEVER** use emojis anywhere in the React/TypeScript UI — not in button labels, status text, tooltips, track headers, panel titles, toasts, or any other interface element.
- **ALWAYS** use icons from `lucide-react` for all iconography in the UI. Import named exports only (e.g. `import { Zap, ChevronRight, Scissors } from 'lucide-react'`).
- Use `strokeWidth={1.25}` for all Lucide icons to match the premium ultra-light aesthetic. Adjust to `strokeWidth={1.5}` only for small icons under 14px.
- **Exception:** Emojis are permitted exclusively inside the actual video content output — e.g. text overlays, karaoke captions, or sticker labels that get burned into the exported MP4. Never in any UI chrome.

### Rule 6: Graceful Fallbacks on External Failures
- **Sticker Scraping:** `duckduckgo_search` can fail or return irrelevant images. Wrap `fetch_and_make_sticker()` in a `try/except` with a 4-second timeout. If it fails, fall back to a matching icon in `public/assets/stickers/` or skip that sticker cleanly without crashing the pipeline.
- **LLM Output:** Always request `response_format={"type": "json_object"}` from `sarvam-105b-conversations` and validate the response with Pydantic before returning it to the frontend.

---

## 4. Backend Module Responsibilities

| File | Responsibility |
| :--- | :--- |
| `backend/main.py` | FastAPI app, CORS, `/api/sarvam-auto-edit` endpoint, `/api/health`. Accepts uploaded video/audio, coordinates pipeline, returns validated `EditPlan` JSON. |
| `backend/sarvam_client.py` | Calls `saaras:v4` (`mode="transliteration"`) for word timestamps and `sarvam-105b-conversations` for the director JSON. Implements `USE_MOCK` and `FALLBACK_PROVIDER`. |
| `backend/sticker_engine.py` | Searches web images via `duckduckgo_search`, strips background with `rembg`, saves RGBA PNGs to `public/assets/dynamic_stickers/`, and enforces disk caching. |
| `backend/silence_detector.py` | Uses `pydub.silence.detect_silence()` to detect dead-air intervals locally at zero API cost and merges them with LLM-identified filler cuts. |
| `backend/schemas.py` | Pydantic models for `WordTimestamp`, `CutSegment`, `StickerOverlay`, `SfxEvent`, `ZoomKeyframe`, and `EditPlan`. |

---

## 5. Verification Checklist Before Completing Any Task

Before marking a feature or PR complete, agents must verify:
1. **Type Check & Build:** `npm run build` succeeds with zero TypeScript errors.
2. **Backend Schema Check:** `POST /api/sarvam-auto-edit` with `USE_MOCK=true` returns valid JSON matching `EditPlan` schema.
3. **Asset Loading:** Dynamic sticker PNGs load in the browser canvas without `ERR_BLOCKED_BY_RESPONSE.NotSameOriginAfterDefaultedToSameOriginByCoep` console errors.
4. **Timeline Sync:** Captions, stickers, and SFX appear on separate draggable tracks in Timeline Studio and align with the spoken words in preview playback.
5. **Export Smoke Test:** Clicking Export produces a playable `.mp4` containing the cuts, burned karaoke captions, stickers, and SFX audio.
