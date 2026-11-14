"""Publishing routes: push a rendered reel to Instagram or YouTube.

These endpoints are the only place where mutating Composio actions are executed.
Each request requires a verified Firebase ID token, an existing connection for
the target platform, and an explicit user action from the Export workspace.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.dependencies import AuthenticatedUser, get_current_user, get_publish_service
from app.schemas.publish import PublishResponse
from app.services.media_store import MediaStore, MediaStoreError
from app.services.publish_service import PublishError, PublishService

logger = logging.getLogger("composio.routes.publish")

router = APIRouter(prefix="/publish", tags=["Social Publishing"])

INSTAGRAM_PUBLIC_URL_HELP = (
    "Instagram only accepts a publicly reachable video URL, so the rendered reel must be "
    "served from a public origin. Set PUBLIC_MEDIA_BASE_URL in the repository root .env.local "
    "to a tunnel or deployed backend origin (for example an ngrok or Cloudflare tunnel URL) "
    "and try again. YouTube publishing does not need this."
)


async def _read_upload(file: UploadFile) -> bytes:
    try:
        return await file.read()
    finally:
        await file.close()


@router.post(
    "/instagram",
    response_model=PublishResponse,
    summary="Publish a Rendered Reel to Instagram",
)
async def publish_instagram(
    file: UploadFile = File(..., description="Rendered MP4 reel"),
    caption: str = Form("", description="Post caption and hashtags"),
    share_to_feed: bool = Form(True, description="Also share the Reel to the main feed"),
    account_id: Optional[str] = Form(None, description="Optional explicit connected account id"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    publish_service: PublishService = Depends(get_publish_service),
) -> PublishResponse:
    """Stage the reel, expose it at a public URL, then create and publish a Reels container."""
    store = MediaStore()
    try:
        staged = store.save(file.filename, await _read_upload(file))
    except MediaStoreError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    suffix = staged["id"].rsplit(".", 1)[-1].lower()
    if suffix not in {"mp4", "mov"}:
        store.discard(staged["path"])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Instagram accepts MP4 or MOV Reels, but this render is '{suffix}'. "
                "Re-export as MP4 before publishing (the WebM fallback used when the "
                "MP4 transcode fails cannot be published to Instagram)."
            ),
        )

    media_url = store.public_url(staged["id"])
    if not media_url:
        store.discard(staged["path"])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INSTAGRAM_PUBLIC_URL_HELP,
        )

    try:
        result = publish_service.publish_instagram(
            user_id=current_user.id,
            media_url=media_url,
            caption=caption,
            share_to_feed=share_to_feed,
            account_id=account_id,
        )
    except PublishError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    # The staged file is deliberately retained: Instagram fetches the container
    # media asynchronously, so deleting it here would break the publish.

    handle = result.get("account_handle") or "your Instagram account"
    return PublishResponse(
        success=True,
        platform="instagram",
        post_id=result.get("post_id"),
        post_url=result.get("post_url"),
        account_handle=result.get("account_handle"),
        message=f"Reel published to {handle}.",
        detail={**result.get("detail", {}), "media_url": media_url},
    )


@router.post(
    "/youtube",
    response_model=PublishResponse,
    summary="Upload a Rendered Reel to YouTube",
)
async def publish_youtube(
    file: UploadFile = File(..., description="Rendered MP4 reel"),
    title: str = Form(..., description="Video title"),
    description: str = Form("", description="Video description"),
    tags: str = Form("", description="Comma-separated keyword tags"),
    privacy_status: str = Form("public", description="public | unlisted | private"),
    category_id: str = Form("22", description="YouTube category id (22 = People & Blogs)"),
    account_id: Optional[str] = Form(None, description="Optional explicit connected account id"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    publish_service: PublishService = Depends(get_publish_service),
) -> PublishResponse:
    """Stage the reel and upload it directly to the connected YouTube channel."""
    store = MediaStore()
    try:
        staged = store.save(file.filename, await _read_upload(file))
    except MediaStoreError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    tag_list = [tag.strip() for tag in (tags or "").split(",") if tag.strip()]

    try:
        result = publish_service.publish_youtube(
            user_id=current_user.id,
            video_path=str(staged["path"]),
            title=title,
            description=description,
            tags=tag_list,
            privacy=privacy_status,
            category_id=category_id,
            account_id=account_id,
        )
    except PublishError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    finally:
        # The upload reads the file synchronously, so it can be removed afterwards.
        store.discard(staged["path"])

    return PublishResponse(
        success=True,
        platform="youtube",
        post_id=result.get("post_id"),
        post_url=result.get("post_url"),
        account_handle=result.get("account_handle"),
        message="Video uploaded to your YouTube channel.",
        detail=result.get("detail", {}),
    )
