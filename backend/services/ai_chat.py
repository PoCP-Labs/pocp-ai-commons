import hashlib
import os

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from genesis import LUMEN_0_ID
from models.ai_usage import AIUsageLog
from models.wallet import CreditTransaction, CreditType, Wallet
from services.anti_abuse import check_daily_ai_burn_limit
from services.exchange_spine import emit_exchange_settled
from services.invocation_ledger import build_invocation_ref
from services.ledger_chain import append_ledger_record
from services.llama_cpp_client import llama_cpp_base_url, llama_cpp_chat_enabled, llama_cpp_chat_model
from services.ollama_client import ollama_base_url, ollama_chat_model
from services.vllm_client import vllm_base_url, vllm_chat_enabled, vllm_chat_model

AI_CHAT_COST_PER_MESSAGE = float(os.getenv("AI_CHAT_COST_PER_MESSAGE", "5"))


async def generate_ai_reply(
    message: str,
    provider: str = "mock",
    model: str | None = None,
    *,
    system_content: str | None = None,
) -> tuple[str, str, str]:
    provider = (provider or "mock").lower()
    system = system_content or (
        "You are PoCP AI Commons assistant. Be helpful, concise, and educational."
    )
    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": message},
                    ],
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"], "openai", model

    if provider == "ollama":
        model = model or ollama_chat_model()
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{ollama_base_url()}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": message},
                    ],
                    "stream": False,
                },
            )
            resp.raise_for_status()
            content = (resp.json().get("message") or {}).get("content") or ""
            return content, "ollama", model

    if provider == "llama_cpp" and llama_cpp_chat_enabled():
        model = model or llama_cpp_chat_model()
        base_url = llama_cpp_base_url()
        timeout = float(os.getenv("LLAMA_CPP_TIMEOUT_SECONDS", "120"))
        headers = {"Content-Type": "application/json"}
        api_key = os.getenv("LLAMA_CPP_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": message},
                    ],
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"], "llama_cpp", model

    if provider == "vllm" and vllm_chat_enabled():
        model = model or vllm_chat_model()
        base_url = vllm_base_url()
        timeout = float(os.getenv("VLLM_TIMEOUT_SECONDS", "120"))
        headers = {"Content-Type": "application/json"}
        api_key = os.getenv("VLLM_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": message},
                    ],
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"], "vllm", model

    # mock fallback keeps MVP usable without paid API keys
    return (
        "[Mock AI] I received your request and would help you turn it into a clearer contribution or learning output: "
        + message[:500],
        "mock",
        model or "mock-chat",
    )


async def chat_and_burn_credits(
    db: Session,
    *,
    entity_id: str,
    message: str,
    provider: str = "mock",
    model: str | None = None,
) -> dict:
    wallet = db.query(Wallet).filter(Wallet.entity_id == entity_id).first()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    cost = AI_CHAT_COST_PER_MESSAGE
    check_daily_ai_burn_limit(db, entity_id, cost)

    if wallet.ai_credits < cost:
        raise HTTPException(status_code=402, detail="Insufficient AI Credits")

    reply, actual_provider, actual_model = await generate_ai_reply(message, provider, model)
    wallet.ai_credits -= cost
    chat_tx = CreditTransaction(
        wallet_id=wallet.id,
        amount=-cost,
        credit_type=CreditType.ai_credits,
        reason="AI chat usage",
    )
    db.add(chat_tx)
    usage = AIUsageLog(
        entity_id=entity_id,
        wallet_id=wallet.id,
        provider=actual_provider,
        model=actual_model,
        prompt=message,
        response=reply,
        credits_spent=cost,
    )
    db.add(usage)
    append_ledger_record(
        db,
        contribution_id=None,
        event_type="ai_credits_burned",
        payload={
            "entity_id": entity_id,
            "wallet_id": wallet.id,
            "provider": actual_provider,
            "model": actual_model,
            "credits_spent": cost,
            "remaining_credits": wallet.ai_credits,
        },
    )
    chat_provider_entity = os.getenv("POCP_CHAT_PROVIDER_ENTITY_ID", LUMEN_0_ID)
    receipt_material = f"{entity_id}|{actual_provider}|{actual_model}|{cost}|{message[:128]}"
    receipt_hash = f"sha256:{hashlib.sha256(receipt_material.encode()).hexdigest()}"
    exchange_record = emit_exchange_settled(
        db,
        consumer_entity_id=entity_id,
        provider_entity_ids=[chat_provider_entity],
        exchange_kind="capability",
        credit_transactions=[chat_tx],
        receipt_hash=receipt_hash,
        capability="reasoning",
        usage={
            "metering_mode": "flat",
            "bc_debited": cost,
            "provider": actual_provider,
            "model": actual_model,
        },
        legacy_event_type="ai_credits_burned",
        settlement_policy="ai_chat.v1",
        invocation_ref=build_invocation_ref(
            source_entity_id=entity_id,
            target_entity_id=chat_provider_entity,
            capability="reasoning",
            usage={
                "metering_mode": "flat",
                "bc_debited": cost,
                "provider": actual_provider,
                "model": actual_model,
            },
            receipt_hash=receipt_hash,
            verification_ref=receipt_hash,
            status="settled",
        ),
    )
    db.flush()
    return {
        "reply": reply,
        "credits_spent": cost,
        "remaining_credits": wallet.ai_credits,
        "provider": actual_provider,
        "model": actual_model,
        "exchange_id": (exchange_record.payload or {}).get("exchange_id"),
    }
