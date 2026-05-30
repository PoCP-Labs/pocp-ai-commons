"""AI chat router — closes the genesis loop.

GENESIS.md §4 defines the genesis cycle:
  Contribution → Verification → CP → AI Credits → AI Use → More Contribution

This module implements the "AI Use" step: entities can SPEND AI Credits
to access AI capability (chat, code help, analysis, etc.).

Without this, the genesis loop is broken. AI Credits are earned but never used.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from services.ai_chat import (
    get_total_ai_usage,
    get_usage_history,
    spend_ai_credits,
)

router = APIRouter(prefix="/api/v1/ai", tags=["ai-chat"])


@router.post("/chat")
def ai_chat(
    entity_id: str,
    prompt: str,
    model: str = Query("pocp-default", description="AI model to use"),
    db: Session = Depends(get_db),
):
    """Spend AI Credits to get an AI response.

    This is the genesis loop's 'AI Use' step.

    - Checks entity's AI Credits balance
    - Deducts credits based on prompt length
    - Returns AI response (simulated in MVP; real LLM in v0.3)
    - Records usage in ledger (Protocol Principle 8)
    """
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    result = spend_ai_credits(db, entity_id, prompt, model)

    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["detail"])

    if result["status"] == "insufficient":
        raise HTTPException(
            status_code=402,
            detail={
                "message": result["detail"],
                "required": result["required"],
                "balance": result["balance"],
                "hint": result["hint"],
            },
        )

    return result


@router.get("/chat/{entity_id}/history")
def ai_chat_history(
    entity_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get AI usage history for an entity."""
    return get_usage_history(db, entity_id, skip, limit)


@router.get("/chat/{entity_id}/stats")
def ai_chat_stats(entity_id: str, db: Session = Depends(get_db)):
    """Get aggregate AI usage stats for an entity."""
    return get_total_ai_usage(db, entity_id)
