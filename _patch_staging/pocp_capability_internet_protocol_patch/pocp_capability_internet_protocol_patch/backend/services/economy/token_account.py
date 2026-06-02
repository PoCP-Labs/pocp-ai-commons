from __future__ import annotations
from dataclasses import dataclass
import uuid

@dataclass
class TokenAccount:
    account_id: str
    entity_id: str
    cp_balance: float = 0.0
    ai_credit_balance: float = 0.0
    compute_credit_balance: float = 0.0
    pocp_token_balance_internal: float = 0.0
    staked_balance: float = 0.0
    pending_rewards: float = 0.0
    slashed_amount: float = 0.0
    status: str = "active"

class TokenAccountService:
    def create(self, entity_id: str) -> TokenAccount:
        return TokenAccount(account_id=f"acct_{uuid.uuid4().hex[:16]}", entity_id=entity_id)

    def credit(self, account: TokenAccount, unit: str, amount: float) -> TokenAccount:
        if unit == "CP":
            account.cp_balance += amount
        elif unit == "AIC":
            account.ai_credit_balance += amount
        elif unit == "CC":
            account.compute_credit_balance += amount
        elif unit == "PT_INTERNAL":
            account.pocp_token_balance_internal += amount
        else:
            raise ValueError(f"Unsupported unit: {unit}")
        return account
