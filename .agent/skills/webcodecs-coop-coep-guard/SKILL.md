---
name: webcodecs-coop-coep-guard
description: Preserve Cross-Origin Isolation (COOP/COEP) headers, Vite proxy rules, and WebCodecs memory limits in Timeline Studio so SharedArrayBuffer and MP4 export work reliably. Use when editing vite.config.ts, netlify.toml, backend CORS, or debugging blank exports/blocked assets.
---

# WebCodecs & COOP/COEP Guardrails

## Mandatory Headers
Timeline Studio relies on `SharedArrayBuffer` and WebWorkers for browser-native MP4 encoding. Every server serving the frontend MUST send:
```http
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

## Common Failure Modes & Fixes
1. **Dynamic Stickers Blocked in Browser (`ERR_BLOCKED_BY_RESPONSE`):**
   - *Cause:* `COEP: require-corp` blocks `<img>` or `fetch()` calls to `http://localhost:8000` if FastAPI lacks CORP headers.
   - *Fix:* Proxy `/api` and `/assets/dynamic_stickers` through `vite.config.ts` (`server.proxy`) so the browser treats them as same-origin, AND set `Cross-Origin-Resource-Policy: cross-origin` on FastAPI responses.
2. **Browser Tab Crash / OOM During Export:**
   - *Cause:* Feeding >60s or 4K horizontal video into WebCodecs canvas decoding.
   - *Fix:* Enforce a soft UI guard recommending 15–60s vertical `9:16` clips (`1080x1920` or `720x1280`) and downscale oversized dynamic sticker PNGs to `<= 512px` before loading onto the canvas.
3. **Local ONNX Whisper Stalling:**
   - *Rule:* Never invoke Timeline Studio's built-in browser Whisper model for auto-editing; route all audio to `/api/sarvam-auto-edit`.
