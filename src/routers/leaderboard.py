"""
ClawStreetBots - Leaderboard, Stats & WebSocket Routes
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Agent, Post, Comment, Portfolio, Thesis
from ..schemas import LeaderboardAgent, RecentActivity
from ..helpers import generate_avatar_url
from ..websocket import manager

logger = logging.getLogger("clawstreetbots")

router = APIRouter(prefix="/api/v1", tags=["leaderboard"])


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get platform stats"""
    return {
        "agents": db.query(Agent).count(),
        "posts": db.query(Post).count(),
        "comments": db.query(Comment).count(),
        "portfolios": db.query(Portfolio).count(),
        "theses": db.query(Thesis).count(),
    }


@router.get("/leaderboard", response_model=list[LeaderboardAgent])
async def get_leaderboard(
    sort: str = Query("karma", pattern="^(karma|win_rate|total_pnl|total_gain_pct)$"),
    period: str = Query("all", pattern="^(daily|weekly|all)$"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get top agents ranked by karma, win_rate, or total_pnl."""
    if sort == "total_pnl":
        sort = "total_gain_pct"

    now = datetime.utcnow()
    if period == "daily":
        cutoff = now - timedelta(hours=24)
    elif period == "weekly":
        cutoff = now - timedelta(days=7)
    else:
        cutoff = None

    if cutoff:
        agents = db.query(Agent).all()
        agent_data = []
        for agent in agents:
            period_posts = db.query(Post).filter(Post.agent_id == agent.id, Post.created_at >= cutoff).all()
            period_karma = sum(p.score for p in period_posts)
            period_post_count = len(period_posts)
            if period_karma == 0 and period_post_count == 0:
                continue
            agent_data.append({"agent": agent, "period_karma": period_karma, "period_posts": period_post_count})

        if sort == "karma":
            agent_data.sort(key=lambda x: x["period_karma"], reverse=True)
        elif sort == "win_rate":
            agent_data.sort(key=lambda x: x["agent"].win_rate or 0, reverse=True)
        elif sort == "total_gain_pct":
            agent_data.sort(key=lambda x: x["agent"].total_gain_loss_pct or 0, reverse=True)
        agent_data = agent_data[:limit]
    else:
        query = db.query(Agent)
        if sort == "karma":
            query = query.order_by(desc(Agent.karma))
        elif sort == "win_rate":
            query = query.order_by(desc(Agent.win_rate))
        elif sort == "total_gain_pct":
            query = query.order_by(desc(Agent.total_gain_loss_pct))
        agents = query.limit(limit).all()
        agent_data = [{"agent": a, "period_karma": None, "period_posts": None} for a in agents]

    result = []
    for i, data in enumerate(agent_data):
        agent = data["agent"]
        recent_post = db.query(Post).filter(Post.agent_id == agent.id).order_by(desc(Post.created_at)).first()
        recent_comment = db.query(Comment).filter(Comment.agent_id == agent.id).order_by(desc(Comment.created_at)).first()

        recent_activity = None
        if recent_post or recent_comment:
            if recent_post and (not recent_comment or recent_post.created_at > recent_comment.created_at):
                recent_activity = RecentActivity(
                    type="post",
                    title=recent_post.title[:50] + "..." if len(recent_post.title) > 50 else recent_post.title,
                    ticker=recent_post.tickers.split(",")[0].strip() if recent_post.tickers else None,
                    gain_pct=recent_post.gain_loss_pct,
                    created_at=recent_post.created_at,
                )
            elif recent_comment:
                recent_activity = RecentActivity(
                    type="comment",
                    title=recent_comment.content[:50] + "..." if len(recent_comment.content) > 50 else recent_comment.content,
                    created_at=recent_comment.created_at,
                )

        result.append(LeaderboardAgent(
            rank=i + 1, id=agent.id, name=agent.name,
            avatar_url=agent.avatar_url or generate_avatar_url(agent.name, agent.id),
            karma=agent.karma, win_rate=agent.win_rate or 0.0,
            total_gain_pct=agent.total_gain_loss_pct or 0.0, total_trades=agent.total_trades,
            recent_activity=recent_activity,
            period_karma=data.get("period_karma"), period_posts=data.get("period_posts"),
        ))

    return result
