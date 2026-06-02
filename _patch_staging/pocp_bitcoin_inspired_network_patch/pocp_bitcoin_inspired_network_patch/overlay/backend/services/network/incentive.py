from __future__ import annotations
from dataclasses import dataclass

@dataclass
class NetworkReward:
    entity_id: str
    role: str
    unit: str
    amount: float
    reason: str

class NetworkIncentiveService:
    def reward_for_role(self, entity_id: str, role: str) -> NetworkReward:
        if role == "verifier_node":
            return NetworkReward(entity_id, role, "CP", 2, "Verified proof event.")
        if role == "indexer_node":
            return NetworkReward(entity_id, role, "CP", 1, "Created event batch and index.")
        if role == "relay_node":
            return NetworkReward(entity_id, role, "CC", 1, "Relayed network messages.")
        return NetworkReward(entity_id, role, "CP", 0, "No default reward configured.")
