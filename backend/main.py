from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal, init_db
from routers.api import router
from routers.auth import router as auth_router
from routers.ai_chat import router as ai_chat_router
from routers.verification import router as verification_router
from genesis import ensure_genesis_entities
from seed import seed_demo


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        ensure_genesis_entities(db)
        db.commit()
        seed_demo(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="PoCP AI Commons API",
    version="0.2.0",
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


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "pocp-ai-commons",
        "protocol": "entity-centric-pocp",
        "version": "0.2.0",
    }
