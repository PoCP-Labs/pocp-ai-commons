from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TokenAccountSnapshot:
    entity_id: str
    cp_balance: float = 0.0
    ai_credit_balance: float = 0.0
    compute_credit_balance: float = 0.0
    pocp_token_balance_internal: float = 0.0
    locked_balance: float = 0.0
    staked_balance: float = 0.0
    pending_rewards: float = 0.0


@dataclass
class TokenTransaction:
    entity_id: str
    unit: str
    amount: float
    transaction_type: str
    reason: str
    reference_id: str | None = None


SUPPORTED_UNITS = {"CP", "AIC", "CC", "PT"}
