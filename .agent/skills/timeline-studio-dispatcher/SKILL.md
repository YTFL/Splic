---
name: timeline-studio-dispatcher
description: Wire the Sarvam EditPlan JSON into the forked MartinDelophy/ai-video-editor (Timeline Studio) multi-track state store, including ripple cuts, animated Romanized karaoke captions, overlay stickers, and meme SFX. Use when modifying src/ components or timeline dispatchers.
---

# Timeline Studio Dispatcher & Karaoke Captions

## Purpose
Connects the `"⚡ Auto-Cut"` UI button in Timeline Studio to the FastAPI `/api/sarvam-auto-edit` endpoint and translates the returned `EditPlan` JSON into editable tracks on the browser timeline.

## Surgical Integration Rules
- **Do NOT rewrite** the core WebCodecs exporter, WebGPU shaders, or color-grading panels.
- **Inspect First:** Locate the existing track/clip mutation actions in `src/store` or `src/features/timeline` (and check `.agent/skills/edit-timeline-studio` for exact action names).

## Timestamp Synchronization (Critical)
When applying `cuts` (ripple-deletes):
1. **Option A (Preferred):** Insert `captions`, `stickers`, `sfx`, and `zooms` onto their tracks **before** executing ripple-deletes, if Timeline Studio's ripple-delete automatically shifts downstream track items.
2. **Option B (Explicit Offset):** If Timeline Studio's split/delete only affects the main video track, sort `cuts` ascending and subtract cumulative removed duration from all downstream `start` / `end` timestamps before inserting overlays, captions, and SFX.
3. Always verify which behavior the store implements before finalizing the dispatcher.

## Romanized Hinglish Karaoke Captions
- Group `words` into 2-to-4 word display chunks (max ~1.8s per chunk) so captions stay punchy on 9:16 reels.
- Style active spoken word in bright yellow (`#FFD600`) with a subtle scale pop (`1.08x`), inactive words in crisp white (`#FFFFFF`), and a heavy black stroke/drop shadow (`#000000`) for readability over any video background.
- Place captions in the lower-middle safe zone (`y: 0.72` to `0.78`) to avoid Instagram Reels / YouTube Shorts UI overlays at the bottom.
