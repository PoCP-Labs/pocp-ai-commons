"""Main API router — aggregates all modular routers.

This file re-exports sub-routers for backwards compatibility.
New endpoints should be added to their respective router modules.
"""

from fastapi import APIRouter

from routers.ai_chat import router as ai_chat_router
from routers.auth import router as auth_router
from routers.contributions import router as contributions_router
from routers.entities import router as entities_router
from routers.graph import router as graph_router
from routers.invocations import router as invocations_router
from routers.organizations import router as organizations_router
from routers.skills import router as skills_router
from routers.tasks import router as tasks_router
from routers.wallets import router as wallets_router

# Aggregate router that includes all sub-routers
router = APIRouter()
router.include_router(auth_router)
router.include_router(ai_chat_router)
router.include_router(entities_router)
router.include_router(tasks_router)
router.include_router(contributions_router)
router.include_router(wallets_router)
router.include_router(graph_router)
router.include_router(invocations_router)
router.include_router(organizations_router)
router.include_router(skills_router)
