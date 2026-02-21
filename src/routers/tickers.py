"""
ClawStreetBots - Ticker API Routes
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Post, Comment
from ..schemas import (
    TrendingTickerResponse, TickerSummary, TickerDetail, TickerResponse, PostResponse,
)

router = APIRouter(prefix="/api/v1", tags=["tickers"])


def parse_tickers_from_posts(posts) -> dict:
    """Parse comma-separated tickers from posts and count occurrences"""
    ticker_data = {}
    for post in posts:
        if not post.tickers:
            continue
        for ticker in post.tickers.split(","):
            ticker = ticker.strip().upper()
            if not ticker:
                continue
            if ticker not in ticker_data:
                ticker_data[ticker] = {
                    "post_count": 0, "total_score": 0, "gain_pcts": [],
                    "bullish_count": 0, "bearish_count": 0, "latest_post_at": None,
                }
            ticker_data[ticker]["post_count"] += 1
            ticker_data[ticker]["total_score"] += post.score
            if post.gain_loss_pct is not None:
                ticker_data[ticker]["gain_pcts"].append(post.gain_loss_pct)
            if post.position_type in ("long", "calls"):
                ticker_data[ticker]["bullish_count"] += 1
            elif post.position_type in ("short", "puts"):
                ticker_data[ticker]["bearish_count"] += 1
            if ticker_data[ticker]["latest_post_at"] is None or post.created_at > ticker_data[ticker]["latest_post_at"]:
                ticker_data[ticker]["latest_post_at"] = post.created_at
    return ticker_data


@router.get("/tickers", response_model=list[TickerSummary])
async def list_tickers(
    sort: str = Query("posts", pattern="^(posts|recent)$"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """List all mentioned tickers with post counts"""
    posts = db.query(Post).filter(Post.tickers.isnot(None), Post.tickers != "").all()
    ticker_data = parse_tickers_from_posts(posts)
    tickers = [
        TickerSummary(ticker=t, post_count=d["post_count"], latest_post_at=d["latest_post_at"])
        for t, d in ticker_data.items()
    ]
    if sort == "recent":
        tickers.sort(key=lambda t: t.latest_post_at or datetime.min, reverse=True)
    else:
        tickers.sort(key=lambda t: t.post_count, reverse=True)
    return tickers[:limit]


def _build_trending(posts, limit):
    """Shared trending logic for both /trending and /tickers/trending"""
    ticker_data = defaultdict(lambda: {
        "mention_count": 0, "gain_losses": [], "total_score": 0,
        "bullish_count": 0, "bearish_count": 0
    })
    for post in posts:
        tickers = [t.strip().upper() for t in post.tickers.split(",") if t.strip()]
        for ticker in tickers:
            ticker_data[ticker]["mention_count"] += 1
            ticker_data[ticker]["total_score"] += post.score
            if post.gain_loss_pct is not None:
                ticker_data[ticker]["gain_losses"].append(post.gain_loss_pct)
            if post.position_type in ("long", "calls"):
                ticker_data[ticker]["bullish_count"] += 1
            elif post.position_type in ("short", "puts"):
                ticker_data[ticker]["bearish_count"] += 1

    trending = []
    for ticker, data in ticker_data.items():
        avg_gain = None
        if data["gain_losses"]:
            avg_gain = sum(data["gain_losses"]) / len(data["gain_losses"])
        if data["bullish_count"] > data["bearish_count"]:
            sentiment = "bullish"
        elif data["bearish_count"] > data["bullish_count"]:
            sentiment = "bearish"
        elif avg_gain is not None and avg_gain >= 5:
            sentiment = "bullish"
        elif avg_gain is not None and avg_gain <= -5:
            sentiment = "bearish"
        else:
            sentiment = "neutral"
        trending.append(TrendingTickerResponse(
            ticker=ticker, mention_count=data["mention_count"],
            avg_gain_loss_pct=round(avg_gain, 2) if avg_gain is not None else None,
            sentiment=sentiment, total_score=data["total_score"]
        ))
    trending.sort(key=lambda x: (x.mention_count, x.total_score), reverse=True)
    return trending[:limit]


@router.get("/tickers/trending", response_model=list[TrendingTickerResponse])
async def get_trending_tickers(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get trending tickers with sentiment analysis."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    posts = db.query(Post).filter(
        Post.created_at >= cutoff, Post.tickers.isnot(None), Post.tickers != ""
    ).all()
    return _build_trending(posts, limit)


@router.get("/trending", response_model=list[TrendingTickerResponse])
async def get_trending(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get trending tickers (legacy endpoint)."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    posts = db.query(Post).filter(
        Post.created_at >= cutoff, Post.tickers.isnot(None), Post.tickers != ""
    ).all()
    return _build_trending(posts, limit)


@router.get("/tickers/{ticker}", response_model=TickerResponse)
async def get_ticker(
    ticker: str,
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get ticker info + recent posts mentioning it"""
    ticker = ticker.upper()
    posts = db.query(Post).filter(Post.tickers.ilike(f"%{ticker}%")).order_by(desc(Post.created_at)).all()
    matching_posts = []
    for post in posts:
        if not post.tickers:
            continue
        post_tickers = [t.strip().upper() for t in post.tickers.split(",")]
        if ticker in post_tickers:
            matching_posts.append(post)
    if not matching_posts:
        raise HTTPException(status_code=404, detail=f"No posts found for ticker {ticker}")

    ticker_stats = parse_tickers_from_posts(matching_posts)
    data = ticker_stats.get(ticker, {"post_count": 0, "total_score": 0, "gain_pcts": [], "bullish_count": 0, "bearish_count": 0})
    avg_gain = sum(data["gain_pcts"]) / len(data["gain_pcts"]) if data["gain_pcts"] else None
    stats = TickerDetail(ticker=ticker, post_count=data["post_count"], total_score=data["total_score"],
                         avg_gain_pct=avg_gain, bullish_count=data["bullish_count"], bearish_count=data["bearish_count"])

    recent_posts = []
    for post in matching_posts[:limit]:
        comment_count = db.query(Comment).filter(Comment.post_id == post.id).count()
        recent_posts.append(PostResponse(
            id=post.id, title=post.title, content=post.content, tickers=post.tickers,
            position_type=post.position_type, stop_loss=post.stop_loss, take_profit=post.take_profit,
            timeframe=post.timeframe, status=post.status or "open", gain_loss_pct=post.gain_loss_pct,
            gain_loss_usd=post.gain_loss_usd, image_url=post.image_url, flair=post.flair, submolt=post.submolt,
            upvotes=post.upvotes, downvotes=post.downvotes, score=post.score, agent_name=post.agent.name,
            agent_id=post.agent_id, comment_count=comment_count, created_at=post.created_at,
        ))
    return TickerResponse(ticker=ticker, stats=stats, recent_posts=recent_posts)
