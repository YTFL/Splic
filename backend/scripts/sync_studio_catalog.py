"""
Refresh backend/studio_catalog/ from timeline_studio/public/assets.

The Vercel backend service only bundles backend/, so the director's sticker
library and SFX vocabulary come from this committed snapshot there. Run this
after adding or removing bundled stickers or sound effects:

    python backend/scripts/sync_studio_catalog.py

`python -m pytest backend/test_suite.py` fails while the snapshot is stale.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BACKEND_DIR.parent / "timeline_studio" / "public" / "assets"
SNAPSHOT_DIR = BACKEND_DIR / "studio_catalog"


def sfx_stems() -> list[str]:
    return sorted(p.stem for p in (ASSETS_DIR / "sound-effects").glob("*.mp3"))


def main() -> None:
    manifest = ASSETS_DIR / "stickers" / "stickers-manifest.json"
    if not manifest.exists():
        raise SystemExit(f"Sticker manifest not found: {manifest}")
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(manifest, SNAPSHOT_DIR / "stickers-manifest.json")
    (SNAPSHOT_DIR / "sound-effects.json").write_text(json.dumps(sfx_stems(), indent=2) + "\n", encoding="utf-8")
    print(f"Synced studio catalog snapshot -> {SNAPSHOT_DIR}")


if __name__ == "__main__":
    main()
