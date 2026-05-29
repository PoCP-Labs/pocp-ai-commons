from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal, init_db
from routers.api import router
from routers.auth import router as auth_router
from routers.protected import router as protected_router
from seed import seed_demo
from seed_auth import seed_auth_accounts


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_demo(db)
        seed_auth_accounts(db)
        db.commit()
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
app.include_router(protected_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "pocp-ai-commons",
        "protocol": "entity-centric-pocp",
        "version": "0.2.0",
    }
