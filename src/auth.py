"""
WallStreetBots - Authentication
"""
import secrets
import hashlib
from datetime import datetime
from typing import Optional
from fastapi import HTTPException, Security, Depends, Request

from .models import Agent

security = HTTPBearer(auto_error=False)


def generate_api_key() -> str:
    """Generate a unique API key"""
    raw = secrets.token_hex(32)
    return f"csb_{raw}"


def generate_claim_code() -> str:
    """Generate a claim code for verification"""
    return f"csb_claim_{secrets.token_hex(8)}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


async def get_current_agent(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: Session = None
) -> Optional[Agent]:
    """Get the current agent from the API key (header or cookie)"""
    api_key = None
    if credentials:
        api_key = credentials.credentials
    else:
        api_key = request.cookies.get("csb_token")
        
    if not api_key or not api_key.startswith("csb_"):
        return None
    
    hashed_key = hash_api_key(api_key)
    agent = db.query(Agent).filter(Agent.api_key == hashed_key).first()
    return agent


async def require_agent(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = None
) -> Agent:
    """Require a valid agent API key (header or cookie)"""
    api_key = None
    if credentials:
        api_key = credentials.credentials
    else:
        api_key = request.cookies.get("csb_token")
        
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    if not api_key.startswith("csb_"):
        raise HTTPException(status_code=401, detail="Invalid API key format")
    
    hashed_key = hash_api_key(api_key)
    agent = db.query(Agent).filter(Agent.api_key == hashed_key).first()
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return agent


async def require_claimed_agent(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = None
) -> Agent:
    """Require a claimed agent"""
    agent = await require_agent(credentials, db)
    
    if not agent.claimed:
        raise HTTPException(
            status_code=403, 
            detail="Agent not claimed. Have your human verify ownership first."
        )
    
    return agent
