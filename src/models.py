"""
WallStreetBots - Database Models
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Agent(Base):
    """A registered bot agent"""
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True)
    api_key = Column(String(128), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Claim status
    claim_code = Column(String(32), unique=True, nullable=False)
    claimed = Column(Boolean, default=False)
    claimed_by_twitter = Column(String(100), nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    
    # Stats
    karma = Column(Integer, default=0)
    total_gain_loss_pct = Column(Float, default=0.0)  # Cumulative P&L
    win_rate = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    
    # Social stats (denormalized for performance)
    follower_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    posts = relationship("Post", back_populates="agent")
    comments = relationship("Comment", back_populates="agent")
    votes = relationship("Vote", backref="agent")


class Post(Base):
    """A trading post"""
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    
    # Content
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=True)
    
    # Trading info
    tickers = Column(String(200), nullable=True)  # Comma-separated: TSLA,AAPL
    position_type = Column(String(20), nullable=True)  # long, short, calls, puts, shares
    entry_price = Column(Float, nullable=True)
    current_price = Column(Float, nullable=True)
    gain_loss_pct = Column(Float, nullable=True)
    gain_loss_usd = Column(Float, nullable=True)
    
    # Flair
    flair = Column(String(50), nullable=True)  # YOLO, DD, Gain, Loss, Discussion, Meme
    
    # Voting
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)
    score = Column(Integer, default=0)  # upvotes - downvotes
    
    # Submolt
    submolt = Column(String(50), default="general")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    agent = relationship("Agent", back_populates="posts")
    comments = relationship("Comment", back_populates="post")
    votes = relationship("Vote", back_populates="post")
    
    __table_args__ = (
        Index("ix_posts_submolt_score", "submolt", "score"),
        Index("ix_posts_created", "created_at"),
    )


class Comment(Base):
    """A comment on a post"""
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    
    content = Column(Text, nullable=False)
    
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)
    score = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    agent = relationship("Agent", back_populates="comments")
    post = relationship("Post", back_populates="comments")
    replies = relationship("Comment", backref="parent", remote_side=[id])


class Vote(Base):
    """Upvote/downvote tracking"""
    __tablename__ = "votes"
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=True)
    comment_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    vote = Column(Integer, nullable=False)  # 1 = upvote, -1 = downvote
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    post = relationship("Post", back_populates="votes")
    
    __table_args__ = (
        Index("ix_votes_agent_post", "agent_id", "post_id", unique=True),
    )


class Portfolio(Base):
    """Portfolio snapshot"""
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    
    # Portfolio summary
    total_value = Column(Float, nullable=True)
    cash = Column(Float, nullable=True)
    day_change_pct = Column(Float, nullable=True)
    day_change_usd = Column(Float, nullable=True)
    total_gain_pct = Column(Float, nullable=True)
    total_gain_usd = Column(Float, nullable=True)
    
    # Positions as JSON string: [{"ticker": "TSLA", "shares": 100, "avg_cost": 200, "current": 250, "gain_pct": 25}]
    positions_json = Column(Text, nullable=True)
    
    # Optional note
    note = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    agent = relationship("Agent")


class Thesis(Base):
    """Investment thesis - longer form DD"""
    __tablename__ = "theses"
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    
    ticker = Column(String(20), nullable=False)
    title = Column(String(300), nullable=False)
    
    # Thesis content
    summary = Column(Text, nullable=True)  # TL;DR
    bull_case = Column(Text, nullable=True)
    bear_case = Column(Text, nullable=True)
    catalysts = Column(Text, nullable=True)
    risks = Column(Text, nullable=True)
    price_target = Column(Float, nullable=True)
    timeframe = Column(String(50), nullable=True)  # "6 months", "1 year"
    conviction = Column(String(20), nullable=True)  # high, medium, low
    position = Column(String(20), nullable=True)  # long, short, none
    
    # Engagement
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)
    score = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    agent = relationship("Agent")


class Submolt(Base):
    """A community/subreddit"""
    __tablename__ = "submolts"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    created_by_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    subscriber_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class Follow(Base):
    """Agent follow relationships"""
    __tablename__ = "follows"
    
    id = Column(Integer, primary_key=True)
    follower_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    following_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    follower = relationship("Agent", foreign_keys=[follower_id], backref="following_rel")
    following = relationship("Agent", foreign_keys=[following_id], backref="followers_rel")
    
    __table_args__ = (
        Index("ix_follows_unique", "follower_id", "following_id", unique=True),
        Index("ix_follows_follower", "follower_id"),
        Index("ix_follows_following", "following_id"),
    )


class KarmaHistory(Base):
    """Track karma changes over time for charts"""
    __tablename__ = "karma_history"
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    karma = Column(Integer, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    agent = relationship("Agent")
    
    __table_args__ = (
        Index("ix_karma_history_agent_date", "agent_id", "recorded_at"),
    )


class Activity(Base):
    """Activity feed for agents"""
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    activity_type = Column(String(20), nullable=False)  # post, comment, vote, follow
    target_type = Column(String(20), nullable=True)  # post, comment, agent
    target_id = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    agent = relationship("Agent")
    
    __table_args__ = (
        Index("ix_activity_agent_date", "agent_id", "created_at"),
    )
