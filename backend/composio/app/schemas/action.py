"""Pydantic schemas for toolkit discovery and controlled action execution."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolkitSummary(BaseModel):
    """Metadata summary for an available Composio toolkit."""
    slug: str = Field(..., description="Unique slug for the toolkit (e.g. 'instagram', 'youtube')")
    name: str = Field(..., description="Display name of the toolkit")
    description: Optional[str] = Field(None, description="Overview of toolkit capabilities")
    category: Optional[str] = Field("social_media", description="Classification category")
    is_supported: bool = Field(True, description="Whether currently supported in this backend")
    total_actions: int = Field(0, description="Total number of tools available under this toolkit")


class ActionSummary(BaseModel):
    """Metadata for an individual action/tool."""
    slug: str = Field(..., description="Action identifier in SCREAMING_SNAKE_CASE")
    name: str = Field(..., description="Human-readable action name")
    description: Optional[str] = Field(None, description="Action description")
    toolkit: str = Field(..., description="Toolkit to which this action belongs")
    is_read_only: bool = Field(True, description="Whether this is a safe, non-mutating action")
    is_allowed: bool = Field(False, description="Whether execution is allowed under current policy")
    parameters_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="JSON schema describing the required arguments"
    )


class ExecuteActionRequest(BaseModel):
    """Request payload for executing an allowlisted action."""
    action_slug: str = Field(..., description="Slug of the action to execute")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters required by the action"
    )
    account_id: Optional[str] = Field(
        None,
        description="Optional connected account ID. If omitted, uses active connection for current user."
    )


class ExecuteActionResponse(BaseModel):
    """Response returned upon controlled action execution."""
    success: bool = Field(..., description="Whether action execution succeeded")
    action_slug: str = Field(..., description="Slug of the executed action")
    data: Optional[Any] = Field(None, description="Output payload returned by the tool")
    message: Optional[str] = Field(None, description="Status or error message")

