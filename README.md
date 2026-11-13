# Splic ⚡

> **Autonomous, Human-in-the-Loop Indic Short-Form Video Auto-Editor**  
> Powered by **Sarvam AI** and **Timeline Studio** (WebCodecs multi-track canvas editor).

---

## Overview

Over 40 million Indian content creators publish short-form vertical videos (Instagram Reels, YouTube Shorts) in code-mixed vernaculars (*Hinglish, Tanglish, Kanglish*). Existing automated editors fail for Indic creators because they:
1. Cannot transcribe rapid code-mixed speech accurately.
2. Force formal Devanagari/regional scripts instead of the **Romanized phonetic captions** (*"Aaj hum baat karenge..."*) that Indian social audiences read.
3. Lack awareness of Indian cultural entities, brands, foods, and references (*Zomato, UPI, Biryani, Auto-rickshaw, Chai*).
4. Miss Indian conversational filler words (*"matlab"*, *"arre"*, *"toh basically"*) and meme timing.

**Splic** solves this with a **1-click "⚡ Auto-Cut"** workflow that orchestrates **Sarvam Saaras v4** (speech-to-text with Romanized transliteration), **Sarvam-105B** (AI video director), local silence detection, dynamic sticker synthesis (`rembg`), and sound effects directly into an interactive browser timeline.

---

## Key Features

- **⚡ 1-Click Auto-Cut:** Upload a 9:16 vertical video and generate a full multi-track edit plan in seconds.
- **🗣️ Romanized Indic Karaoke Captions:** Word-level synchronized captions in phonetic Latin script (Hinglish/Tanglish/Kanglish) with active word highlights.
- **✂️ Smart Ripple Cuts:** Removes dead-air pauses (> 0.8s) and vernacular filler hesitations without awkward clip jumps.
- **🎨 Dynamic Indian Stickers:** Automatically discovers cultural entities, searches relevant images, removes backgrounds via `rembg`, and places transparent stickers onto timeline overlay tracks.
- **🔊 Meme SFX & Punch-In Zooms:** Contextual meme sound effects (`vine_boom`, `cash`, `ding`) and punch-in zoom keyframes aligned with comedic or dramatic moments.
- **🤝 100% Human-in-the-Loop:** Every edit lands as a draggable, editable track on Timeline Studio's canvas. Creators can scrub, adjust timing, edit text, and export directly in-browser using WebCodecs.

---

## Project Architecture

```text
┌──────────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + TypeScript + Vite)              │
│  Forked Timeline Studio (WebCodecs + Multi-Track Canvas Timeline)    │
│  • "⚡ Auto-Cut" Toolbar Button                                 │
│  • Dispatches JSON Edit Plan into Timeline Tracks                    │
│  • Interactive Drag/Drop, Caption Editing & Client-Side MP4 Export   │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ POST /api/sarvam-auto-edit (audio/video)
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    BACKEND (Python + FastAPI)                        │
│  1. Local Silence Pre-Check: pydub.silence.detect_silence() (0 cost) │
│  2. Speech-to-Text: Sarvam Saaras v4 (mode="translit")        │
│  3. Video Director LLM: Sarvam-105B (JSON Mode)        │
│  4. Dynamic Sticker Pipeline: duckduckgo_search + rembg + Disk Cache │
│  5. Resilience: Groq/Gemini LLM fallback + offline heuristic director│
└──────────────────────────────────────────────────────────────────────┘
```

---

## Getting Started

### 1-Click Launch (Recommended)

Run both the FastAPI backend and Next.js frontend concurrently with a single command:

**macOS & Linux:**
```bash
./run.sh
```

**Windows (Command Prompt / Double-Click):**
```cmd
run.bat
```

**Windows (PowerShell):**
```powershell
.\run.ps1
```

The runner automatically:
1. Validates Node.js and Python (3.10+) installations.
2. Creates and configures the Python virtual environment (`backend/.venv`) if missing.
3. Installs backend and frontend dependencies if needed.
4. Generates initial `.env` files from the templates (add your `SARVAM_API_KEY` to `backend/.env`).
5. Launches FastAPI on [http://localhost:8000](http://localhost:8000) (Docs at [/docs](http://localhost:8000/docs)).
6. Launches Next.js on [http://localhost:3000](http://localhost:3000).
7. Gracefully stops all services when you press `Ctrl+C`.

---

### Manual Setup (Alternative)

#### 1. Prerequisites
- Node.js 20+ and `npm`
- Python 3.10+ (for FastAPI backend)

#### 2. Frontend (Timeline Studio)
```bash
cd timeline_studio
npm install
npm run dev        # Starts Next.js dev server on port 3000
npm run build      # Production bundle check
```

#### 3. Backend (FastAPI + Sarvam AI)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Environment Configuration (`backend/.env`)
```env
SARVAM_API_KEY=your_sarvam_api_subscription_key   # Required; restart the backend after changing it
FALLBACK_PROVIDER=none      # Optional: "groq" | "gemini"
```

---

## Documentation

- [AGENTS.md](agents.md) — Agentic development rules, guardrails, and verification workflows.
- [GEMINI.md](gemini.md) — Architectural design, API contracts, and constraints.
- [indic_video_auto_editor_spec.md](indic_video_auto_editor_spec.md) — Technical product specification.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
