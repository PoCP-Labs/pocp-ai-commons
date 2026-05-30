"""
PoCP AI Commons — Dependency Injection
========================================
FastAPI dependencies for authentication and authorization.

Usage in route handlers:
    from deps import get_current_account, get_current_entity, require_superuser

    @router.get("/me")
    def me(account: Account = Depends(get_current_account)):
        ...

    @router.post("/admin/...")
    def admin_action(account: Account = Depends(require_superuser)):
        ...
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from database import get_db
from models.account import Account
from models.entity import Entity
from services.auth import decode_token

# OAuth2 scheme — tokenUrl points to the login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_account(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Account:
    """
    Decode the access token and return the authenticated Account.
    Raises 401 if token is invalid, expired, or account not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
    except JWTError:
        raise credentials_exception

    if payload.get("type") != "access":
        raise credentials_exception

    account_id: str = payload.get("sub")
    if account_id is None:
        raise credentials_exception

    account = db.query(Account).filter(Account.id == account_id).first()
    if account is None or not account.is_active:
        raise credentials_exception

    return account


async def get_current_entity(
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> Entity:
    """
    Return the Entity associated with the current authenticated account.
    Useful when route logic operates on entities rather than accounts.
    """
    entity = db.query(Entity).filter(Entity.id == account.entity_id).first()
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated entity not found",
        )
    return entity


async def require_superuser(
    account: Account = Depends(get_current_account),
) -> Account:
    """
    Ensure the current account has superuser privileges.
    Raises 403 if not a superuser.
    """
    if not account.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required",
        )
    return account


# ---------------------------------------------------------------------------
# Optional dependency: allows both authenticated and anonymous access
# ---------------------------------------------------------------------------


async def get_optional_account(
    token: str | None = Depends(
        OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
    ),
    db: Session = Depends(get_db),
) -> Account | None:
    """
    Returns the authenticated Account if a valid token is provided,
    or None if no token / invalid token. Does NOT raise 401.
    Useful for endpoints that behave differently for logged-in users.
    """
    if token is None:
        return None
    try:
        payload = decode_token(token)
    except JWTError:
        return None

    if payload.get("type") != "access":
        return None

    account_id = payload.get("sub")
    if not account_id:
        return None

    account = db.query(Account).filter(Account.id == account_id).first()
    if account is None or not account.is_active:
        return None

    return account
