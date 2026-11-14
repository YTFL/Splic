"""Publishing service that pushes a rendered reel to Instagram or YouTube.

These are the only mutating Composio actions the Splic backend performs, and
they are reachable exclusively through the dedicated ``/api/v1/publish/*``
routes, which require a verified Firebase user, an existing Composio connection
and an explicit user action. The generic ``/composio/execute`` endpoint keeps
rejecting every publishing slug, so nothing can be posted incidentally.

Tool schemas (verified against the live Composio API):

* ``INSTAGRAM_GET_USER_INFO``          -> ``{fields}``
* ``INSTAGRAM_CREATE_MEDIA_CONTAINER`` -> ``{ig_user_id, video_url, media_type, caption, ...}``
* ``INSTAGRAM_CREATE_POST``            -> ``{ig_user_id, creation_id}``
* ``YOUTUBE_UPLOAD_VIDEO``             -> ``{title, description, tags, categoryId, privacyStatus, videoFilePath}``
"""

import logging
from typing import Any, Dict, Iterable, List, Optional

from app.integrations.composio.client import ComposioClientManager, get_composio_client_manager

logger = logging.getLogger("composio.publish")

INSTAGRAM_MEDIA_MAX_CAPTION = 2200


class PublishError(RuntimeError):
    """Raised when a publishing action cannot be completed."""


def _as_mapping(payload: Any) -> Dict[str, Any]:
    """Normalise Composio execution responses into plain dictionaries."""
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    if hasattr(payload, "model_dump"):
        try:
            return payload.model_dump()
        except Exception:  # pragma: no cover - defensive
            return {}
    if hasattr(payload, "__dict__"):
        return dict(payload.__dict__)
    return {}


def _deep_find(payload: Any, keys: Iterable[str]) -> Optional[Any]:
    """Search a nested response for the first non-empty value under ``keys``."""
    wanted = tuple(keys)
    stack: List[Any] = [payload]
    seen = 0
    while stack and seen < 500:
        current = stack.pop(0)
        seen += 1
        if isinstance(current, dict):
            for key in wanted:
                value = current.get(key)
                if isinstance(value, (str, int)) and str(value).strip():
                    return value
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return None


class PublishService:
    """Executes the Instagram and YouTube publishing actions for a user."""

    def __init__(self, client_manager: Optional[ComposioClientManager] = None):
        self.client_manager = client_manager or get_composio_client_manager()

    # ------------------------------------------------------------------ helpers
    def _execute(
        self,
        slug: str,
        arguments: Dict[str, Any],
        user_id: str,
        account_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        client = self.client_manager.get_client()

        try:
            if hasattr(client, "tools") and hasattr(client.tools, "execute"):
                exec_kwargs: Dict[str, Any] = {
                    "slug": slug,
                    "arguments": arguments,
                    "user_id": user_id,
                }
                if account_id:
                    exec_kwargs["connected_account_id"] = account_id
                return _as_mapping(client.tools.execute(**exec_kwargs))

            if hasattr(client, "execute_action"):
                return _as_mapping(
                    client.execute_action(action=slug, params=arguments, entity_id=user_id)
                )

            if hasattr(client, "execute"):
                return _as_mapping(
                    client.execute(slug=slug, parameters=arguments, user_id=user_id)
                )
        except Exception as exc:
            message = str(exc)
            logger.error("Composio action %s failed: %s", slug, message)
            raise PublishError(f"{slug} failed: {message}") from exc

        raise PublishError("The Composio client does not expose a supported execution method.")

    @staticmethod
    def _failed_response(payload: Dict[str, Any]) -> Optional[str]:
        """Return an error string when Composio reports a failed execution."""
        for key in ("error", "err", "errorMessage"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
        successful = payload.get("successful", payload.get("success"))
        if successful is False:
            return str(payload.get("message") or "Composio reported an unsuccessful execution.")
        data = payload.get("data")
        if isinstance(data, dict):
            return PublishService._failed_response(data)
        return None

    # ---------------------------------------------------------------- Instagram
    def publish_instagram(
        self,
        user_id: str,
        media_url: str,
        caption: str = "",
        share_to_feed: bool = True,
        account_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a Reels media container from ``media_url`` and publish it."""
        profile = self._execute(
            "INSTAGRAM_GET_USER_INFO",
            {"fields": "id,username,account_type"},
            user_id,
            account_id,
        )
        failure = self._failed_response(profile)
        if failure:
            raise PublishError(f"Could not read the Instagram account: {failure}")

        ig_user_id = _deep_find(profile, ("id", "ig_user_id", "user_id"))
        username = _deep_find(profile, ("username",))
        if not ig_user_id:
            raise PublishError(
                "Composio did not return an Instagram Business account id. Reconnect the "
                "Instagram account and confirm it is a Business or Creator profile."
            )

        container = self._execute(
            "INSTAGRAM_CREATE_MEDIA_CONTAINER",
            {
                "ig_user_id": str(ig_user_id),
                "video_url": media_url,
                "media_type": "REELS",
                "content_type": "reel",
                "caption": (caption or "")[:INSTAGRAM_MEDIA_MAX_CAPTION],
                "share_to_feed": bool(share_to_feed),
            },
            user_id,
            account_id,
        )
        failure = self._failed_response(container)
        if failure:
            raise PublishError(f"Instagram rejected the media container: {failure}")

        creation_id = _deep_find(container, ("creation_id", "creationId", "container_id", "id"))
        if not creation_id:
            raise PublishError("Instagram did not return a media container id.")

        published = self._execute(
            "INSTAGRAM_CREATE_POST",
            {"ig_user_id": str(ig_user_id), "creation_id": str(creation_id)},
            user_id,
            account_id,
        )
        failure = self._failed_response(published)
        if failure:
            raise PublishError(f"Instagram could not publish the Reel: {failure}")

        post_id = _deep_find(published, ("id", "media_id", "post_id"))
        permalink = _deep_find(published, ("permalink", "url"))

        return {
            "post_id": str(post_id) if post_id else None,
            "post_url": str(permalink) if permalink else None,
            "account_handle": f"@{username}" if username else None,
            "detail": {
                "ig_user_id": str(ig_user_id),
                "creation_id": str(creation_id),
            },
        }

    # ------------------------------------------------------------------ YouTube
    def publish_youtube(
        self,
        user_id: str,
        video_path: str,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        privacy: str = "public",
        category_id: str = "22",
        account_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload a staged video file to the connected YouTube channel."""
        privacy_status = (privacy or "public").strip().lower()
        if privacy_status not in {"public", "unlisted", "private"}:
            privacy_status = "public"

        result = self._execute(
            "YOUTUBE_UPLOAD_VIDEO",
            {
                "title": (title or "Splic Studio Reel")[:100],
                "description": description or "",
                "tags": [str(tag) for tag in (tags or []) if str(tag).strip()],
                "categoryId": str(category_id),
                "privacyStatus": privacy_status,
                "videoFilePath": video_path,
            },
            user_id,
            account_id,
        )
        failure = self._failed_response(result)
        if failure:
            raise PublishError(f"YouTube rejected the upload: {failure}")

        video_id = _deep_find(result, ("video_id", "videoId", "id"))
        if not video_id:
            raise PublishError("YouTube did not return a video id for the upload.")

        return {
            "post_id": str(video_id),
            "post_url": f"https://youtu.be/{video_id}",
            "account_handle": None,
            "detail": {"privacy_status": privacy_status},
        }
