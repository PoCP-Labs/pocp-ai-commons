from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal, check_database, database_dialect, init_db
from routers.api import router
from routers.auth import router as auth_router
from routers.ai_chat import router as ai_chat_router
from routers.verification import router as verification_router
from routers.export import router as export_router
from routers.federation import router as federation_router
from genesis import ensure_genesis_entities
from seed import seed_demo
from services.ledger_chain import backfill_ledger_hashes


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        ensure_genesis_entities(db)
        backfill_ledger_hashes(db)
        db.commit()
        seed_demo(db)
    finally:
        db.close()
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

app.include_router(router)
app.include_router(auth_router)
app.include_router(ai_chat_router)
app.include_router(verification_router)
app.include_router(export_router)
app.include_router(federation_router)


@app.get("/health")
def health():
    db_status = check_database()
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "service": "pocp-ai-commons",
        "protocol": "entity-centric-pocp",
        "version": "0.3.0",
        "database": {
            "dialect": database_dialect(),
            "status": db_status,
        },
    }
