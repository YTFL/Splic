# Autonomous Video Auto-Editor for Indic Creators
### Project Architecture, Technical Specification & 24-Hour Hackathon Execution Blueprint

---

## 1. Executive Summary

Short-form video platforms (Instagram Reels, YouTube Shorts) have transformed the Indian creator economy, with over 40 million creators producing content in regional languages and code-mixed vernaculars (Hinglish, Tanglish, Kanglish). However, editing tools remain linguistically and culturally Western-centric. Platforms such as [CapCut](https://www.capcut.com/) and [Descript](https://www.descript.com/) cannot accurately transcribe code-mixed audio, fail to generate Romanized phonetic captions, offer zero asset recognition for Indian entities (e.g., Zomato, UPI, Biryani), and ignore Indic conversational pauses.

This project delivers an **Autonomous, Human-in-the-Loop Video Auto-Editor for Vernacular Creators**. By pairing [Sarvam AI's speech-and-reasoning stack](https://www.sarvam.ai/) with an open-source browser-based multi-track timeline ([Timeline Studio](https://github.com/MartinDelophy/ai-video-editor)), the system takes raw smartphone video footage and automatically:
1. Trims dead-air silence and Indic filler words.
2. Burns animated, word-by-word bouncing karaoke subtitles in Romanized Hinglish or dual-script (Indic + English translation).
3. Detects spoken Indian entities and dynamically scrapes images from the web, strips backgrounds in 300ms using local computer vision (`rembg`), and places custom transparent cutout stickers onto the timeline.
4. Drops contextual meme sound effects and camera punch-ins on punchlines.
5. Populates an interactive web timeline where the creator can review, nudge assets, edit captions, and export directly in the browser via WebCodecs.

---

## 2. The Problem & Market Failure

### 2.1 The Vernacular Creator Friction
* **The "Mute" Consumption Reality:** Over 85% of short-form mobile videos are consumed without sound. High-retention reels mandate dynamic, word-by-word animated captions.
* **The Transliteration Void:** Indian social media users read code-mixed language in Roman script (*"Aaj hum baat karenge..."* rather than Devanagari *"आज हम बात करेंगे..."*). Global ASR engines (OpenAI Whisper, Google Cloud Speech) force rigid Devanagari or English translation, hallucinating on colloquial code-switching.
* **Manual Asset Hunting:** Adding visual context (e.g., placing an icon of a samosa, a stock market chart, or an auto-rickshaw when mentioned) requires searching Google Images, downloading files, using background-removal tools, and manually keyframing them in editing software.
* **Time Sink:** A simple 30-second conversational reel requires 2 to 3 hours of manual timeline assembly.

### 2.2 Why Existing Tools Fail
| Dimension | Global Editors (CapCut, OpusClip, Descript) | Our Indic Auto-Editor Engine |
| :--- | :--- | :--- |
| **Code-Mixing ASR** | Hallucinates or drops Hindi words mid-sentence | [Sarvam Saaras v4](https://docs.sarvam.ai/api/api-guides-tutorials/models/saaras) (`mode="codemix"` / `"translit"`) |
| **Subtitle Script** | Enforces rigid Devanagari or English only | Native Romanized phonetic Hinglish karaoke captions |
| **Cultural Entities** | Western stickers (hot dogs, dollars, US memes) | Dynamic web discovery of Indian brands, food, and culture |
| **Output Flexibility** | Opaque black-box MP4 render (unfixable errors) | Interactive, multi-track web timeline (human-in-the-loop) |

---

## 3. End-to-End System Architecture

```
[User Smartphone Video (.mp4)]
          │
          ├─► 1. Web Audio Extraction (WAV @ 16kHz)
          │
          ▼
[Sarvam Saaras v4 STT Endpoint]
   ├── mode="translit" ──► Romanized Indic transcript
   └── word_timestamps        ──► Exact float timestamps per word
          │
          ▼
[Sarvam-105B Reasoning Director]
   ├── 1. Dead-Air & Filler Interval Detection (Silence > 0.8s, "matlab", "arre")
   ├── 2. Indian Cultural Entity Extraction (Brands, Food, Slang, Celebrities)
   └── 3. Comedic Punchline & SFX Mapping (Vine boom, Cash sound, Whoosh)
          │
          ▼
[Dynamic Asset Synthesis Pipeline]
   ├── Web Image Search (DuckDuckGo Search)
   ├── Background Removal (Local Python `rembg` U2-Net)
   └── RGBA Cutout PNG Generation (/public/assets/stickers/<entity>.png)
          │
          ▼
[Timeline Studio Command Runner (MCP / Transaction Engine)]
   ├── Track 1: Split & Ripple-Trimmed Video Clips
   ├── Track 2: Animated Word-by-Word Subtitle Blocks
   ├── Track 3: Overlay / Picture-in-Picture Cutout Stickers
   └── Track 4: Synced Meme Audio SFX
          │
          ▼
[In-Browser Interactive Multi-Track Timeline]
   ├── Real-time scrubbing & live preview
   ├── Creator nudges misplaced assets or edits typo
   └── 1-Click Export ──► WebCodecs/Canvas renders MP4 locally
```

---

## 4. Detailed Component Specifications

### 4.1 Speech & Captioning Engine
* **Model:** [Sarvam Saaras v4](https://docs.sarvam.ai/api/api-guides-tutorials/models/saaras)
* **Endpoint:** `POST https://api.sarvam.ai/speech-to-text`
* **Configuration:**
  * `model`: `saaras:v4`
  * `mode`: `translit`
  * `language_code`: `hi-IN` (or auto-detected across 22 Indic languages)
* **Payload Output:**
  ```json
  {
    "transcript": "Maine kal Zomato se Biryani mangwayi par paise double kat gaye",
    "words": [
      { "word": "Maine", "start_time": 0.42, "end_time": 0.78 },
      { "word": "kal", "start_time": 0.81, "end_time": 1.15 },
      { "word": "Zomato", "start_time": 1.25, "end_time": 1.72 },
      { "word": "se", "start_time": 1.75, "end_time": 1.95 },
      { "word": "Biryani", "start_time": 2.10, "end_time": 2.65 },
      { "word": "mangwayi", "start_time": 2.70, "end_time": 3.15 },
      { "word": "par", "start_time": 5.40, "end_time": 5.70 },
      { "word": "paise", "start_time": 5.75, "end_time": 6.10 },
      { "word": "double", "start_time": 6.15, "end_time": 6.60 },
      { "word": "kat", "start_time": 6.65, "end_time": 6.95 },
      { "word": "gaye", "start_time": 7.00, "end_time": 7.30 }
    ]
  }
  ```
* **Karaoke Synchronization:** Subtitles are grouped into 2- to 4-word reading chunks. In the video canvas, the active spoken word is highlighted in yellow with scale-bounce animation while unaccented words remain white with a subtle black border.

---

### 4.2 The AI Video Director (Reasoning & Editing Decisions)
* **Model:** [Sarvam-105B](https://docs.sarvam.ai/api/token-factory/models/sarvam-105b) (`sarvam-105b`, 128K context)
* **Endpoint:** `POST https://api.sarvam.ai/v2/chat/completions`
* **System Prompt:**
  ```
  You are an expert short-form viral video editor for Instagram Reels.
  Given a transcript with word-level start and end timestamps:
  1. Identify pauses > 0.8s or filler hesitation zones ("matlab", "uhm", "arre") to ripple-cut.
  2. Identify Indian brands, foods, celebrities, objects, and cultural terms to display as stickers.
  3. Identify comedic punchlines or shocking revelations to attach sound effects (vine_boom.mp3, cash.mp3, ding.mp3).
  4. Identify high-energy statements to apply 1.2x camera punch-in zooms.
  Output strictly in valid JSON matching the schema.
  ```
* **Director JSON Schema:**
  ```json
  {
    "cuts": [
      { "start": 3.15, "end": 5.40, "reason": "Dead air hesitation" }
    ],
    "stickers": [
      { "keyword": "Zomato", "start": 1.25, "duration": 2.0, "position": {"x": 0.5, "y": 0.3} },
      { "keyword": "Biryani", "start": 2.10, "duration": 2.0, "position": {"x": 0.7, "y": 0.4} },
      { "keyword": "Money", "start": 5.75, "duration": 1.8, "position": {"x": 0.5, "y": 0.3} }
    ],
    "sfx": [
      { "asset": "vine_boom.mp3", "start": 6.65, "volume": 0.8 }
    ],
    "zooms": [
      { "start": 6.65, "end": 7.30, "scale": 1.25 }
    ]
  }
  ```

---

### 4.3 Dynamic Web-Scraped Sticker & Background Removal Pipeline
Instead of relying on a static, pre-packaged asset folder, the backend dynamically fetches transparent assets for any named entity in real time:

1. **Entity Search:** When Sarvam-105B identifies an entity (e.g., *"Royal Enfield Bullet"* or *"Vada Pav"*), Python searches for transparent images using DuckDuckGo search:
   ```python
   from duckduckgo_search import DDGS
   with DDGS() as ddgs:
       results = list(ddgs.images(f"{keyword} isolated png sticker", max_results=1))
   ```
2. **Local Background Stripping:** If the retrieved image has a background, it is passed through `rembg` (U2-Net / BirefNet):
   ```python
   from rembg import remove
   from PIL import Image

   clean_image = remove(raw_pil_image)
   clean_image.save(f"public/assets/stickers/{entity_slug}.png")
   ```
3. **Local Disk Caching:** Assets are cached on disk so identical entities across test runs avoid duplicate downloads.

---

### 4.4 The Multi-Track Web Timeline Engine
* **Base Repository:** [Timeline Studio (`MartinDelophy/ai-video-editor`)](https://github.com/MartinDelophy/ai-video-editor)
* **Architecture:** React + TypeScript + WebCodecs. Runs entirely inside the client browser.
* **Command Contract:** The backend output translates directly into Timeline Studio's native track operations:
  * `timeline_split_clip(clip_id, timestamp)`
  * `timeline_add_overlay(asset_url, start, duration, x, y, scale)`
  * `timeline_add_caption(words, start, duration, style)`
  * `timeline_add_audio(sfx_url, start, volume)`
* **Human-in-the-Loop Value:** The creator sees every AI decision visualized on draggable tracks. If a sticker is positioned slightly over the speaker's face, the creator drags it across the canvas or adjusts its start point on the timeline.

---

## 5. Credit Economics & Hybrid Fallback Strategy

### 5.1 Hackathon Credit Budget (500 Credits = ₹500 INR)
On Sarvam AI, ₹1 INR equals 1 API credit. Costs for short-form video auto-editing are exceptionally low:

* **Sarvam Saaras v4 (STT):** ₹0.49 per audio minute.
  * *Per 30-second reel:* ₹0.245 (less than 25 paise).
* **Sarvam-105B (LLM):** ₹15/1M input tokens, ₹60/1M output tokens.
  * *Per reel analysis (~700 tokens total):* ~₹0.02 (2 paise).
* **Total Cost per 30-second Reel:** **~₹0.27 INR**.
* **Total Capacity:** 500 credits allows over **1,800 full video pipeline runs**, ensuring zero risk of credit exhaustion during the hackathon.

### 5.2 Zero-Credit Development & Hybrid Fallback
To safeguard API credits and avoid waiting on network calls during frontend/CSS development:
1. **Stubbed Tests, Live Runs Only on Demand:** Automated tests stub the Sarvam HTTP layer; real Sarvam calls happen only when a user runs Auto-Cut. Iterate on timeline styling using the already-applied tracks (with undo) instead of re-running the pipeline.
2. **Local Silence Detection:** Run acoustic silence cuts using `pydub.silence.detect_silence()` locally in Python (0 API cost, executed in 40ms on CPU).
3. **LLM Fallback:** Implement a runtime fallback toggle to Groq (Llama-3.3-70B) or Google Gemini API if network timeouts occur during the live judging round.

---

## 6. 24-Hour Implementation Roadmap

```
Hours 00:00 - 04:00 │ Phase 1: Environment Setup & Core Glue Script
                    │ • Clone & verify MartinDelophy/ai-video-editor build (`npm run dev`)
                    │ • Write standalone Python FastAPI server (`app.py`)
                    │ • Hook up Sarvam Saaras v4 (`mode="translit"`)
                    │ • Test JSON output structure on a 20-second sample video

Hours 04:00 - 08:00 │ Phase 2: Video Director & Asset Pipeline
                    │ • Write Sarvam-105B system prompt with strict JSON schema
                    │ • Implement dynamic web scraping + `rembg` background removal
                    │ • Build static fallback library of 20 top Indian stickers & 5 sound effects

Hours 08:00 - 14:00 │ Phase 3: Timeline Studio Integration
                    │ • Add "⚡ Auto-Cut" button to Timeline Studio toolbar
                    │ • Wire FastAPI response to Timeline Studio's track insertion dispatchers
                    │ • Verify ripple-cuts, caption track creation, and overlay tracks in browser

Hours 14:00 - 18:00 │ Phase 4: UI Polish, Styling & WebCodecs Verification
                    │ • Style karaoke captions (yellow highlight, bold font, drop shadow)
                    │ • Test client-side MP4 export via WebCodecs
                    │ • Verify cross-origin isolation headers for browser workers

Hours 18:00 - 21:00 │ Phase 5: Demo Rehearsal & Fallback Testing
                    │ • Record 2 real-world demo test clips in code-mixed Hinglish
                    │ • Verify cached responses and fallback mode switches
                    │ • Stress-test dynamic sticker generation on random judge inputs

Hours 21:00 - 24:00 │ Phase 6: Slide Deck & Presentation Polish
                    │ • Polish 5-slide deck highlighting the cultural gap of Western editors
                    │ • Rehearse live 2-minute stage pitch
```

---

## 7. The Winning Stage Pitch & Live Demo Script

### The Opening Hook (30 Seconds)
> *"Judges, over 40 million Indian creators make reels every day in Hinglish, Tamil, and Kannada. Over 85% of their audience watches on mute. Yet, if you open CapCut or Descript today, they are completely blind to Indian creators. They garble code-mixed speech, cannot generate Romanized Hinglish captions, and have zero stickers for Indian brands or cultural terms.*
> *Creators spend 3 hours per video doing manual, repetitive grunt work. Today, we built the first autonomous, human-in-the-loop video editor designed specifically for vernacular India, powered by Sarvam AI."*

### The Live Stage Action (60 Seconds)
1. **The Raw Footage:** Play a raw 20-second smartphone video of a teammate speaking colloquial Hinglish with long pauses:
   > *"Maine kal Zomato se Biryani mangwayi... (awkward silence)... par delivery wale ne paise extra maang liye."*
2. **The 1-Click Execution:** Click **"⚡ Auto-Cut"**.
3. **The Reveal (3 Seconds Later):**
   * The awkward silence is cleanly jump-cut.
   * Dynamic, bouncing Romanized karaoke captions appear: *"Maine kal Zomato se Biryani mangwayi..."*
   * A cut-out **Zomato** logo and steaming **Biryani** sticker pop up at the exact spoken timestamps.
   * A **cash register / vine boom** sound effect plays on *"paise extra maang liye"*.
4. **The Human-in-the-Loop Differentiator:** Show the judge that it is not an unfixable black-box video: scrub the timeline, nudge the Biryani sticker 1 second to the right with the mouse, edit a typo in the caption, and hit **Export MP4**.

---

## 8. Summary Table of Key Resources & Repositories

| Component | Technology / Repository | Role in Project |
| :--- | :--- | :--- |
| **Indic Speech-to-Text** | [Sarvam Saaras v4](https://docs.sarvam.ai/api/api-guides-tutorials/models/saaras) | Transcribes code-mixed audio with word timestamps in Romanized script |
| **Indic Reasoning Director** | [Sarvam-105B](https://docs.sarvam.ai/api/token-factory/models/sarvam-105b) | Analyzes timestamps, cuts silence, identifies entities, and plans SFX |
| **Interactive Video Timeline** | [Timeline Studio (MartinDelophy)](https://github.com/MartinDelophy/ai-video-editor) | Browser-based multi-track timeline, canvas preview, and WebCodecs export |
| **Background Removal** | [rembg](https://github.com/danielgatis/rembg) | Converts scraped web images into transparent cutout PNG stickers |
| **Web Image Discovery** | `duckduckgo_search` | Real-time image discovery for mentioned Indian entities |
| **Backend Orchestrator** | FastAPI / Python | Coordinates API calls, asset caching, and timeline JSON dispatching |
