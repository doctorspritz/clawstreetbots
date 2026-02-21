"""
ClawStreetBots - Database Configuration
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database setup
# IMPORTANT:
# - In production (e.g. Railway), you should set DATABASE_URL to Postgres.
# - The old default sqlite path lived under /tmp which is often ephemeral, causing data loss on deploy.
RAILWAY_ENVIRONMENT = os.getenv("RAILWAY_ENVIRONMENT")
DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip() or None

# Railway deploys must use Postgres (fail fast rather than silently using sqlite and losing data).
if RAILWAY_ENVIRONMENT and not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is required in production (RAILWAY_ENVIRONMENT is set). "
        "Provision Postgres on Railway and set DATABASE_URL."
    )

if not DATABASE_URL:
    # Local/dev fallback
    DATABASE_URL = "sqlite:///./clawstreetbots.db"

# Railway uses postgres://, SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

IS_PROD = bool(RAILWAY_ENVIRONMENT)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
