"""
PoCP AI Commons — Auth Seed Data
==================================
Creates demo accounts for existing seeded human entities (Alice and Bob).
Called after the main seed_demo() to add auth credentials.

Demo credentials:
    alice@pocp.dev / alice12345
    bob@pocp.dev   / bob12345
"""

from sqlalchemy.orm import Session

from models.account import Account
from models.entity import Entity, EntityType
from services.auth import hash_password


def seed_auth_accounts(db: Session) -> None:
    """Create demo accounts for seeded human entities if not already present."""
    # Skip if accounts already exist
    if db.query(Account).first():
        return

    # Find seeded human entities
    humans = (
        db.query(Entity)
        .filter(Entity.entity_type == EntityType.human)
        .order_by(Entity.created_at)
        .all()
    )

    demo_credentials = [
        {"email": "alice@pocp.dev", "password": "alice12345", "is_superuser": False},
        {"email": "bob@pocp.dev", "password": "bob12345", "is_superuser": True},
    ]

    for i, human in enumerate(humans):
        if i >= len(demo_credentials):
            break

        creds = demo_credentials[i]
        account = Account(
            entity_id=human.id,
            email=creds["email"],
            hashed_password=hash_password(creds["password"]),
            is_active=True,
            is_superuser=creds["is_superuser"],
        )
        db.add(account)

    db.flush()
