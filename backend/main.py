from contextlib import asynccontextmanager
import asyncio
import logging
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
except ImportError:
    pass

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import SessionLocal, check_database, database_dialect, get_db, init_db
from routers.api import router
from routers.auth import router as auth_router
from routers.ai_chat import router as ai_chat_router
from routers.verification import router as verification_router
from routers.exchanges import router as exchanges_router
from routers.export import router as export_router
from routers.federation import router as federation_router
from routers.code_attribution import router as code_attribution_router
from routers.external_inspiration import router as external_inspiration_router
from routers.integrations import router as integrations_router
from routers.intelligence import router as intelligence_router
from routers.compute import router as compute_router
from routers.capabilities import router as capabilities_router
from routers.capability_registry import router as capability_registry_router
from routers.capability_invocations import router as capability_invocations_router
from routers.community_partners import router as community_partners_router
from routers.crypto import router as crypto_router
from routers.wallet import router as wallet_router
from routers.meta_agents import router as meta_agents_router
from routers.agent_studio import router as agent_studio_router
from routers.locale import router as locale_router
from routers.nodes import entity_router as nodes_entity_router
from routers.nodes import router as nodes_router
from genesis import ensure_genesis_entities
from seed import seed_demo
from middleware.read_only_mirror import ReadOnlyMirrorMiddleware
from services.federation_sync import sync_all_trusted_peers
from services.ledger_chain import backfill_ledger_hashes
from services.node_mode import is_read_only_mirror, node_mode
from services.trust_config import load_trusted_nodes
from services.trust_ledger import record_trust_list_if_changed

logger = logging.getLogger(__name__)


async def _compute_auto_balance_loop() -> None:
    from services.compute_balance_cron import (
        auto_balance_enabled,
        auto_balance_interval_minutes,
        run_auto_balance_cycle,
    )
    from services.node_mode import is_read_only_mirror

    interval_sec = auto_balance_interval_minutes() * 60
    while True:
        await asyncio.sleep(interval_sec)
        if not auto_balance_enabled() or is_read_only_mirror():
            continue
        db = SessionLocal()
        try:
            result = run_auto_balance_cycle(db)
            if result.get("status") == "completed":
                db.commit()
                recycled = sum(
                    1
                    for action in result.get("actions") or []
                    if action.get("action") == "recycled"
                )
                if recycled:
                    logger.info(
                        "Compute auto-balance: targets=%s recycled=%s",
                        result.get("targets"),
                        recycled,
                    )
            else:
                db.rollback()
        except Exception as exc:
            db.rollback()
            logger.warning("Compute auto-balance cycle failed: %s", exc)
        finally:
            db.close()


async def _federation_peer_maintenance_loop() -> None:
    """Re-probe discovered peers and refresh addrbook (Bitcoin AddrMan maintenance)."""
    from services.federation_peer_addrbook import maintain_discovered_peers, peer_maintenance_enabled
    from services.node_mode import is_read_only_mirror

    try:
        interval = int(os.getenv("POCP_PEER_MAINTENANCE_INTERVAL_SEC", "120"))
    except ValueError:
        interval = 120
    interval = max(30, interval)
    while True:
        await asyncio.sleep(interval)
        if not peer_maintenance_enabled():
            continue
        if is_read_only_mirror():
            continue
        db = SessionLocal()
        try:
            summary = maintain_discovered_peers(db)
            db.commit()
            if summary.get("probed", 0) > 0:
                logger.info(
                    "Peer maintenance: probed=%s ok=%s failed=%s banned=%s",
                    summary.get("probed"),
                    summary.get("ok"),
                    summary.get("failed"),
                    summary.get("banned"),
                )
        except Exception as exc:
            logger.warning("Peer maintenance cycle failed: %s", exc)
            db.rollback()
        finally:
            db.close()


async def _federation_auto_discover_loop() -> None:
    """Periodic peer discovery (Bitcoin-style addr discovery analogue)."""
    from routers.federation import AutoDiscoverPeersIn, auto_discover_peers
    from services.node_mode import is_read_only_mirror

    try:
        interval = int(os.getenv("POCP_PEER_DISCOVERY_INTERVAL_SEC", "60"))
    except ValueError:
        interval = 60
    interval = max(15, interval)
    while True:
        await asyncio.sleep(interval)
        if os.getenv("POCP_PEER_AUTO_DISCOVER", "false").lower() not in ("1", "true", "yes", "on"):
            continue
        if is_read_only_mirror():
            continue
        db = SessionLocal()
        try:
            summary = auto_discover_peers(
                AutoDiscoverPeersIn(
                    candidate_urls=[],
                    include_localhost_scan=os.getenv("POCP_PEER_DISCOVERY_LOCALHOST", "true").lower()
                    in ("1", "true", "yes", "on"),
                    max_candidates=int(os.getenv("POCP_PEER_DISCOVERY_MAX_CANDIDATES", "24")),
                ),
                db=db,
            )
            if summary.get("discovered_count", 0) > 0:
                logger.info(
                    "Peer auto-discovery: discovered=%s scanned=%s",
                    summary.get("discovered_count"),
                    summary.get("scanned"),
                )
        except Exception as exc:
            logger.warning("Peer auto-discovery cycle failed: %s", exc)
            db.rollback()
        finally:
            db.close()


def _full_seed_enabled() -> bool:
    """Optional demo richness: partners, inspirations, bundled capabilities."""
    return os.getenv("POCP_FULL_SEED", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        ensure_genesis_entities(db)
        if _full_seed_enabled():
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
        logger.info("Startup seed complete (full_seed=%s)", _full_seed_enabled())
        if os.getenv("POCP_NEXUS_AUTOPILOT", "true").lower() == "true":
            from services.agent_studio.nexus_autopilot import run_nexus_autopilot

            ap_db = SessionLocal()
            try:
                tick = run_nexus_autopilot(ap_db)
                ap_db.commit()
                logger.info(
                    "Nexus-0 autopilot: mode=%s pending=%s",
                    tick.get("mode"),
                    tick.get("pending_handoff_count"),
                )
            except Exception:
                ap_db.rollback()
                logger.warning("Nexus-0 autopilot tick failed", exc_info=True)
            finally:
                ap_db.close()
    except Exception:
        logger.exception("Startup seed failed")
        raise
    finally:
        db.close()

    super_loop_task = None
    from services.agent_studio.nexus_super_loop import (
        cursor_backend_automation_enabled,
        super_loop_backend_enabled,
        super_loop_host_mode,
    )

    if super_loop_host_mode():
        logger.info(
            "Nexus super-loop host mode: in-container loops disabled; run scripts/run-studio-super-loop.ps1"
        )

    if super_loop_backend_enabled():

        async def _nexus_super_loop() -> None:
            from services.agent_studio.nexus_super_loop import run_nexus_super_tick

            try:
                interval = int(os.getenv("POCP_NEXUS_SUPER_LOOP_INTERVAL_SEC", "600"))
            except ValueError:
                interval = 600
            await asyncio.sleep(20)
            while True:
                db = SessionLocal()
                try:
                    tick = run_nexus_super_tick(db)
                    db.commit()
                    logger.info(
                        "Nexus super-loop: nexus=%s cursor_processed=%s pending=%s human_required=%s",
                        (tick.get("nexus") or {}).get("mode"),
                        (tick.get("cursor") or {}).get("processed_count"),
                        tick.get("pending_for_cursor"),
                        tick.get("human_required"),
                    )
                except Exception:
                    db.rollback()
                    logger.warning("Nexus super-loop tick failed", exc_info=True)
                finally:
                    db.close()
                await asyncio.sleep(interval)

        super_loop_task = asyncio.create_task(_nexus_super_loop())
        logger.info("Nexus super-loop background task started (PDCA + Cursor + heal)")

    cursor_task = None
    if super_loop_task is None and cursor_backend_automation_enabled():

        async def _cursor_automation_loop() -> None:
            from services.agent_studio.cursor_automation import run_cursor_automation_tick
            from services.agent_studio.cursor_bridge import automation_enabled

            try:
                interval = int(os.getenv("POCP_CURSOR_AUTOMATION_INTERVAL_SEC", "300"))
            except ValueError:
                interval = 300
            await asyncio.sleep(15)
            while True:
                if automation_enabled():
                    db = SessionLocal()
                    try:
                        tick = run_cursor_automation_tick(db)
                        db.commit()
                        if tick.get("processed"):
                            logger.info(
                                "Cursor automation: processed %s handoff(s)",
                                len(tick["processed"]),
                            )
                    except Exception:
                        db.rollback()
                        logger.warning("Cursor automation tick failed", exc_info=True)
                    finally:
                        db.close()
                await asyncio.sleep(interval)

        cursor_task = asyncio.create_task(_cursor_automation_loop())
        logger.info("Cursor automation background loop started")

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

    balance_task: asyncio.Task | None = None
    if os.getenv("POCP_COMPUTE_AUTO_BALANCE", "").lower() in ("1", "true", "yes"):
        balance_task = asyncio.create_task(_compute_auto_balance_loop())
        logger.info("Compute auto-balance background loop started")

    discovery_task: asyncio.Task | None = None
    maintenance_task: asyncio.Task | None = None
    if os.getenv("POCP_PEER_AUTO_DISCOVER", "false").lower() in ("1", "true", "yes", "on"):
        discovery_task = asyncio.create_task(_federation_auto_discover_loop())
        logger.info("Federation peer auto-discovery loop started")
    if os.getenv("POCP_PEER_MAINTENANCE", "true").lower() in ("1", "true", "yes", "on"):
        maintenance_task = asyncio.create_task(_federation_peer_maintenance_loop())
        logger.info("Federation peer maintenance loop started")

    yield

    for task in (discovery_task, maintenance_task, balance_task, cursor_task, super_loop_task):
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="PoCP AI Commons API",
    version="0.4.0",
    description=(
        "Proof of Contribution Protocol — "
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
app.include_router(exchanges_router)
app.include_router(federation_router)
app.include_router(code_attribution_router)
app.include_router(external_inspiration_router)
app.include_router(community_partners_router)
app.include_router(integrations_router)
app.include_router(intelligence_router)
app.include_router(capabilities_router)
app.include_router(capability_registry_router)
app.include_router(capability_invocations_router)
app.include_router(compute_router)
app.include_router(crypto_router)
app.include_router(wallet_router)
app.include_router(meta_agents_router)
app.include_router(agent_studio_router)
app.include_router(locale_router)
app.include_router(nodes_router)
app.include_router(nodes_entity_router)


@app.get("/.well-known/pocp-node.json")
def well_known_pocp_node(db: Session = Depends(get_db)):
    """Instance-level node manifest — capability-first discovery."""
    from services.node_manifest import build_instance_node_manifest

    return build_instance_node_manifest(db)


@app.get("/.well-known/agent.json")
def well_known_agent_card(db: Session = Depends(get_db)):
    """A2A discovery — node-level Agent Card (BI-1)."""
    from services.a2a_agent_card import build_node_agent_card

    return build_node_agent_card(db)


@app.get("/health")
def health():
    from services.crypto_suite import active_crypto_suite

    db_status = check_database()
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "service": "pocp-ai-commons",
        "protocol": "pocp-v0.1",
        "version": "0.4.0",
        "stage": "phase-a",
        "full_seed": _full_seed_enabled(),
        "crypto_suite": active_crypto_suite(),
        "node_mode": node_mode(),
        "read_only_mirror": is_read_only_mirror(),
        "trusted_peer_count": len(load_trusted_nodes()),
        "database": {
            "dialect": database_dialect(),
            "status": db_status,
        },
    }
