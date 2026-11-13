---
name: sarvam-indic-pipeline
description: Build and test the Sarvam AI speech-to-text (Saaras v4) and video director LLM (Sarvam-105B Conversations) backend pipeline with stubbed offline tests and local pydub silence detection. Use when implementing or modifying backend/sarvam_client.py, backend/silence_detector.py, or backend/schemas.py.
---

# Sarvam Indic Video Pipeline

## Purpose
Orchestrates audio transcription (`saaras:v4`), silence detection (`pydub`), and structured video edit planning (`sarvam-105b`) for 15-60s Indic short-form reels while protecting the 500-credit (INR 500) hackathon budget.

## Exact API Contracts

### 1. Speech-to-Text (`saaras:v4`)
- **Endpoint:** `POST https://api.sarvam.ai/speech-to-text`
- **Headers:** `{"api-subscription-key": os.environ["SARVAM_API_KEY"]}`
- **Multipart Form Data:**
  - `file`: 16kHz mono `.wav` extracted from the uploaded `.mp4`
  - `model`: `"saaras:v4"`
  - `mode`: `"translit"` (outputs Romanized Hinglish/Tanglish/Kanglish rather than Devanagari)
  - `language_code`: `"hi-IN"` (or `"unknown"` for auto-detect)
- **Optional Dual-Subtitle Call:** Only if dual English captions are toggled on, run a secondary pass with `mode="translate"` or translate the grouped caption chunks.

### 2. AI Video Director (`sarvam-105b`)
- **Endpoint:** `https://api.sarvam.ai/v2/chat/completions` (OpenAI SDK compatible)
- **Model:** `"sarvam-105b"` (128K context; open-weight alternatives on `/v2`: `"glm5.3"` or `"deepseekv4.1-flash-1017"`)
- **Required Parameter:** `response_format={"type": "json_object"}` and `temperature=0.2`

## Credit-Saving Rules (Mandatory)
1. **Stub, Don't Spend:** There is no mock mode. Automated tests must patch `sarvam_client._stt_request` / `_call_sarvam` (see `backend/test_suite.py`); live calls happen only on manual runs with `SARVAM_API_KEY` set in `backend/.env`.
2. **Local Silence Detection First:** Run `pydub.silence.detect_silence(audio, min_silence_len=450, silence_thresh=-36)` locally in Python (0 credits, ~40ms) and pass those candidate intervals to the director or merge them directly into `cuts`.
3. **Pydantic Validation:** Validate every LLM JSON response against `EditPlan` in `backend/schemas.py` before returning to the frontend.

## Required Output Schema (`EditPlan`)
```json
{
  "transcript": "string",
  "words": [{ "word": "string", "start_time": 0.42, "end_time": 0.78 }],
  "cuts": [{ "start": 3.15, "end": 5.40, "reason": "Dead air hesitation" }],
  "stickers": [{ "keyword": "Zomato", "asset": "/assets/dynamic_stickers/zomato.png", "start": 1.25, "duration": 2.0, "position": { "x": 0.5, "y": 0.3 } }],
  "sfx": [{ "asset": "/assets/sfx/vine_boom.mp3", "start": 6.65, "volume": 0.8 }],
  "zooms": [{ "start": 6.65, "end": 7.30, "scale": 1.25 }]
}
```
