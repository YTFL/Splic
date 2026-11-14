"""Local media store for rendered reels awaiting social publishing.

Instagram cannot accept a file upload: its Graph API containers require a
publicly reachable media URL. Rendered videos are therefore written to a local
directory and served by the backend at ``/media/<id>``; the public origin comes
from ``PUBLIC_MEDIA_BASE_URL`` so a tunnel or deployed host can expose it.
YouTube uploads read the same staged file directly.
"""

import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import Settings, get_settings

logger = logging.getLogger("composio.media_store")

ALLOWED_VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}


class MediaStoreError(ValueError):
    """Raised when an uploaded media file cannot be staged safely."""


class MediaStore:
    """Stages uploaded videos on disk and exposes their public URL."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    @property
    def root(self) -> Path:
        directory = self.settings.media_root
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @property
    def max_bytes(self) -> int:
        return max(1, int(self.settings.MAX_UPLOAD_MB)) * 1024 * 1024

    def save(self, filename: Optional[str], content: bytes) -> Dict[str, Any]:
        """Write ``content`` to the media directory and return its descriptor."""
        if not content:
            raise MediaStoreError("The rendered video upload was empty.")

        suffix = Path(filename or "").suffix.lower()
        if suffix not in ALLOWED_VIDEO_SUFFIXES:
            allowed = ", ".join(sorted(ALLOWED_VIDEO_SUFFIXES))
            raise MediaStoreError(
                f"Unsupported video format '{suffix or 'unknown'}'. Supported formats: {allowed}."
            )

        if len(content) > self.max_bytes:
            raise MediaStoreError(
                f"The rendered video is {len(content) / (1024 * 1024):.1f} MB, which exceeds the "
                f"{self.settings.MAX_UPLOAD_MB} MB upload limit."
            )

        self.purge_older_than(hours=24)

        media_id = f"{uuid.uuid4().hex}{suffix}"
        path = self.root / media_id
        path.write_bytes(content)
        logger.info("Staged render %s (%d bytes) for publishing", media_id, len(content))

        return {
            "id": media_id,
            "path": path,
            "bytes": len(content),
            "filename": f"splic-reel{suffix}",
        }

    def public_url(self, media_id: str) -> Optional[str]:
        """Return the public URL for a staged render, or None when not reachable."""
        base = self.settings.media_public_base_url
        if not base:
            return None
        return f"{base}/media/{media_id}"

    def purge_older_than(self, hours: int = 24) -> None:
        """Delete staged renders left behind by earlier publish attempts."""
        cutoff = time.time() - max(1, int(hours)) * 3600
        try:
            for entry in self.root.iterdir():
                if entry.is_file() and entry.stat().st_mtime < cutoff:
                    entry.unlink(missing_ok=True)
        except OSError as exc:  # pragma: no cover - best effort cleanup
            logger.warning("Could not purge staged media: %s", exc)

    def discard(self, path: Optional[Path]) -> None:
        """Remove a staged render; failures are logged but never block publishing."""
        if not path:
            return
        try:
            Path(path).unlink(missing_ok=True)
        except OSError as exc:  # pragma: no cover - best effort cleanup
            logger.warning("Could not remove staged media %s: %s", path, exc)
