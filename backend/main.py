from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal, check_database, database_dialect, init_db
from routers.api import router
from routers.auth import router as auth_router
from routers.ai_chat import router as ai_chat_router
from routers.verification import router as verification_router
from routers.export import router as export_router
from routers.federation import router as federation_router
from routers.code_attribution import router as code_attribution_router
from routers.external_inspiration import router as external_inspiration_router
from routers.integrations import router as integrations_router
from routers.intelligence import router as intelligence_router
from routers.compute import router as compute_router
from routers.capabilities import router as capabilities_router
from routers.community_partners import router as community_partners_router
from routers.crypto import router as crypto_router
from genesis import ensure_genesis_entities
from seed import seed_demo
from middleware.read_only_mirror import ReadOnlyMirrorMiddleware
from services.federation_sync import sync_all_trusted_peers
from services.ledger_chain import backfill_ledger_hashes
from services.node_mode import is_read_only_mirror, node_mode
from services.trust_config import load_trusted_nodes
from services.trust_ledger import record_trust_list_if_changed

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        ensure_genesis_entities(db)
        from services.external_inspiration import ensure_inspiration_entities, sync_registry_to_records

        ensure_inspiration_entities(db)
        sync_registry_to_records(db)
        from services.federation_community import ensure_federation_peer_entities

        ensure_federation_peer_entities(db)
        from services.capability_import import sync_bundled_capabilities

        sync_bundled_capabilities(db)
        from services.mcp_import import sync_bundled_mcp_capabilities

        sync_bundled_mcp_capabilities(db, activate=False)
        from services.oss_entity_registry import ensure_all_oss_entities

        ensure_all_oss_entities(db)
        from services.community_partner import ensure_partner_entities

        ensure_partner_entities(db, include_declined=True)
        seed_demo(db)
        backfill_ledger_hashes(db)
        record_trust_list_if_changed(db)
        db.commit()
        logger.info("Startup seed complete")
    except Exception:
        logger.exception("Startup seed failed")
        raise
    finally:
        db.close()

    if os.getenv("POCP_FEDERATION_SYNC_ON_STARTUP", "false").lower() == "true":
        if load_trusted_nodes():
            sync_db = SessionLocal()
            try:
                summary = sync_all_trusted_peers(sync_db)
                logger.info(
                    "Federation startup sync: imported=%s skipped=%s errors=%s",
                    summary["imported"],
                    summary["skipped"],
                    summary["errors"],
                )
            except Exception as exc:
                logger.warning("Federation startup sync failed: %s", exc)
            finally:
                sync_db.close()

    yield


app = FastAPI(
    title="PoCP AI Commons API",
    version="0.3.0",
    description=(
        "Entity-Centric Proof of Contribution Protocol — "
        "humans, agents, and skills collaborating on verifiable contributions."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ReadOnlyMirrorMiddleware)

app.include_router(router)
app.include_router(auth_router)
app.include_router(ai_chat_router)
app.include_router(verification_router)
app.include_router(export_router)
app.include_router(federation_router)
app.include_router(code_attribution_router)
app.include_router(external_inspiration_router)
app.include_router(community_partners_router)
app.include_router(integrations_router)
app.include_router(intelligence_router)
app.include_router(capabilities_router)
app.include_router(compute_router)
app.include_router(crypto_router)


@app.get("/health")
def health():
    from services.crypto_suite import active_crypto_suite
    from services.community_partner import build_outreach_report

    db_status = check_database()
    partner_stats = {}
    if db_status == "ok":
        try:
            sync_db = SessionLocal()
            try:
                report = build_outreach_report(sync_db)
                partner_stats = {
                    "partner_count": report.get("partner_count", 0),
                    "high_priority_outreach": len(report.get("high_priority_prospects") or []),
                }
            finally:
                sync_db.close()
        except Exception:
            partner_stats = {"status": "unavailable"}

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "service": "pocp-ai-commons",
        "protocol": "entity-centric-pocp",
        "version": "0.3.0",
        "capability_layer": "0.1",
        "capability_principle": "Everything connects through verified contribution.",
        "crypto_suite": active_crypto_suite(),
        "node_mode": node_mode(),
        "read_only_mirror": is_read_only_mirror(),
        "trusted_peer_count": len(load_trusted_nodes()),
        "community_partners": partner_stats,
        "database": {
            "dialect": database_dialect(),
            "status": db_status,
        },
    }
