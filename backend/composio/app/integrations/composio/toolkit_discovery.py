"""Toolkit and Action Discovery Service for Composio.

Discovers available toolkits (Instagram, YouTube), introspects supported actions,
and marks allowlist permissions for safe execution.
"""

import logging
from typing import Any, Dict, List, Optional, Set
from .client import ComposioClientManager, get_composio_client_manager
from app.schemas.action import ToolkitSummary, ActionSummary

logger = logging.getLogger("composio.discovery")

# Allowlisted actions permitted for controlled execution (strictly read-only/informational)
ALLOWLISTED_READ_ONLY_ACTIONS: Set[str] = {
    # Instagram Safe Actions
    "INSTAGRAM_GET_USER_INFO",
    "INSTAGRAM_GET_USER_INSIGHTS",
    "INSTAGRAM_GET_IG_USER_MEDIA",
    "INSTAGRAM_GET_IG_USER_STORIES",
    "INSTAGRAM_GET_IG_MEDIA",
    "INSTAGRAM_GET_IG_MEDIA_INSIGHTS",
    "INSTAGRAM_GET_IG_MEDIA_COMMENTS",
    "INSTAGRAM_GET_IG_COMMENT_REPLY",
    "INSTAGRAM_GET_CONVERSATION",
    "INSTAGRAM_GET_IG_USER_CONTENT_PUBLISHING_LIMIT",
    # YouTube Safe Actions
    "YOUTUBE_LIST_MY_CHANNELS",
    "YOUTUBE_LIST_CHANNELS",
    "YOUTUBE_LIST_VIDEOS",
    "YOUTUBE_GET_CHANNEL_ACTIVITIES",
    "YOUTUBE_LIST_PLAYLISTS",
    "YOUTUBE_LIST_COMMENTS",
    "YOUTUBE_LIST_SUBSCRIPTIONS",
}

# Explicitly forbidden publishing/mutating actions (out of scope for safety)
BLOCKED_MUTATING_ACTIONS: Set[str] = {
    # Instagram blocked
    "INSTAGRAM_CREATE_POST",
    "INSTAGRAM_CREATE_CAROUSEL_CONTAINER",
    "INSTAGRAM_DELETE_COMMENT",
    "INSTAGRAM_POST_IG_MEDIA",
    "INSTAGRAM_PUBLISH_CONTAINER",
    # YouTube blocked
    "YOUTUBE_UPLOAD_VIDEO",
    "YOUTUBE_MULTIPART_UPLOAD_VIDEO",
    "YOUTUBE_DELETE_VIDEO",
    "YOUTUBE_DELETE_LIVE_BROADCAST",
    "YOUTUBE_INSERT_COMMENT_REPLY",
    "YOUTUBE_DELETE_COMMENT",
    "YOUTUBE_CREATE_PLAYLIST",
    "YOUTUBE_DELETE_PLAYLIST",
    "YOUTUBE_DELETE_PLAYLIST_ITEM",
    "YOUTUBE_INSERT_CHANNEL_SECTION",
    "YOUTUBE_DELETE_CHANNEL_SECTION",
    "YOUTUBE_DELETE_CAPTION_TRACK",
}

# Curated metadata dictionary based on official Composio documentation
VERIFIED_TOOLKITS: Dict[str, Dict[str, Any]] = {
    "instagram": {
        "name": "Instagram",
        "description": "Composio integration for Instagram Business and Creator profiles (Meta Graph API).",
        "category": "social_media",
        "actions": [
            {
                "slug": "INSTAGRAM_GET_USER_INFO",
                "name": "Get User Info",
                "description": "Retrieve profile details, username, account type and follower count.",
                "is_read_only": True,
            },
            {
                "slug": "INSTAGRAM_GET_IG_MEDIA_INSIGHTS",
                "name": "Get Media Insights",
                "description": "Retrieve metrics for posts, reels, and stories (reach, impressions, likes).",
                "is_read_only": True,
            },
            {
                "slug": "INSTAGRAM_GET_IG_USER_MEDIA",
                "name": "Get User Media",
                "description": "List recent photos, videos, and reels associated with the user account.",
                "is_read_only": True,
            },
            {
                "slug": "INSTAGRAM_GET_IG_USER_CONTENT_PUBLISHING_LIMIT",
                "name": "Get Publishing Limit",
                "description": "Check current rate limits and quota status for content publishing.",
                "is_read_only": True,
            },
            {
                "slug": "INSTAGRAM_CREATE_POST",
                "name": "Create Post",
                "description": "Publish a photo or video to Instagram profile (MUTATING - BLOCKED).",
                "is_read_only": False,
            },
            {
                "slug": "INSTAGRAM_CREATE_CAROUSEL_CONTAINER",
                "name": "Create Carousel Container",
                "description": "Create a multi-item carousel draft container (MUTATING - BLOCKED).",
                "is_read_only": False,
            },
        ],
    },
    "youtube": {
        "name": "YouTube",
        "description": "Composio integration for YouTube Data API v3 channels, videos, and playlists.",
        "category": "video_platform",
        "actions": [
            {
                "slug": "YOUTUBE_LIST_MY_CHANNELS",
                "name": "List My Channels",
                "description": "Retrieve channels owned by the authenticated YouTube/Google account.",
                "is_read_only": True,
            },
            {
                "slug": "YOUTUBE_GET_CHANNEL_ACTIVITIES",
                "name": "Get Channel Activities",
                "description": "Fetch recent events, uploads, subscriptions, and playlist updates.",
                "is_read_only": True,
            },
            {
                "slug": "YOUTUBE_LIST_VIDEOS",
                "name": "List Videos",
                "description": "List video details and metadata for specified video IDs or channel.",
                "is_read_only": True,
            },
            {
                "slug": "YOUTUBE_UPLOAD_VIDEO",
                "name": "Upload Video",
                "description": "Upload a video file to the channel (MUTATING - BLOCKED).",
                "is_read_only": False,
            },
            {
                "slug": "YOUTUBE_DELETE_VIDEO",
                "name": "Delete Video",
                "description": "Permanently delete a video from channel (MUTATING - BLOCKED).",
                "is_read_only": False,
            },
        ],
    },
}


class ToolkitDiscoveryService:
    """Service for discovering Composio toolkits and actions."""

    def __init__(self, client_manager: Optional[ComposioClientManager] = None):
        self.client_manager = client_manager or get_composio_client_manager()

    def list_supported_toolkits(self) -> List[ToolkitSummary]:
        """List all supported social media toolkits."""
        toolkits = []
        for slug, meta in VERIFIED_TOOLKITS.items():
            toolkits.append(
                ToolkitSummary(
                    slug=slug,
                    name=meta["name"],
                    description=meta["description"],
                    category=meta["category"],
                    is_supported=True,
                    total_actions=len(meta["actions"]),
                )
            )
        return toolkits

    def get_toolkit(self, toolkit_slug: str) -> Optional[ToolkitSummary]:
        """Get summary for a specific toolkit."""
        slug = toolkit_slug.lower()
        if slug in VERIFIED_TOOLKITS:
            meta = VERIFIED_TOOLKITS[slug]
            return ToolkitSummary(
                slug=slug,
                name=meta["name"],
                description=meta["description"],
                category=meta["category"],
                is_supported=True,
                total_actions=len(meta["actions"]),
            )
        return None

    def list_actions(self, toolkit_slug: str, user_id: Optional[str] = None) -> List[ActionSummary]:
        """Discover and list actions available under the given toolkit.
        
        Attempts live discovery via SDK where available, falling back to verified
        catalog with allowlist enforcement.
        """
        slug = toolkit_slug.lower()
        if slug not in VERIFIED_TOOLKITS:
            raise KeyError(f"Unsupported toolkit '{toolkit_slug}'. Supported: {list(VERIFIED_TOOLKITS.keys())}")

        discovered_actions: List[ActionSummary] = []

        # Attempt dynamic discovery via live Composio SDK if available
        try:
            client = self.client_manager.get_client()
            if hasattr(client, "tools") and hasattr(client.tools, "get"):
                tools = client.tools.get(user_id=user_id or "default", toolkits=[slug])
                if tools:
                    for t in tools:
                        action_slug = getattr(t, "slug", getattr(t, "name", ""))
                        if action_slug:
                            is_read = action_slug in ALLOWLISTED_READ_ONLY_ACTIONS
                            is_allowed = action_slug in ALLOWLISTED_READ_ONLY_ACTIONS and action_slug not in BLOCKED_MUTATING_ACTIONS
                            discovered_actions.append(
                                ActionSummary(
                                    slug=action_slug,
                                    name=getattr(t, "name", action_slug),
                                    description=getattr(t, "description", None),
                                    toolkit=slug,
                                    is_read_only=is_read,
                                    is_allowed=is_allowed,
                                    parameters_schema=getattr(t, "parameters", None),
                                )
                            )
                    if discovered_actions:
                        return discovered_actions
        except Exception as exc:
            logger.debug(f"Dynamic tool discovery via SDK bypassed: {exc}")

        # Fallback to verified catalog
        meta = VERIFIED_TOOLKITS[slug]
        for a in meta["actions"]:
            action_slug = a["slug"]
            is_read = a.get("is_read_only", True)
            is_allowed = action_slug in ALLOWLISTED_READ_ONLY_ACTIONS and action_slug not in BLOCKED_MUTATING_ACTIONS

            discovered_actions.append(
                ActionSummary(
                    slug=action_slug,
                    name=a["name"],
                    description=a["description"],
                    toolkit=slug,
                    is_read_only=is_read,
                    is_allowed=is_allowed,
                    parameters_schema=None,
                )
            )

        return discovered_actions

    def is_action_allowed(self, action_slug: str) -> bool:
        """Check whether an action is allowlisted for safe execution."""
        slug = action_slug.upper()
        if slug in BLOCKED_MUTATING_ACTIONS:
            return False
        return slug in ALLOWLISTED_READ_ONLY_ACTIONS

