import os
from datetime import datetime, timedelta
from typing import Any

import httpx
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from models.entity import Entity, EntityStatus, EntityType
from models.user_account import UserAccount
from models.wallet import Wallet
from services.ledger_chain import append_ledger_record
from services.protocol_config import get_rewards_config
from services.rights import get_or_create_wallet, issue_right

JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))
STARTER_AI_CREDITS = float(os.getenv("STARTER_AI_CREDITS", "100"))  # legacy env; see config/pocp_rewards.yaml
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


def _entity_metadata(provider: str, provider_user_id: str, username: str) -> dict:
    external_ids: dict[str, str] = {}
    if provider == "github":
        external_ids["github"] = username
    portable_id = f"github:{username}" if provider == "github" else f"{provider}:{provider_user_id}"
    return {
        "provider": provider,
        "provider_user_id": provider_user_id,
        "external_ids": external_ids,
        "portable_id": portable_id,
    }


def ensure_human_entity_for_user(db: Session, user: UserAccount) -> tuple[Entity, Wallet]:
    if user.entity_id:
        entity = db.query(Entity).filter(Entity.id == user.entity_id).first()
        if entity:
            entity.metadata_ = {
                **(entity.metadata_ or {}),
                **_entity_metadata(user.provider, user.provider_user_id, user.username),
            }
            wallet = get_or_create_wallet(db, entity.id)
            return entity, wallet

    entity = Entity(
        entity_type=EntityType.human,
        name=user.username,
        description=f"Human contributor created from {user.provider} login.",
        owner_id=None,
        creator_id=None,
        status=EntityStatus.active,
        metadata_=_entity_metadata(user.provider, user.provider_user_id, user.username),
    )
    db.add(entity)
    db.flush()
    user.entity_id = entity.id

    wallet = get_or_create_wallet(db, entity.id)
    starter_credits = float(get_rewards_config()["registration"]["ai_credits"])
    if wallet.ai_credits <= 0 and wallet.cp_balance <= 0:
        grant = issue_right(
            db,
            entity_id=entity.id,
            kind="bc",
            amount=starter_credits,
            reason="Registration grant",
        )
        append_ledger_record(
            db,
            contribution_id=None,
            event_type="registration_grant",
            payload={
                "entity_id": entity.id,
                "user_account_id": user.id,
                "ai_credits": starter_credits,
                "rights": [
                    {
                        "kind": grant.kind,
                        "version": grant.version,
                        "amount": grant.amount,
                        "spendable": grant.spendable,
                        "transferable": grant.transferable,
                    }
                ],
                "reason": "starter_ai_credits",
            },
        )
    db.flush()
    return entity, wallet


def get_or_create_user_account(
    db: Session,
    *,
    provider: str,
    provider_user_id: str,
    username: str,
    email: str | None = None,
    avatar_url: str | None = None,
) -> tuple[UserAccount, Entity, Wallet]:
    user = (
        db.query(UserAccount)
        .filter(
            UserAccount.provider == provider,
            UserAccount.provider_user_id == provider_user_id,
        )
        .first()
    )
    if user is None:
        user = UserAccount(
            provider=provider,
            provider_user_id=provider_user_id,
            username=username,
            email=email,
            avatar_url=avatar_url,
        )
        db.add(user)
        db.flush()
    else:
        user.username = username or user.username
        user.email = email or user.email
        user.avatar_url = avatar_url or user.avatar_url

    entity, wallet = ensure_human_entity_for_user(db, user)
    return user, entity, wallet


def bind_user_account_to_entity(
    db: Session,
    *,
    entity: Entity,
    provider: str,
    provider_user_id: str,
    username: str,
    email: str | None = None,
    avatar_url: str | None = None,
) -> tuple[UserAccount, Entity, Wallet]:
    user = (
        db.query(UserAccount)
        .filter(
            UserAccount.provider == provider,
            UserAccount.provider_user_id == provider_user_id,
        )
        .first()
    )
    if user is None:
        user = UserAccount(
            provider=provider,
            provider_user_id=provider_user_id,
            username=username,
            email=email,
            avatar_url=avatar_url,
            entity_id=entity.id,
        )
        db.add(user)
        db.flush()
    else:
        user.username = username or user.username
        user.email = email or user.email
        user.avatar_url = avatar_url or user.avatar_url
        user.entity_id = entity.id

    entity.metadata_ = {
        **(entity.metadata_ or {}),
        **_entity_metadata(provider, provider_user_id, username),
    }
    wallet = get_or_create_wallet(db, entity.id)
    db.flush()
    return user, entity, wallet


async def fetch_github_user(code: str) -> dict[str, Any]:
    client_id = os.getenv("GITHUB_CLIENT_ID")
    client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("GitHub OAuth is not configured")

    async with httpx.AsyncClient(timeout=20) as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
            },
        )
        token_resp.raise_for_status()
        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise RuntimeError("GitHub did not return access_token")

        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_resp.raise_for_status()
        gh_user = user_resp.json()

        email = gh_user.get("email")
        if not email:
            emails_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if emails_resp.status_code == 200:
                for item in emails_resp.json():
                    if item.get("primary") and item.get("verified"):
                        email = item.get("email")
                        break

    return {
        "id": str(gh_user["id"]),
        "username": gh_user.get("login") or f"github-{gh_user['id']}",
        "email": email,
        "avatar_url": gh_user.get("avatar_url"),
    }
