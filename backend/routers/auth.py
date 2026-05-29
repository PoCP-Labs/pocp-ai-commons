"""
PoCP AI Commons — Authentication Router
=========================================
Endpoints for user registration, login, token refresh, logout, and profile.

All auth endpoints are prefixed with /api/v1/auth.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_account, get_current_entity
from models.account import Account
from models.entity import Entity
from schemas.auth import (
    AccountOut,
    LoginResponse,
    ProfileOut,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
)
from services.auth import (
    authenticate_account,
    issue_tokens,
    refresh_access_token,
    register_account,
    revoke_all_tokens,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# POST /register — Create a new account
# ---------------------------------------------------------------------------


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user account.

    Creates a human Entity, an Account with hashed credentials,
    a Wallet with starter AI Credits, and returns access + refresh tokens.
    """
    try:
        account, entity = register_account(
            db,
            email=body.email,
            password=body.password,
            name=body.name,
            description=body.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    tokens = issue_tokens(db, account)
    db.commit()

    return RegisterResponse(
        account=AccountOut.model_validate(account),
        entity_id=entity.id,
        **tokens,
    )


# ---------------------------------------------------------------------------
# POST /login — Authenticate and get tokens (OAuth2 password flow)
# ---------------------------------------------------------------------------


@router.post("/login", response_model=LoginResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    OAuth2 password grant login.

    Accepts `username` (email) and `password` as form fields.
    Returns access_token, refresh_token, token_type, and expires_in.
    """
    account = authenticate_account(db, email=form_data.username, password=form_data.password)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tokens = issue_tokens(db, account)
    db.commit()

    return LoginResponse(**tokens)


# ---------------------------------------------------------------------------
# POST /refresh — Rotate refresh token
# ---------------------------------------------------------------------------


@router.post("/refresh", response_model=LoginResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    The old refresh token is revoked (token rotation).
    """
    try:
        tokens = refresh_access_token(db, body.refresh_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    db.commit()
    return LoginResponse(**tokens)


# ---------------------------------------------------------------------------
# POST /logout — Revoke all refresh tokens
# ---------------------------------------------------------------------------


@router.post("/logout", status_code=204)
def logout(
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """
    Revoke all refresh tokens for the current account.
    The access token remains valid until expiry (stateless).
    """
    revoke_all_tokens(db, account.id)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# GET /me — Get current user profile
# ---------------------------------------------------------------------------


@router.get("/me", response_model=ProfileOut)
def get_profile(
    account: Account = Depends(get_current_account),
    entity: Entity = Depends(get_current_entity),
    db: Session = Depends(get_db),
):
    """
    Return the authenticated user's profile including account info,
    entity details, and wallet balances.
    """
    from models.wallet import Wallet

    wallet = db.query(Wallet).filter(Wallet.entity_id == entity.id).first()

    return ProfileOut(
        account_id=account.id,
        entity_id=entity.id,
        email=account.email,
        name=entity.name,
        description=entity.description,
        is_superuser=account.is_superuser,
        cp_balance=wallet.cp_balance if wallet else 0.0,
        ai_credits=wallet.ai_credits if wallet else 0.0,
        created_at=account.created_at,
    )
