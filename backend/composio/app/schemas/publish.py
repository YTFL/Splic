"""Pydantic schemas for social publishing responses."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PublishResponse(BaseModel):
    """Result of publishing a rendered reel to a social platform."""

    success: bool = Field(..., description="Whether the platform accepted the post")
    platform: str = Field(..., description="Target platform ('instagram' or 'youtube')")
    post_id: Optional[str] = Field(None, description="Platform-side identifier of the published post")
    post_url: Optional[str] = Field(None, description="Public URL of the published post when known")
    account_handle: Optional[str] = Field(None, description="Handle of the account that published")
    message: str = Field(..., description="Human-readable result message")
    detail: Dict[str, Any] = Field(default_factory=dict, description="Non-secret publishing metadata")
