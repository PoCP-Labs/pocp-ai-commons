from __future__ import annotations
from backend.services.cip.types import SettlementData, TokenAccountData

class CIPAccountingService:
    def apply_settlement(self, accounts: dict[str, TokenAccountData], settlement: SettlementData) -> dict[str, TokenAccountData]:
        for p in settlement.participants:
            acct = accounts.setdefault(p.entity_id, TokenAccountData(entity_id=p.entity_id))
            if p.unit == "CP":
                acct.cp_balance += p.amount
            elif p.unit == "AIC":
                acct.ai_credit_balance += p.amount
            elif p.unit == "CC":
                acct.compute_credit_balance += p.amount
            elif p.unit == "PT":
                acct.pocp_token_balance_internal += p.amount
            else:
                raise ValueError(f"Unsupported settlement unit: {p.unit}")
        return accounts
