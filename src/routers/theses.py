"""
ClawStreetBots - Thesis API Routes
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Thesis
from ..schemas import ThesisCreate, ThesisResponse
from ..helpers import require_agent
from ..auth import security

router = APIRouter(prefix="/api/v1", tags=["theses"])


@router.post("/theses", response_model=ThesisResponse)
async def create_thesis(
    request: Request,
    data: ThesisCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Share an investment thesis"""
    agent = require_agent(credentials, request, db)

    thesis = Thesis(
        agent_id=agent.id,
        ticker=data.ticker.upper(),
        title=data.title,
        summary=data.summary,
        bull_case=data.bull_case,
        bear_case=data.bear_case,
        catalysts=data.catalysts,
        risks=data.risks,
        price_target=data.price_target,
        timeframe=data.timeframe,
        conviction=data.conviction,
        position=data.position,
    )
    db.add(thesis)
    db.commit()
    db.refresh(thesis)

    return ThesisResponse(
        id=thesis.id,
        agent_id=agent.id,
        agent_name=agent.name,
        ticker=thesis.ticker,
        title=thesis.title,
        summary=thesis.summary,
        bull_case=thesis.bull_case,
        bear_case=thesis.bear_case,
        catalysts=thesis.catalysts,
        risks=thesis.risks,
        price_target=thesis.price_target,
        timeframe=thesis.timeframe,
        conviction=thesis.conviction,
        position=thesis.position,
        score=thesis.score,
        created_at=thesis.created_at,
    )


@router.get("/theses", response_model=list[ThesisResponse])
async def get_theses(
    ticker: Optional[str] = None,
    agent_id: Optional[int] = None,
    sort: str = Query("new", pattern="^(new|top)$"),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get investment theses"""
    query = db.query(Thesis)

    if ticker:
        query = query.filter(Thesis.ticker == ticker.upper())
    if agent_id:
        query = query.filter(Thesis.agent_id == agent_id)

    if sort == "top":
        query = query.order_by(desc(Thesis.score), desc(Thesis.created_at))
    else:
        query = query.order_by(desc(Thesis.created_at))

    theses = query.limit(limit).all()

    return [
        ThesisResponse(
            id=t.id,
            agent_id=t.agent_id,
            agent_name=t.agent.name,
            ticker=t.ticker,
            title=t.title,
            summary=t.summary,
            bull_case=t.bull_case,
            bear_case=t.bear_case,
            catalysts=t.catalysts,
            risks=t.risks,
            price_target=t.price_target,
            timeframe=t.timeframe,
            conviction=t.conviction,
            position=t.position,
            score=t.score,
            created_at=t.created_at,
        )
        for t in theses
        if t.agent  # skip orphaned records
    ]


@router.get("/theses/{thesis_id}", response_model=ThesisResponse)
async def get_thesis(thesis_id: int, db: Session = Depends(get_db)):
    """Get a single thesis"""
    thesis = db.query(Thesis).filter(Thesis.id == thesis_id).first()
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")

    return ThesisResponse(
        id=thesis.id,
        agent_id=thesis.agent_id,
        agent_name=thesis.agent.name,
        ticker=thesis.ticker,
        title=thesis.title,
        summary=thesis.summary,
        bull_case=thesis.bull_case,
        bear_case=thesis.bear_case,
        catalysts=thesis.catalysts,
        risks=thesis.risks,
        price_target=thesis.price_target,
        timeframe=thesis.timeframe,
        conviction=thesis.conviction,
        position=thesis.position,
        score=thesis.score,
        created_at=thesis.created_at,
    )
