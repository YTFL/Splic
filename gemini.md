# GEMINI.md — Project Context & Engineering Guide

## 1. Project Overview

This repository is a fork of **Timeline Studio** ([`MartinDelophy/ai-video-editor`](https://github.com/MartinDelophy/ai-video-editor)), extended into an **Autonomous, Human-in-the-Loop Video Auto-Editor for Indic Creators**.

### Problem Solved
Over 40 million Indian creators produce short-form vertical videos (Instagram Reels, YouTube Shorts) in code-mixed vernaculars (Hinglish, Tanglish, Kanglish). Global editors (CapCut, Descript, OpusClip) fail this market because they:
1. Cannot transcribe rapid code-mixed speech accurately.
2. Force formal Devanagari/regional scripts instead of the **Romanized phonetic captions** (*"Aaj hum baat karenge..."*) that Gen-Z and Indian social audiences actually read.
3. Have zero sticker/asset awareness for Indian cultural entities (e.g., Zomato, UPI, Biryani, Auto-rickshaw, Chai).
4. Miss Indian conversational filler words (*"matlab"*, *"arre"*, *"toh basically"*) and meme timing.

### Solution
A 1-click **"⚡ Desi Auto-Cut"** workflow inside a browser-native multi-track video timeline:
1. **Extract & Transcribe:** Extracts audio from uploaded 9:16 smartphone clips (15–60s) and calls **Sarvam Saaras v4** (`mode="transliteration"`) to obtain Romanized Indic text with millisecond-level word timestamps.
2. **AI Video Director:** Sends the timestamped transcript to **Sarvam-105B Conversations** (`/v2/chat/completions`), which outputs a strict JSON edit plan containing:
   - **Ripple Cuts:** Dead-air silences (> 0.8s) and Indic filler phrases.
   - **Karaoke Captions:** Word-by-word Romanized Hinglish (and optional English translation) blocks.
   - **Dynamic Stickers:** Mentioned Indian entities, brands, foods, or celebrities.
   - **Meme SFX & Punch-In Zooms:** Contextual sound effects (`vine_boom.mp3`, `cash.mp3`, `ding.mp3`) and `1.25x` scale keyframes.
3. **Dynamic Asset Synthesis:** For every detected entity, the Python backend searches for an image via `duckduckgo_search`, removes the background locally in ~300ms using `rembg`, caches the transparent RGBA PNG to disk, and returns its asset URL.
4. **Human-in-the-Loop Timeline:** Instead of rendering an uneditable black-box MP4, the edit plan populates Timeline Studio's interactive tracks (Video, Captions, Overlay/PiP, Audio SFX). The creator can scrub, nudge stickers, fix typos, and export MP4 directly in the browser via WebCodecs.

---

## 2. System Architecture

```text
┌──────────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + TypeScript + Vite)              │
│  Forked Timeline Studio (WebCodecs + Multi-Track Canvas Timeline)    │
│  • "⚡ Desi Auto-Cut" Toolbar Button                                 │
│  • Dispatches JSON Edit Plan into Timeline Tracks                    │
│  • Interactive Drag/Drop, Caption Editing & Client-Side MP4 Export   │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ POST /api/sarvam-auto-edit (audio/video)
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    BACKEND (Python + FastAPI)                        │
│  1. Local Silence Pre-Check: pydub.silence.detect_silence() (0 cost) │
│  2. Speech-to-Text: Sarvam Saaras v4 (mode="transliteration")        │
│  3. Video Director LLM: Sarvam-105B Conversations (JSON Mode)        │
│  4. Dynamic Sticker Pipeline: duckduckgo_search + rembg + Disk Cache │
│  5. Dev/Demo Safety: USE_MOCK cache & Groq/Gemini LLM fallback       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. AI Models & API Contracts

### 3.1 Speech-to-Text: Sarvam Saaras v4
- **Endpoint:** `POST https://api.sarvam.ai/speech-to-text`
- **Auth Header:** `api-subscription-key: <SARVAM_API_KEY>`
- **Form Fields:**
  - `model`: `"saaras:v4"`
  - `mode`: `"transliteration"` *(Critical: outputs Romanized Indic script rather than Devanagari/Tamil script; use `"translate"` if generating secondary English subtitle tracks)*
  - `language_code`: `"hi-IN"` (or `"unknown"` / auto-detect across 22+ Indic languages)
- **Expected Output:** `transcript` string + word-level timestamps (`start_time`, `end_time`, `word`).

### 3.2 AI Video Director: Sarvam-105B Conversations
- **Endpoint:** `https://api.sarvam.ai/v2/chat/completions` (OpenAI-compatible)
- **Model ID:** `"sarvam-105b-conversations"` (or `"sarvam-105b"` for deeper reasoning; budget/speed fallback on Token Factory: `"glm-5.3-flash"` or `"deepseek-v4.1-flash-1017"`)
- **Required Output Schema (`response_format={"type": "json_object"}`):**
```json
{
  "cuts": [
    { "start": 3.15, "end": 5.40, "reason": "Dead air hesitation" }
  ],
  "stickers": [
    {
      "keyword": "Zomato",
      "asset": "/assets/dynamic_stickers/zomato.png",
      "start": 1.25,
      "duration": 2.0,
      "position": { "x": 0.5, "y": 0.3 }
    }
  ],
  "sfx": [
    { "asset": "/assets/sfx/vine_boom.mp3", "start": 6.65, "volume": 0.8 }
  ],
  "zooms": [
    { "start": 6.65, "end": 7.30, "scale": 1.25 }
  ]
}
```

### 3.3 Dynamic Sticker Synthesis
- **Search:** `duckduckgo_search.DDGS().images(f"{keyword} transparent png sticker", max_results=1)`
- **Background Removal:** `rembg.remove(pil_image)` running locally on CPU.
- **Caching:** Save as `public/assets/dynamic_stickers/<slug>.png`. Always check disk cache before scraping.
- **Static Fallbacks:** Maintain a curated `public/assets/stickers/` and `public/assets/sfx/` (`vine_boom.mp3`, `cash.mp3`, `ding.mp3`, `record_scratch.mp3`) in case web scraping times out.

---

## 4. Critical Technical Constraints & Guardrails

1. **Cross-Origin Isolation Headers (Mandatory for WebCodecs/SharedArrayBuffer):**
   The frontend uses browser WebWorkers and `SharedArrayBuffer` for video encoding. Any dev server, proxy, or deployment (`vite.config.ts`, `netlify.toml`, `vercel.json`) MUST preserve:
   ```http
   Cross-Origin-Opener-Policy: same-origin
   Cross-Origin-Embedder-Policy: require-corp
   ```
   When serving dynamic stickers or audio from the FastAPI backend to the Vite frontend, ensure CORS and `Cross-Origin-Resource-Policy: cross-origin` headers are set on static asset responses so `COEP: require-corp` does not block sticker loading.

2. **Bypass Built-In Local Whisper:**
   Timeline Studio includes an experimental in-browser ONNX Whisper model that is slow and fails on Hinglish. Do NOT route auto-edit transcription through it; always route audio to the FastAPI `/api/sarvam-auto-edit` endpoint.

3. **Short-Form Scope (15–60 Seconds):**
   Browser WebCodecs memory is bounded. Target 9:16 vertical clips between 15 and 60 seconds at 1080p.

4. **Credit Conservation (500 Credits = ₹500 INR):**
   - `saaras:v4` costs ~₹0.49/min (~₹0.25 per 30s reel).
   - `sarvam-105b-conversations` costs ₹15/1M input & ₹60/1M output (~₹0.02 per reel).
   - **Rule:** Never burn live Sarvam API credits during UI/CSS/timeline debugging. Use `USE_MOCK=true` with a cached `sample_edit_plan.json` for frontend iteration. Use `pydub` locally for raw silence detection.

---

## 5. Planned Repository Layout

```text
.
├── src/                          # Forked Timeline Studio React/TS frontend
│   ├── features/timeline/        # Timeline state store & track dispatchers
│   ├── components/               # Add "⚡ Desi Auto-Cut" toolbar button here
│   └── ...
├── public/
│   └── assets/
│       ├── stickers/             # Pre-bundled fallback Indian PNG stickers
│       ├── dynamic_stickers/     # Runtime-generated rembg PNG cutouts (gitignored)
│       └── sfx/                  # Meme sound effects (vine_boom.mp3, cash.mp3, ding.mp3)
├── backend/                      # Python FastAPI orchestrator
│   ├── main.py                   # /api/sarvam-auto-edit & static asset serving
│   ├── sarvam_client.py          # Saaras v4 STT + Sarvam-105B Director + Mock/Groq fallback
│   ├── sticker_engine.py         # DuckDuckGo search + rembg + disk cache
│   ├── silence_detector.py       # Local pydub silence detection
│   ├── sample_edit_plan.json     # Cached Sarvam response for zero-credit dev mode
│   └── requirements.txt
├── GEMINI.md                     # This file
└── AGENTS.md                     # Agentic development rules & task workflow
```
