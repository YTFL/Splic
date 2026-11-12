---
name: edit-timeline-studio
description: Domain skill for Timeline Studio multi-track timeline mutations, ripple cuts, karaoke subtitles, dynamic sticker overlays, meme SFX audio, WebCodecs safety, and COEP/CORP compliance.
category: video-editor
risk: safe
source: sickn33/agentic-awesome-skills
date_added: "2026-11-12"
author: Splic Team
tags:
  - video-editor
  - timeline
  - webcodecs
  - canvas
  - captions
  - multi-track
tools:
  - antigravity
  - claude-code
  - cursor
  - gemini-cli
---

# Edit Timeline Studio (Multi-Track Video Auto-Editor)

Domain-specific guidance for mutating **Timeline Studio** (`MartinDelophy/ai-video-editor`) tracks and state without breaking browser-native WebCodecs, WebGPU shaders, or timeline synchronization.

---

## 1. Golden Architectural Guardrails

1. **NEVER Rewrite Core Engine Pipelines:**
   - Do NOT refactor the WebCodecs encoder, WebWorker renderers, WebGPU shaders, color grading wheels, or depth map pipelines.
   - All auto-edit mutations MUST be dispatched as track actions against the existing timeline store (`src/store` or `src/features/timeline`).

2. **100% Human-in-the-Loop:**
   - AI never outputs a locked, black-box MP4 directly.
   - All AI actions (cuts, text, stickers, audio, zooms) MUST land as distinct, draggable, editable elements on timeline tracks.

3. **Strict Timestamp Discipline (Float Seconds):**
   - All timestamps across backend and frontend must be floating-point seconds (e.g., `1.25`, NOT `"00:01:25"`).
   - Precision: Round or match to millisecond precision (`0.001s`).

4. **COEP & CORP Asset Isolation:**
   - Timeline Studio runs with `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp`.
   - Any external asset (sticker PNG, SFX MP3) loaded from the backend MUST either:
     - Be proxied via Vite (`/api` and `/dynamic_stickers` -> `http://localhost:8000`), OR
     - Include the `Cross-Origin-Resource-Policy: cross-origin` response header.

---

## 2. Multi-Track Layout Contract

The Timeline Studio canvas organizes media across dedicated horizontal tracks:

| Track Index | Type | Purpose | Dispatcher Action |
| :--- | :--- | :--- | :--- |
| **Track 1** | `video` | Primary user video footage | Split clip, ripple-delete intervals |
| **Track 2** | `text` / `caption` | Bouncing Romanized Hinglish karaoke subtitles | Add text element with word-level highlight keyframes |
| **Track 3** | `overlay` / `pip` | Transparent PNG stickers (Indian entities/brands) | Add image overlay with `{ x, y, width, height, duration }` |
| **Track 4** | `audio` | Contextual meme SFX (`vine_boom.mp3`, `ding.mp3`) | Add audio clip with start time and volume |
| **Keyframes** | `transform` | Punch-in zoom keyframes (`1.25x` scale on video) | Insert scale transform keyframes on Track 1 |

---

## 3. EditPlan JSON Dispatcher Workflow

When `/api/sarvam-auto-edit` returns an `EditPlan` JSON:

```json
{
  "cuts": [
    { "start": 3.15, "end": 5.40, "reason": "Dead air hesitation" }
  ],
  "captions": [
    {
      "start": 0.42,
      "end": 3.15,
      "text": "Maine kal Zomato se Biryani mangwayi",
      "words": [
        { "word": "Maine", "start_time": 0.42, "end_time": 0.78 },
        { "word": "kal", "start_time": 0.81, "end_time": 1.15 }
      ]
    }
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

### Ripple Cut Synchronization Rule
Timeline Studio handles clip cuts. When multiple cuts are applied:
- **Strategy A (Recommended):** Apply all tracks (captions, stickers, sfx) using the **original recording clock**, THEN perform ripple deletes from **right-to-left** (latest timestamp to earliest), adjusting timeline items to maintain perfect lip-sync.
- **Strategy B:** If Timeline Studio splits clips without automatic downstream ripple shift, compute cumulative cut offsets:
  $$\Delta t(t) = \sum_{cut_i.end \le t} (cut_i.end - cut_i.start)$$
  $$t_{post-cut} = t_{original} - \Delta t(t)$$

---

## 4. UI Trigger Integration ("⚡ Desi Auto-Cut")

- Place the trigger button in the main Timeline Studio header / toolbar alongside existing actions (Export, Import).
- Visual Style: Primary accent badge, high contrast, matching existing zinc/slate dark theme.
- States:
  - **Idle:** `"⚡ Desi Auto-Cut"`
  - **Analyzing Audio:** Spinner + `"Transcribing Hinglish (Sarvam Saaras)..."`
  - **Directing Video:** Spinner + `"Detecting Entites & Cuts (Sarvam-105B)..."`
  - **Synthesizing Assets:** Spinner + `"Generating Cutout Stickers..."`
  - **Done:** Success toast + All tracks populated and ready to scrub.
- Allow 1-click Undo: Wrap the entire auto-cut action in a single history batch if the store supports undo/redo transactions.

