from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal, init_db
from routers.api import router
from seed import seed_demo


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
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


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "pocp-ai-commons",
        "protocol": "entity-centric-pocp",
        "version": "0.2.0",
    }
