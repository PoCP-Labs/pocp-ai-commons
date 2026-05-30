"""Authentication & Authorization for PoCP AI Commons.

Supports two modes:
- "demo" — no auth, reviewer_id in request body (current behavior)
- "jwt" — JWT bearer token required for write operations

Tokens are issued per Entity. Entities authenticate by providing their entity_id.
In production, this should be backed by GitHub OAuth or similar.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import AUTH_MODE, JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET
from models.entity import Entity, EntityType

security = HTTPBearer(auto_error=False)


def create_access_token(entity_id: str, entity_type: str) -> str:
    """Create a JWT token for an entity."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": entity_id,
        "entity_type": entity_type,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_entity(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Extract current entity from JWT token.

    In demo mode, falls back to entity_id from query params or request body.
    """
    if AUTH_MODE == "demo":
        # Demo mode: no auth required, entity identified by query param
        entity_id = request.query_params.get("entity_id")
        if entity_id:
            return {"sub": entity_id, "entity_type": "unknown", "demo": True}
        return {"demo": True}

    # JWT mode: require valid token
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    return decode_access_token(credentials.credentials)


def require_human(entity: dict = Depends(get_current_entity)) -> dict:
    """Ensure the current entity is a human."""
    if entity.get("demo"):
        return entity

    if entity.get("entity_type") != "human":
        raise HTTPException(
            status_code=403,
            detail="Only human entities can perform this action",
        )
    return entity


def require_entity_id(expected_id: str, entity: dict = Depends(get_current_entity)) -> dict:
    """Ensure the current entity matches the expected ID (prevent impersonation)."""
    if entity.get("demo"):
        return entity

    if entity.get("sub") != expected_id:
        raise HTTPException(
            status_code=403,
            detail="You can only act on behalf of your own entity",
        )
    return entity


def can_review_contribution(
    contribution_id: str,
    db,
    entity: dict = Depends(require_human),
) -> dict:
    """Check if the current entity has permission to review a contribution.

    In the current protocol:
    - Any human can review (community review model)
    - Self-review is blocked at service level
    - In the future, this can be extended to role-based review permissions
    """
    # Permission check passes — self-review is blocked in service layer
    return entity
