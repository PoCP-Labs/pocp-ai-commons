import json
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.entity import Entity
from models.ledger import LedgerRecord
from models.wallet import ReputationScore, Wallet
from schemas.federation import FederationNodeOut, ImportEventPayload, TrustListOut, TrustedNode

router = APIRouter(prefix="/api/v1/federation", tags=["federation"])

_NODE_ID = os.getenv("POCP_NODE_ID", f"pocp-node-{uuid.uuid4().hex[:8]}")
_SPEC_VERSION = "0.1"


def _trusted_nodes() -> list[TrustedNode]:
    raw = os.getenv("POCP_TRUSTED_NODES", "[]")
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [TrustedNode(**item) for item in items if isinstance(item, dict)]


@router.get("/node", response_model=FederationNodeOut)
def get_node_info():
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    return FederationNodeOut(
        node_id=_NODE_ID,
        spec_version=_SPEC_VERSION,
        public_endpoints=[
            f"{backend_url}/api/v1/ledger/export",
            f"{backend_url}/api/v1/entities/{{id}}/portable",
            f"{backend_url}/api/v1/ledger/verify",
        ],
    )


@router.get("/trust", response_model=TrustListOut)
def get_trust_list():
    return TrustListOut(trusted_nodes=_trusted_nodes())


@router.post("/import")
def import_federated_event(_body: ImportEventPayload):
    raise HTTPException(
        status_code=501,
        detail="Federation import planned for v0.2; see docs/FEDERATION-v0.1.md",
    )
