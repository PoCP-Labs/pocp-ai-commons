"""Entity management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas import EntityCreate, EntityOut
from services.entities import create_entity, get_entity_by_id, list_entities

router = APIRouter(prefix="/api/v1/entities", tags=["entities"])


@router.get("", response_model=list[EntityOut])
def list_entities_endpoint(
    entity_type: str | None = Query(None, description="Filter by entity type"),
    status: str | None = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_entities(db, entity_type=entity_type, status=status, skip=skip, limit=limit)


@router.get("/{entity_id}", response_model=EntityOut)
def get_entity_endpoint(entity_id: str, db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.post("", response_model=EntityOut, status_code=201)
def create_entity_endpoint(body: EntityCreate, db: Session = Depends(get_db)):
    try:
        entity = create_entity(
            db,
            entity_type=body.entity_type,
            name=body.name,
            description=body.description,
            owner_id=body.owner_id,
            creator_id=body.creator_id,
        )
        return entity
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
