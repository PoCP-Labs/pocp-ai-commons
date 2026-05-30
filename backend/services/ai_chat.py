"""AI Credits consumption — closes the genesis loop.

GENESIS.md §4 defines the genesis cycle:
  Contribution → Verification → CP → AI Credits → AI Use → More Contribution

Without AI Use, the cycle is broken. This module closes it.

AI Credits are NOT currency. They are network rights earned through contribution,
spent on AI capability access.
"""

import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.ai_usage import AIUsageRecord
from models.entity import Entity
from models.ledger import LedgerRecord
from models.wallet import CreditTransaction, CreditType, Wallet

logger = logging.getLogger("pocp")


def calculate_credits_cost(prompt: str, model: str = "default") -> float:
    """Calculate AI Credits cost for a prompt.

    Simple model: base cost + per-character cost.
    Future: token-based pricing, model-tier pricing.
    """
    base_cost = 1.0
    per_char_cost = 0.01
    char_count = len(prompt)
    return round(base_cost + (char_count * per_char_cost), 2)


def spend_ai_credits(
    db: Session,
    entity_id: str,
    prompt: str,
    model_provider: str = "pocp-default",
) -> dict:
    """Spend AI Credits for AI capability access.

    This is the genesis loop's "AI Use" step.

    Process:
    1. Find entity and wallet
    2. Check sufficient balance
    3. Calculate cost
    4. Deduct credits
    5. Record AIUsageRecord
    6. Write Ledger Memory (Protocol Principle 8)
    7. Return response
    """
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        return {"status": "error", "detail": "Entity not found"}

    wallet = db.query(Wallet).filter(Wallet.entity_id == entity_id).first()
    if not wallet:
        return {"status": "error", "detail": "No wallet found. Register as human first."}

    cost = calculate_credits_cost(prompt, model_provider)

    if wallet.ai_credits < cost:
        usage = AIUsageRecord(
            entity_id=entity_id,
            model_provider=model_provider,
            prompt=prompt,
            credits_deducted=0,
            status="insufficient",
        )
        db.add(usage)
        db.flush()

        return {
            "status": "insufficient",
            "detail": f"Insufficient AI Credits. Need {cost}, have {wallet.ai_credits}.",
            "required": cost,
            "balance": wallet.ai_credits,
            "hint": "Complete more contribution tasks to earn AI Credits.",
        }

    # Deduct credits
    wallet.ai_credits -= cost

    # Record transaction
    db.add(
        CreditTransaction(
            wallet_id=wallet.id,
            amount=-cost,
            credit_type=CreditType.ai_credits,
            reason=f"AI usage ({model_provider})",
        )
    )

    # Generate AI response (simulated for MVP; real LLM API in v0.3)
    response = _generate_ai_response(prompt, model_provider)

    # Record usage
    usage = AIUsageRecord(
        entity_id=entity_id,
        model_provider=model_provider,
        prompt=prompt,
        response=response,
        credits_deducted=cost,
        status="completed",
    )
    db.add(usage)
    db.flush()

    # Write to Ledger Memory (Protocol Principle 8)
    db.add(
        LedgerRecord(
            contribution_id=None,
            event_type="ai_credits_spent",
            payload={
                "entity_id": entity_id,
                "entity_name": entity.name,
                "model_provider": model_provider,
                "credits_deducted": cost,
                "remaining_balance": round(wallet.ai_credits, 2),
                "usage_id": usage.id,
                "prompt_length": len(prompt),
            },
        )
    )
    db.flush()

    logger.info(f"AI Credits spent: entity={entity_id} cost={cost} model={model_provider}")

    return {
        "status": "completed",
        "response": response,
        "credits_deducted": cost,
        "remaining_balance": round(wallet.ai_credits, 2),
        "model_provider": model_provider,
    }


def _generate_ai_response(prompt: str, model: str) -> str:
    """Generate an AI response. In production, this calls a real LLM API.

    For MVP, provides contextual simulated responses that demonstrate
    the genesis loop in action.
    """
    prompt_lower = prompt.lower()

    if any(w in prompt_lower for w in ["hello", "hi ", "hey"]):
        return (
            "Hello! I'm PoCP AI Commons assistant. "
            "I'm here to help you explore the Proof of Contribution Protocol. "
            "Ask me about AI Credits, contribution tasks, or the genesis loop."
        )

    if "help" in prompt_lower:
        return (
            "I can help you with:\n"
            "- Understanding PoCP (Proof of Contribution Protocol)\n"
            "- Learning about AI Credits and how to earn them\n"
            "- Finding contribution tasks\n"
            "- Exploring the contribution graph\n\n"
            "Try asking: 'What is PoCP?' or 'How do I earn AI Credits?'"
        )

    if "pocp" in prompt_lower or "protocol" in prompt_lower:
        return (
            "PoCP (Proof of Contribution Protocol) records and verifies contributions "
            "from humans and intelligent entities. Instead of asking 'Who owns what?', "
            "PoCP asks 'Who contributed what?'\n\n"
            "Through verified contribution, you earn:\n"
            "- CP (Contribution Points) — non-transferable reputation\n"
            "- AI Credits — spendable on AI capability access\n"
            "- Reputation — for both humans and non-human entities\n\n"
            "See GENESIS.md for the full vision."
        )

    if "credit" in prompt_lower or "earn" in prompt_lower:
        return (
            "AI Credits are PoCP's first network right — earned through verified contribution, "
            "not bought with money.\n\n"
            "You start with 100 credits on registration.\n"
            "Earn more by completing contribution tasks:\n"
            "- Small task: +50 credits\n"
            "- Medium task: +150 credits\n"
            "- Large task: +300 credits\n\n"
            f"Each AI query costs credits based on length. This query cost ~{calculate_credits_cost(prompt)} credits."
        )

    if "graph" in prompt_lower or "contribution" in prompt_lower:
        return (
            "The Contribution Graph is PoCP's core asset. It shows:\n"
            "- Which entities participated in which contributions\n"
            "- How AI agents and Skills were invoked\n"
            "- The flow of value creation and verification\n\n"
            "Every approved contribution adds nodes and edges to the graph."
        )

    # Default contextual response
    word_count = len(prompt.split())
    return (
        f"I processed your {word_count}-word query using {model}. "
        f"In the full implementation (v0.3+), this connects to real LLM APIs "
        f"(DeepSeek, GPT-4o, etc.) with your AI Credits paying for actual compute.\n\n"
        f"This MVP response demonstrates the genesis loop: "
        f"you earned credits through contribution, and now you're using them. "
        f"This query cost {calculate_credits_cost(prompt)} AI Credits."
    )


def get_usage_history(
    db: Session,
    entity_id: str,
    skip: int = 0,
    limit: int = 20,
) -> list[dict]:
    """Get AI usage history for an entity."""
    records = (
        db.query(AIUsageRecord)
        .filter(AIUsageRecord.entity_id == entity_id)
        .order_by(AIUsageRecord.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": r.id,
            "model_provider": r.model_provider,
            "prompt_preview": r.prompt[:100] + "..." if len(r.prompt) > 100 else r.prompt,
            "credits_deducted": r.credits_deducted,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


def get_total_ai_usage(db: Session, entity_id: str) -> dict:
    """Get aggregate AI usage stats for an entity."""
    total = db.query(func.count(AIUsageRecord.id)).filter(
        AIUsageRecord.entity_id == entity_id,
        AIUsageRecord.status == "completed",
    ).scalar() or 0

    total_credits = db.query(func.sum(AIUsageRecord.credits_deducted)).filter(
        AIUsageRecord.entity_id == entity_id,
        AIUsageRecord.status == "completed",
    ).scalar() or 0

    return {
        "total_queries": total,
        "total_credits_spent": round(float(total_credits), 2),
    }
