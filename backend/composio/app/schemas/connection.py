"""Pydantic schemas for OAuth connection initiation and status checks."""

from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class ConnectInstagramRequest(BaseModel):
    """Payload to initiate Instagram OAuth connection."""
    redirect_url: Optional[str] = Field(
        None,
        description="Frontend callback URL to return after OAuth completion."
    )
    force_reconnect: bool = Field(
        False,
        description="If True, initiates a new auth link even if an active account exists."
    )


class ConnectYouTubeRequest(BaseModel):
    """Payload to initiate YouTube OAuth connection."""
    redirect_url: Optional[str] = Field(
        None,
        description="Frontend callback URL to return after OAuth completion."
    )
    force_reconnect: bool = Field(
        False,
        description="If True, initiates a new auth link even if an active account exists."
    )
    scopes: Optional[List[str]] = Field(
        default=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
        ],
        description=(
            "Requested Google/YouTube OAuth permission scopes. The upload scope is required "
            "for publishing; drop it only for read-only connections."
        )
    )


class ConnectionInitiationResponse(BaseModel):
    """Safe response providing the OAuth authorization URL for the user."""
    connection_request_id: str = Field(..., description="Unique ID for this connection request")
    toolkit: str = Field(..., description="Target toolkit ('instagram' or 'youtube')")
    redirect_url: str = Field(..., description="Composio hosted authorization URL for user consent")
    status: str = Field("INITIATED", description="Status of connection request")
    user_id: str = Field(..., description="User ID for whom connection was initiated")
    expires_at: Optional[str] = Field(None, description="Expiration time of redirect link if applicable")
    instructions: str = Field(
        "Direct the creator to the redirect_url in a browser to complete authentication.",
        description="Instructional guide for the frontend client."
    )


class ConnectionStatusResponse(BaseModel):
    """Status verification response for a connection."""
    connection_id: Optional[str] = Field(None, description="ID of connected account once active")
    toolkit: str = Field(..., description="Toolkit ('instagram' or 'youtube')")
    status: str = Field(..., description="Status ('ACTIVE', 'PENDING', 'EXPIRED', 'NOT_CONNECTED')")
    user_id: str = Field(..., description="User ID")
    is_active: bool = Field(..., description="True if account is actively authenticated")
    message: Optional[str] = Field(None, description="Status detail message")

