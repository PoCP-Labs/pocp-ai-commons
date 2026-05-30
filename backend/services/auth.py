"""
PoCP AI Commons — Authentication Service
==========================================
Core authentication logic: password hashing, JWT creation/verification,
account registration, and token refresh/revocation.

Security design:
- Passwords hashed with bcrypt via passlib.
- Access tokens are short-lived (30 min default).
- Refresh tokens are long-lived (7 days), stored hashed in DB for revocation.
- Token rotation: issuing a new refresh token revokes the old one.
"""

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session

from models.account import Account, RefreshToken
from models.entity import Entity, EntityStatus, EntityType
from models.wallet import Wallet

# ---------------------------------------------------------------------------
# Configuration (override via environment variables)
# ---------------------------------------------------------------------------

SECRET_KEY = os.getenv("POCP_SECRET_KEY", "pocp-dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("POCP_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("POCP_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# ---------------------------------------------------------------------------
# Password hashing (Using bcrypt directly to avoid passlib deprecations & bugs)
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    password_bytes = plain_password.encode("utf-8")
    try:
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT Token creation and verification
# ---------------------------------------------------------------------------


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a short-lived access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, datetime]:
    """Create a long-lived refresh token. Returns (token_string, expires_at)."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh", "jti": str(uuid.uuid4())})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises JWTError on failure."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def _hash_token(token: str) -> str:
    """SHA-256 hash of a token for DB storage (not the full token)."""
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Account operations
# ---------------------------------------------------------------------------


def register_account(
    db: Session,
    email: str,
    password: str,
    name: str,
    description: Optional[str] = None,
) -> tuple[Account, Entity]:
    """
    Register a new account:
    1. Create a human Entity.
    2. Create an Account linked to that Entity.
    3. Grant registration AI Credits (same as existing grant logic).
    Returns (account, entity).
    """
    # Check email uniqueness
    existing = db.query(Account).filter(Account.email == email).first()
    if existing:
        raise ValueError("An account with this email already exists")

    # Create human entity
    entity = Entity(
        entity_type=EntityType.human,
        name=name,
        description=description,
        status=EntityStatus.active,
    )
    db.add(entity)
    db.flush()

    # Create wallet with starter credits
    wallet = Wallet(entity_id=entity.id, cp_balance=0.0, ai_credits=100.0)
    db.add(wallet)

    # Create account
    account = Account(
        entity_id=entity.id,
        email=email,
        hashed_password=hash_password(password),
    )
    db.add(account)
    db.flush()

    return account, entity


def authenticate_account(
    db: Session,
    email: str,
    password: str,
) -> Optional[Account]:
    """Authenticate by email and password. Returns Account or None."""
    account = db.query(Account).filter(Account.email == email).first()
    if not account:
        return None
    if not verify_password(password, account.hashed_password):
        return None
    if not account.is_active:
        return None
    return account


def issue_tokens(
    db: Session,
    account: Account,
) -> dict:
    """
    Issue access + refresh token pair for an authenticated account.
    Stores the refresh token hash in DB for revocation support.
    """
    token_data = {"sub": account.id, "entity_id": account.entity_id}

    access_token = create_access_token(token_data)
    refresh_token, expires_at = create_refresh_token(token_data)

    # Store refresh token hash
    rt = RefreshToken(
        account_id=account.id,
        token_hash=_hash_token(refresh_token),
        expires_at=expires_at,
    )
    db.add(rt)
    db.flush()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def refresh_access_token(
    db: Session,
    refresh_token: str,
) -> dict:
    """
    Validate a refresh token and issue a new token pair (token rotation).
    Revokes the old refresh token.
    """
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise ValueError("Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise ValueError("Token is not a refresh token")

    token_hash = _hash_token(refresh_token)
    stored = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash, RefreshToken.revoked == False)
        .first()
    )
    if not stored:
        raise ValueError("Refresh token not found or already revoked")

    if stored.expires_at < datetime.utcnow():
        stored.revoked = True
        db.flush()
        raise ValueError("Refresh token expired")

    # Revoke old token
    stored.revoked = True
    db.flush()

    # Issue new pair
    account = db.query(Account).filter(Account.id == stored.account_id).first()
    if not account or not account.is_active:
        raise ValueError("Account not found or inactive")

    return issue_tokens(db, account)


def revoke_all_tokens(db: Session, account_id: str) -> int:
    """Revoke all refresh tokens for an account (logout everywhere)."""
    count = (
        db.query(RefreshToken)
        .filter(RefreshToken.account_id == account_id, RefreshToken.revoked == False)
        .update({"revoked": True})
    )
    db.flush()
    return count


def get_account_by_id(db: Session, account_id: str) -> Optional[Account]:
    """Retrieve account by ID."""
    return db.query(Account).filter(Account.id == account_id).first()
