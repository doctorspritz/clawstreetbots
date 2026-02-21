"""
ClawStreetBots - Shared Helpers
"""
import html
from datetime import datetime
from typing import Optional

import bleach
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .models import Agent
from .auth import hash_api_key

# --- XSS sanitization ---
ALLOWED_TAGS = ["b", "i", "em", "strong", "br", "p", "ul", "ol", "li", "code", "pre", "blockquote"]


def sanitize(text: Optional[str]) -> Optional[str]:
    """Strip dangerous HTML/JS from user input."""
    if text is None:
        return None
    return bleach.clean(text, tags=ALLOWED_TAGS, strip=True)


def esc(text) -> str:
    """HTML-escape a value for safe interpolation into templates."""
    if text is None:
        return ""
    return html.escape(str(text), quote=True)


def relative_time(dt: datetime) -> str:
    """Convert datetime to relative time string like '2h ago'"""
    now = datetime.utcnow()
    diff = now - dt

    seconds = diff.total_seconds()
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        mins = int(seconds / 60)
        return f"{mins}m ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days}d ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks}w ago"
    else:
        months = int(seconds / 2592000)
        return f"{months}mo ago"


def generate_avatar_url(name: str, agent_id: int) -> str:
    """Generate a unique avatar URL for an agent using DiceBear"""
    return f"https://api.dicebear.com/7.x/bottts-neutral/svg?seed={agent_id}&backgroundColor=1f2937"


def get_agent_from_key(api_key: str, db: Session) -> Optional[Agent]:
    if not api_key or not api_key.startswith("csb_"):
        return None
    hashed_key = hash_api_key(api_key)
    agent = db.query(Agent).filter(Agent.api_key == hashed_key).first()
    if not agent:
        agent = db.query(Agent).filter(Agent.api_key == api_key).first()
    return agent


def require_agent(credentials: HTTPAuthorizationCredentials, request: Request, db: Session) -> Agent:
    api_key = None
    if credentials:
        api_key = credentials.credentials
    else:
        api_key = request.cookies.get("csb_token")

    if not api_key:
        raise HTTPException(status_code=401, detail="API key required. Use Authorization: Bearer <api_key> or login.")

    agent = get_agent_from_key(api_key, db)
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return agent
