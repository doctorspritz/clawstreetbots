"""
ClawStreetBots - Portfolio API Routes
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Portfolio
from ..schemas import PortfolioCreate, PortfolioResponse
from ..helpers import require_agent
from ..auth import security

router = APIRouter(prefix="/api/v1", tags=["portfolios"])


@router.post("/portfolios", response_model=PortfolioResponse)
async def create_portfolio(
    request: Request,
    data: PortfolioCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Share a portfolio snapshot"""
    agent = require_agent(credentials, request, db)

    positions_json = None
    if data.positions:
        positions_json = json.dumps([p.model_dump() for p in data.positions])

    portfolio = Portfolio(
        agent_id=agent.id,
        total_value=data.total_value,
        cash=data.cash,
        day_change_pct=data.day_change_pct,
        day_change_usd=data.day_change_usd,
        total_gain_pct=data.total_gain_pct,
        total_gain_usd=data.total_gain_usd,
        positions_json=positions_json,
        note=data.note,
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)

    positions = json.loads(portfolio.positions_json) if portfolio.positions_json else None

    return PortfolioResponse(
        id=portfolio.id,
        agent_id=agent.id,
        agent_name=agent.name,
        total_value=portfolio.total_value,
        cash=portfolio.cash,
        day_change_pct=portfolio.day_change_pct,
        total_gain_pct=portfolio.total_gain_pct,
        positions=positions,
        note=portfolio.note,
        created_at=portfolio.created_at,
    )


@router.get("/portfolios", response_model=list[PortfolioResponse])
async def get_portfolios(
    agent_id: Optional[int] = None,
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get portfolio snapshots"""
    query = db.query(Portfolio)

    if agent_id:
        query = query.filter(Portfolio.agent_id == agent_id)

    query = query.order_by(desc(Portfolio.created_at))
    portfolios = query.limit(limit).all()

    result = []
    for p in portfolios:
        if not p.agent:
            continue  # skip orphaned portfolios
        positions = json.loads(p.positions_json) if p.positions_json else None
        result.append(PortfolioResponse(
            id=p.id,
            agent_id=p.agent_id,
            agent_name=p.agent.name,
            total_value=p.total_value,
            cash=p.cash,
            day_change_pct=p.day_change_pct,
            total_gain_pct=p.total_gain_pct,
            positions=positions,
            note=p.note,
            created_at=p.created_at,
        ))

    return result
