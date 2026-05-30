"""Auth token endpoint — generate JWT tokens for entities.

In demo mode, tokens are not required.
In production mode, entities must authenticate to get a token.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import AUTH_MODE
from database import get_db
from models.entity import Entity
from schemas import EntityOut
from services.auth import create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class TokenResponse:
    """Simple token response schema."""

    def __init__(self, access_token: str, token_type: str = "Bearer"):
        self.access_token = access_token
        self.token_type = token_type


@router.post("/token")
def get_token(entity_id: str, db: Session = Depends(get_db)):
    """Generate a JWT token for an entity.

    In demo mode: returns token without validation.
    In production mode: requires entity to exist and be active.
    """
    entity = db.query(Entity).filter(Entity.id == entity_id).first()

    if AUTH_MODE != "demo":
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        if entity.status != "active":
            raise HTTPException(status_code=403, detail="Entity is not active")

    token = create_access_token(
        entity_id=entity_id,
        entity_type=entity.entity_type.value if entity else "unknown",
    )

    return {
        "access_token": token,
        "token_type": "Bearer",
        "entity_id": entity_id,
        "mode": AUTH_MODE,
    }
