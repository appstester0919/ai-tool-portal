"""
AI Tool Portal — v0.1.0
Minimal scaffold: returns empty tools list.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI(title="ai-tool-portal", version="0.1.0")


@app.get("/api/plugins/ai-tool-portal/tools")
async def list_tools():
    return {"tools": [], "categories": []}


@app.get("/api/plugins/ai-tool-portal/tools/{tool_id}/health")
async def tool_health(tool_id: str):
    return {
        "tool_id": tool_id,
        "status": "down",
        "port_listening": False,
        "pid": None,
        "rss_mb": None,
        "uptime_s": None,
        "version": None,
        "checked_at": None,
        "error": "v0.1: not yet implemented",
    }


@app.post("/api/plugins/ai-tool-portal/tools/{tool_id}/action")
async def tool_action(tool_id: str, action: str = "", confirm: bool = False):
    return {
        "ok": False,
        "stdout": "",
        "stderr": "v0.1: actions not yet implemented",
        "exit_code": -1,
        "duration_ms": 0,
        "new_status": None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18792)