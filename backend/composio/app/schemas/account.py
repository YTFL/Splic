"""Pydantic schemas for connected social media accounts."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConnectedAccountSummary(BaseModel):
    """Safe, sanitized representation of a connected social account.
    
    Security note: Access tokens, refresh tokens, and internal OAuth credentials
    are strictly excluded from this model.
    """
    id: str = Field(..., description="Unique connection ID (e.g. ca_...)")
    toolkit: str = Field(..., description="Toolkit/App identifier (e.g. 'instagram', 'youtube')")
    status: str = Field(..., description="Connection status (e.g. 'ACTIVE', 'EXPIRED', 'PENDING')")
    user_id: str = Field(..., description="Owner user identifier")
    account_name: Optional[str] = Field(None, description="Display name of the connected profile/channel")
    account_handle: Optional[str] = Field(None, description="Username or channel identifier (e.g. @creator)")
    created_at: Optional[str] = Field(None, description="ISO timestamp of connection creation")
    updated_at: Optional[str] = Field(None, description="ISO timestamp of last connection update")
    is_active: bool = Field(True, description="True if connection is active and valid")


class AccountListResponse(BaseModel):
    """Response containing multiple connected accounts for a user."""
    accounts: List[ConnectedAccountSummary] = Field(default_factory=list, description="List of accounts")
    total: int = Field(..., description="Total count of accounts matching query")
    user_id: str = Field(..., description="Owner user identifier")
    toolkit_filter: Optional[str] = Field(None, description="Filter applied if any")


class AccountDetailResponse(BaseModel):
    """Detailed metadata for a specific connected account."""
    id: str = Field(..., description="Unique connection ID")
    toolkit: str = Field(..., description="Toolkit name")
    status: str = Field(..., description="Connection status")
    user_id: str = Field(..., description="Owner user identifier")
    account_name: Optional[str] = Field(None, description="Display name")
    account_handle: Optional[str] = Field(None, description="Username or handle")
    is_active: bool = Field(True, description="Whether the connection is currently usable")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Safe, non-secret public metadata")


class AccountDisconnectResponse(BaseModel):
    """Response confirming account disconnection."""
    success: bool = Field(..., description="Whether disconnection succeeded")
    account_id: str = Field(..., description="ID of the disconnected account")
    message: str = Field(..., description="Human-readable status message")

