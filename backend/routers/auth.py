import os
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db
from models.user_account import UserAccount
from services.auth import (
    BACKEND_URL,
    FRONTEND_URL,
    create_access_token,
    decode_access_token,
    fetch_github_user,
    get_or_create_user_account,
)

router = APIRouter(prefix="/api/v1", tags=["auth"])


class DevLoginIn(BaseModel):
    username: str
    email: EmailStr | None = None


def _serialize(user: UserAccount, entity, wallet) -> dict:
    return {
        "user": {
            "id": user.id,
            "provider": user.provider,
            "provider_user_id": user.provider_user_id,
            "username": user.username,
            "email": user.email,
            "avatar_url": user.avatar_url,
        },
        "entity": {
            "id": entity.id,
            "entity_type": entity.entity_type.value,
            "name": entity.name,
            "description": entity.description,
            "status": entity.status.value,
        },
        "wallet": {
            "id": wallet.id,
            "entity_id": wallet.entity_id,
            "cp_balance": wallet.cp_balance,
            "ai_credits": wallet.ai_credits,
        },
    }


def current_user_from_header(authorization: str | None, db: Session) -> UserAccount:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    user_id = payload.get("sub")
    user = db.query(UserAccount).filter(UserAccount.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> UserAccount:
    return current_user_from_header(authorization, db)


def require_entity_scope(entity_id: str, user: UserAccount) -> None:
    """PA-6 auth scope: bearer session entity must match the requested entity_id."""
    if user.entity_id != entity_id:
        raise HTTPException(
            status_code=403,
            detail="Auth scope: entity_id does not match authenticated session",
        )


@router.get("/auth/github/login")
def github_login():
    client_id = os.getenv("GITHUB_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=500, detail="GITHUB_CLIENT_ID is not configured")
    callback = os.getenv("GITHUB_OAUTH_CALLBACK_URL", f"{BACKEND_URL}/api/v1/auth/github/callback")
    params = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": callback,
            "scope": "read:user user:email",
        }
    )
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{params}")


@router.get("/auth/github/callback")
async def github_callback(code: str = Query(...), db: Session = Depends(get_db)):
    gh = await fetch_github_user(code)
    user, entity, wallet = get_or_create_user_account(
        db,
        provider="github",
        provider_user_id=gh["id"],
        username=gh["username"],
        email=gh.get("email"),
        avatar_url=gh.get("avatar_url"),
    )
    db.commit()
    token = create_access_token(user.id, {"entity_id": entity.id, "username": user.username})
    return RedirectResponse(f"{FRONTEND_URL}?token={token}")


@router.post("/auth/dev-login")
def dev_login(body: DevLoginIn, db: Session = Depends(get_db)):
    if os.getenv("ENABLE_DEV_LOGIN", "true").lower() != "true":
        raise HTTPException(status_code=403, detail="Dev login is disabled")
    user, entity, wallet = get_or_create_user_account(
        db,
        provider="dev",
        provider_user_id=body.email or body.username,
        username=body.username,
        email=body.email,
    )
    db.commit()
    token = create_access_token(user.id, {"entity_id": entity.id, "username": user.username})
    return {"access_token": token, "token_type": "bearer", **_serialize(user, entity, wallet)}


@router.get("/me")
def me(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = current_user_from_header(authorization, db)
    from models.entity import Entity
    from models.wallet import Wallet

    entity = db.query(Entity).filter(Entity.id == user.entity_id).first()
    wallet = db.query(Wallet).filter(Wallet.entity_id == user.entity_id).first()
    if not entity or not wallet:
        raise HTTPException(status_code=404, detail="Entity or wallet not found")
    return _serialize(user, entity, wallet)


@router.post("/auth/logout")
def logout():
    return {"ok": True}
