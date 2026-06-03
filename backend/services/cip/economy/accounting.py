from __future__ import annotations

from services.cip.types import SettlementData, TokenAccountData


class CIPAccountingService:
    """Internal accounting units only: CP, AIC, CC, PT."""

    def apply_settlement(
        self,
        accounts: dict[str, TokenAccountData],
        settlement: SettlementData,
    ) -> dict[str, TokenAccountData]:
        for participant in settlement.participants:
            account = accounts.setdefault(
                participant.entity_id,
                TokenAccountData(entity_id=participant.entity_id),
            )
            if participant.unit == "CP":
                account.cp_balance += participant.amount
            elif participant.unit == "AIC":
                account.ai_credit_balance += participant.amount
            elif participant.unit == "CC":
                account.compute_credit_balance += participant.amount
            elif participant.unit == "PT":
                account.pocp_token_balance_internal += participant.amount
            else:
                raise ValueError(f"Unsupported settlement unit: {participant.unit}")
        return accounts
