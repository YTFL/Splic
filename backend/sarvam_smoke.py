"""sarvam_smoke.py — one Sarvam chat completion, nothing else.

Run from the repository root:
    backend/.venv/Scripts/python backend/sarvam_smoke.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv(Path(__file__).resolve().parent / ".env")

api_key = os.getenv("SARVAM_API_KEY", "").strip()
if not api_key:
    sys.exit("SARVAM_API_KEY is not set (add it to backend/.env).")

client = SarvamAI(api_subscription_key=api_key)

response = client.chat.completions(
    model="sarvam-105b",
    messages=[{"role": "user", "content": "Say hello in one short Hinglish sentence."}],
)

print(response.choices[0].message.content)
