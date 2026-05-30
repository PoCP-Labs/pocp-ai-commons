"""Application startup and configuration."""

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, OperationalError

from config import CORS_ORIGINS, DATABASE_URL, LOG_LEVEL, RATE_LIMIT, SEED_ON_STARTUP
from database import SessionLocal, init_db
from middleware.rate_limit import RateLimitMiddleware
from middleware.request_id import RequestIDMiddleware
from routers.api import router
from seed import seed_demo
from services.migrations import run_migrations

# --- Structured Logging ---
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s %(levelname)s [%(name)s] request_id=%(request_id)s %(message)s",
)
logger = logging.getLogger("pocp")


def _run_startup_tasks(app: FastAPI):
    """Run database init, migrations, and seed data."""
    # 1. Create tables (for SQLite, handles new DBs)
    init_db()

    # 2. Run alembic migrations (for existing DBs needing schema changes)
    if DATABASE_URL.startswith("sqlite"):
        # SQLite: skip alembic, use create_all (simpler for dev)
        logger.info("SQLite detected — using metadata.create_all for schema")
    else:
        # PostgreSQL/other: use alembic migrations
        try:
            run_migrations()
            logger.info("Database migrations applied successfully")
        except Exception as e:
            logger.warning(f"Migration failed (non-fatal for dev): {e}")

    # 3. Seed demo data
    if SEED_ON_STARTUP:
        db = SessionLocal()
        try:
            seed_demo(db)
            logger.info("Demo data seeded successfully")
        except Exception as e:
            logger.warning(f"Seed demo failed (non-fatal): {e}")
        finally:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and optionally seed demo data."""
    _run_startup_tasks(app)
    yield
    logger.info("Application shutdown")


app = FastAPI(
    title="PoCP AI Commons API",
    version="0.2.0",
    description=(
        "Entity-Centric Proof of Contribution Protocol — "
        "humans, agents, and skills collaborating on verifiable contributions."
    ),
    lifespan=lifespan,
)

# --- Middleware Stack (order matters: last added = first executed) ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware, rate_per_minute=RATE_LIMIT)
app.add_middleware(RequestIDMiddleware)


# --- Request Logging Middleware ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = getattr(request.state, "request_id", "unknown")
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    logger.info(
        f"{request.method} {request.url.path} {response.status_code} "
        f"duration={duration:.3f}s",
        extra={"request_id": request_id},
    )
    return response


# --- Routers ---
app.include_router(router)


# --- Error Handlers ---
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={
            "error": "conflict",
            "detail": str(exc.orig) if hasattr(exc, "orig") else "Database integrity violation",
        },
    )


@app.exception_handler(OperationalError)
async def operational_error_handler(request: Request, exc: OperationalError):
    return JSONResponse(
        status_code=503,
        content={"error": "service_unavailable", "detail": "Database connection error"},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "detail": exc.errors()},
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "detail": exc.errors()},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"error": "bad_request", "detail": str(exc)},
    )


@app.exception_handler(PermissionError)
async def permission_error_handler(request: Request, exc: PermissionError):
    return JSONResponse(
        status_code=403,
        content={"error": "forbidden", "detail": str(exc)},
    )


# --- Health Check ---
@app.get("/health")
def health():
    """Enhanced health check with database connectivity verification."""
    health_info = {
        "status": "ok",
        "service": "pocp-ai-commons",
        "protocol": "entity-centric-pocp",
        "version": "0.2.0",
        "database": DATABASE_URL.split("://")[0],
        "auth_mode": os.getenv("AUTH_MODE", "demo"),
    }

    # Check database connectivity
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        health_info["database_status"] = "connected"
    except Exception as e:
        health_info["database_status"] = "error"
        health_info["database_error"] = str(e)
        health_info["status"] = "degraded"

    return health_info
