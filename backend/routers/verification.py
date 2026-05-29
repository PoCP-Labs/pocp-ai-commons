from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.contribution import ContributionEvent, ContributionStatus
from models.user_account import UserAccount
from routers.auth import require_current_user
from services.verifiers import MultiVerifierService

router = APIRouter(prefix="/api/v1", tags=["verification"])


@router.post("/contributions/{contribution_id}/auto-verify")
async def auto_verify_contribution(
    contribution_id: str,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    contribution = (
        db.query(ContributionEvent)
        .options(joinedload(ContributionEvent.task), joinedload(ContributionEvent.participants))
        .filter(ContributionEvent.id == contribution_id)
        .first()
    )
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    if contribution.primary_entity_id != current_user.entity_id:
        raise HTTPException(status_code=403, detail="Only the contribution owner can request auto verification")
    if contribution.status not in (ContributionStatus.submitted, ContributionStatus.draft):
        raise HTTPException(status_code=400, detail=f"Cannot verify contribution in status: {contribution.status.value}")
    consensus = await MultiVerifierService().verify_contribution(db, contribution)
    db.commit()
    return {"contribution_id": contribution.id, "status": contribution.status.value, "consensus": consensus}
