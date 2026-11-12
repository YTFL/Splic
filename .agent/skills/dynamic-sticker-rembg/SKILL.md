---
name: dynamic-sticker-rembg
description: Implement real-time web image scraping (duckduckgo_search), local background removal (rembg), disk caching, and static asset fallbacks for Indian cultural entities. Use when building or debugging backend/sticker_engine.py or sticker asset serving.
---

# Dynamic Sticker Synthesis (`duckduckgo_search` + `rembg`)

## Purpose
Turns any Indian brand, food, celebrity, or slang entity extracted by Sarvam-105B (e.g., `"Zomato"`, `"Vada Pav"`, `"Royal Enfield"`) into a transparent RGBA PNG sticker in ~300ms with zero paid image APIs.

## Implementation Workflow
1. **Normalize & Check Cache First:**
   - Convert `keyword` to a safe slug: `re.sub(r"[^a-z0-9]+", "_", keyword.lower()).strip("_")`.
   - Check `public/assets/dynamic_stickers/<slug>.png`. If it exists, return `/assets/dynamic_stickers/<slug>.png` immediately.
2. **Search Web Image:**
   - Query `DDGS().images(f"{keyword} transparent png sticker", max_results=2)`.
   - Enforce a strict `timeout=4` seconds on `requests.get(image_url)` so a slow CDN never stalls the 3-second auto-edit demo.
3. **Strip Background Locally:**
   - Open bytes with `PIL.Image.open(BytesIO(resp.content)).convert("RGBA")`.
   - Resize oversized images (`max_dim = 512`) **before** calling `rembg.remove()` to keep CPU inference under 300ms and prevent WebCodecs canvas bloat.
   - Save output as PNG to `public/assets/dynamic_stickers/<slug>.png`.
4. **Graceful Fallback:**
   - Wrap the entire fetch + `rembg` block in `try/except`.
   - On failure or timeout, check `public/assets/stickers/` for a closest static match (e.g., `money.png`, `fire.png`, `food.png`) or return `None` and drop that single sticker cleanly.

## Browser COEP Compatibility
Because Timeline Studio enforces `Cross-Origin-Embedder-Policy: require-corp`, do NOT serve dynamic stickers from an unproxied cross-origin port without `Cross-Origin-Resource-Policy: cross-origin`. Prefer routing `/assets/dynamic_stickers` through the Vite dev proxy or saving directly into Timeline Studio's `public/assets/dynamic_stickers/` directory.
