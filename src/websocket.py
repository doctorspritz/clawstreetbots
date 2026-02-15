"""
WebSocket manager for real-time feed updates
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, Set, Any
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections and broadcasts"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        async with self._lock:
            self.active_connections.discard(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients.

        Note: Don't hold the manager lock while awaiting network IO.
        """
        async with self._lock:
            connections = list(self.active_connections)

        if not connections:
            return

        data = json.dumps(message, default=self._json_serializer)

        # Send outside lock; do it concurrently so one slow client doesn't delay others.
        results = await asyncio.gather(
            *(connection.send_text(data) for connection in connections),
            return_exceptions=True,
        )

        dead_connections: list[WebSocket] = [
            connection
            for connection, result in zip(connections, results)
            if isinstance(result, Exception)
        ]

        if dead_connections:
            async with self._lock:
                for connection in dead_connections:
                    self.active_connections.discard(connection)
    
    def _json_serializer(self, obj):
        """Handle datetime serialization"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


# Global manager instance
manager = ConnectionManager()


# Event types
class EventType:
    NEW_POST = "new_post"
    POST_VOTE = "post_vote"
    NEW_COMMENT = "new_comment"
    COMMENT_VOTE = "comment_vote"


async def broadcast_new_post(post_data: Dict[str, Any]):
    """Broadcast a new post event"""
    await manager.broadcast({
        "type": EventType.NEW_POST,
        "data": post_data,
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_post_vote(post_id: int, score: int, upvotes: int, downvotes: int):
    """Broadcast a post vote update"""
    await manager.broadcast({
        "type": EventType.POST_VOTE,
        "data": {
            "post_id": post_id,
            "score": score,
            "upvotes": upvotes,
            "downvotes": downvotes
        },
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_new_comment(comment_data: Dict[str, Any]):
    """Broadcast a new comment event"""
    await manager.broadcast({
        "type": EventType.NEW_COMMENT,
        "data": comment_data,
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_comment_vote(
    comment_id: int,
    score: int,
    upvotes: int,
    downvotes: int,
    post_id: int | None = None,
):
    """Broadcast a comment vote update."""
    await manager.broadcast({
        "type": EventType.COMMENT_VOTE,
        "data": {
            "comment_id": comment_id,
            "post_id": post_id,
            "score": score,
            "upvotes": upvotes,
            "downvotes": downvotes,
        },
        "timestamp": datetime.utcnow().isoformat(),
    })
