"""Organization management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.entity import Entity, EntityStatus, EntityType
from schemas import OrganizationCreate, OrganizationOut

router = APIRouter(prefix="/api/v1/organizations", tags=["organizations"])


@router.get("", response_model=list[OrganizationOut])
def list_organizations(db: Session = Depends(get_db)):
    from models.organization import Organization

    return db.query(Organization).all()


@router.post("", response_model=OrganizationOut, status_code=201)
def create_organization(body: OrganizationCreate, db: Session = Depends(get_db)):
    from models.organization import Organization

    proxy = db.query(Entity).filter(Entity.id == body.governance_proxy_id).first()
    if not proxy or proxy.entity_type != EntityType.human:
        raise HTTPException(status_code=400, detail="governance_proxy_id must be a human entity")

    entity = Entity(
        entity_type=EntityType.organization,
        name=body.name,
        description=body.description,
        owner_id=body.governance_proxy_id,
        creator_id=body.creator_id or body.governance_proxy_id,
        status=EntityStatus.active,
    )
    db.add(entity)
    db.flush()

    org = Organization(
        entity_id=entity.id,
        org_type=body.org_type,
        governance_proxy_id=body.governance_proxy_id,
        config={"governance": "human_proxy"},
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org
