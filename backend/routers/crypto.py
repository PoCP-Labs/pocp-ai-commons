"""Crypto agility and quantum-readiness API."""

from fastapi import APIRouter

from services.crypto_suite import crypto_readiness_report, list_crypto_suites, suite_spec

router = APIRouter(prefix="/api/v1/crypto", tags=["crypto"])


@router.get("/suites")
def get_crypto_suites():
    """Registered PoCP crypto suites (classic + hybrid transition)."""
    return {
        "compat": "pocp.crypto_agility.v0.1",
        "suites": list_crypto_suites(),
    }


@router.get("/readiness")
def get_quantum_readiness():
    """Operator snapshot: active suite, PQC keys, minimum policy, NIST target."""
    return {
        "compat": "pocp.quantum_readiness.v0.1",
        **crypto_readiness_report(),
    }


@router.get("/suites/{suite_id}")
def get_crypto_suite(suite_id: str):
    try:
        return suite_spec(suite_id)
    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=str(exc)) from exc
