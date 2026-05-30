"""
PoCP AI Commons — Authentication Schemas
==========================================
Pydantic models for auth request/response payloads.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """Registration payload."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128, description="Minimum 8 characters")
    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    description: Optional[str] = None


class RefreshRequest(BaseModel):
    """Token refresh payload."""

    refresh_token: str


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class AccountOut(BaseModel):
    """Account info (excludes sensitive fields like hashed_password)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_id: str
    email: str
    is_active: bool
    is_superuser: bool
    created_at: datetime


class LoginResponse(BaseModel):
    """Token response returned on login and refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")


class RegisterResponse(BaseModel):
    """Response returned on successful registration."""

    account: AccountOut
    entity_id: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class ProfileOut(BaseModel):
    """Current user profile with wallet info."""

    account_id: str
    entity_id: str
    email: str
    name: str
    description: Optional[str] = None
    is_superuser: bool
    cp_balance: float = 0.0
    ai_credits: float = 0.0
    created_at: datetime
