"""
AI Tool Portal — v0.1 scaffold
Returns empty tools list. Full implementation in v0.2+.
"""
from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter()

@router.get("/tools")
async def all_tools():
    """Returns empty tool registry — v0.2 populates with real services."""
    return {
        "tools": [],
        "categories": [],
        "version": "0.1.0",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

@router.get("/tools/{tool_id}/health")
async def tool_health(tool_id: str):
    return {
        "tool_id": tool_id,
        "status": "down",
        "error": "Not implemented in v0.1",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

@router.post("/tools/{tool_id}/action")
async def tool_action(tool_id: str, action: str = None, confirm: bool = False):
    return {
        "ok": False,
        "error": "Not implemented in v0.1",
        "tool_id": tool_id,
    }