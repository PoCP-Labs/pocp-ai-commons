from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from routers.auth import current_user_from_header
from services.ai_chat import chat_and_burn_credits

router = APIRouter(prefix="/api/v1", tags=["ai-chat"])


class ChatIn(BaseModel):
    message: str
    provider: str = "mock"
    model: str | None = None


@router.post("/ai/chat")
async def ai_chat(
    body: ChatIn,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = current_user_from_header(authorization, db)
    result = await chat_and_burn_credits(
        db,
        entity_id=user.entity_id,
        message=body.message,
        provider=body.provider,
        model=body.model,
    )
    db.commit()
    return result


@router.get("/ai/usage")
def ai_usage(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = current_user_from_header(authorization, db)
    from models.ai_usage import AIUsageLog

    rows = (
        db.query(AIUsageLog)
        .filter(AIUsageLog.entity_id == user.entity_id)
        .order_by(AIUsageLog.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": r.id,
            "provider": r.provider,
            "model": r.model,
            "prompt": r.prompt,
            "response": r.response,
            "credits_spent": r.credits_spent,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
