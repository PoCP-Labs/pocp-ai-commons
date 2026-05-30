"""Contribution graph endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas import ContributionGraph
from services.graph import build_contribution_graph

router = APIRouter(prefix="/api/v1", tags=["graph"])


@router.get("/graph", response_model=ContributionGraph)
def get_contribution_graph(db: Session = Depends(get_db)):
    return build_contribution_graph(db)
