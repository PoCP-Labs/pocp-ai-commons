"""Skills and agents management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.entity import Entity, EntityStatus, EntityType
from schemas import AgentOut, SkillCreate, SkillOut

router = APIRouter(prefix="/api/v1", tags=["skills", "agents"])


@router.get("/skills", response_model=list[SkillOut])
def list_skills(db: Session = Depends(get_db)):
    from models.skill import Skill

    return db.query(Skill).all()


@router.get("/agents", response_model=list[AgentOut])
def list_agents(db: Session = Depends(get_db)):
    from models.agent import Agent

    return db.query(Agent).all()


@router.post("/skills", response_model=SkillOut, status_code=201)
def create_skill(body: SkillCreate, db: Session = Depends(get_db)):
    from models.skill import Skill

    maintainer = db.query(Entity).filter(Entity.id == body.maintainer_id).first()
    if not maintainer:
        raise HTTPException(status_code=404, detail="Maintainer entity not found")

    entity = Entity(
        entity_type=EntityType.skill,
        name=body.name,
        description=body.description,
        owner_id=body.maintainer_id,
        creator_id=body.maintainer_id,
        status=EntityStatus.active,
    )
    db.add(entity)
    db.flush()

    skill = Skill(
        entity_id=entity.id,
        version=body.version,
        prompt_template=body.prompt_template,
        maintainer_id=body.maintainer_id,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill
