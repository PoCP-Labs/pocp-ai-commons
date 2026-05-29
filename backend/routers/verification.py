from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.contribution import ContributionEvent, ContributionStatus
from services.verifiers import MultiVerifierService

router = APIRouter(prefix="/api/v1", tags=["verification"])


@router.post("/contributions/{contribution_id}/auto-verify")
async def auto_verify_contribution(contribution_id: str, db: Session = Depends(get_db)):
    contribution = (
        db.query(ContributionEvent)
        .options(joinedload(ContributionEvent.task), joinedload(ContributionEvent.participants))
        .filter(ContributionEvent.id == contribution_id)
        .first()
    )
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    if contribution.status not in (ContributionStatus.submitted, ContributionStatus.draft):
        raise HTTPException(status_code=400, detail=f"Cannot verify contribution in status: {contribution.status.value}")
    consensus = await MultiVerifierService().verify_contribution(db, contribution)
    db.commit()
    return {"contribution_id": contribution.id, "status": contribution.status.value, "consensus": consensus}
