"""
AI Tool Portal — v0.2
Backend API with health checks for 6 core services.
Full 13-tool support in v0.3.
"""
import subprocess, re, json, sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter

import tools_registry
TOOLS = tools_registry.TOOLS
CATEGORIES = tools_registry.CATEGORIES
get_tool = tools_registry.get_tool

router = APIRouter()

# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def run_cmd(cmd: list[str], timeout_s: int = 10) -> tuple[str, str, int]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", f"timeout after {timeout_s}s", 124


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_proc_by_patterns(patterns: list[str], comm_filter: Optional[str] = None) -> Optional[dict]:
    """Find first matching process. Returns {pid, comm, cmdline} or None."""
    for pat in patterns:
        out, _, rc = run_cmd(["pgrep", "-f", pat])
        if rc != 0:
            continue
        for line in out.strip().split("\n"):
            if not line:
                continue
            try:
                pid = int(line.split()[0])
                # Filter by comm
                comm_path = f"/proc/{pid}/comm"
                try:
                    comm = open(comm_path).read().strip()
                except (IOError, ProcessLookupError):
                    comm = ""
                if comm_filter and comm != comm_filter:
                    continue
                cmdline = open(f"/proc/{pid}/cmdline").read().replace("\x00", " ").strip()
                return {"pid": pid, "comm": comm, "cmdline": cmdline}
            except (IOError, ValueError, IndexError):
                continue
    return None


def get_proc_info(pid: int) -> dict:
    """Read RSS (KB) and uptime (s) from /proc/$pid."""
    info = {"pid": pid, "rss_kb": None, "uptime_s": None}
    try:
        status = open(f"/proc/{pid}/status").read()
        m = re.search(r"VmRSS:\s+(\d+)\s+kB", status)
        if m:
            info["rss_kb"] = int(m.group(1))
        stat = open(f"/proc/{pid}/stat").read().split()
        if len(stat) >= 22:
            starttime = float(stat[22])
            uptime_str = open("/proc/uptime").read().split()[0]
            info["uptime_s"] = round(float(uptime_str) - starttime / 100.0, 1)
    except (IOError, ValueError, IndexError):
        pass
    return info


def port_listening(port: int) -> bool:
    out, _, rc = run_cmd(["ss", "-tln"])
    if rc == 0:
        return any(f":{port}" in line for line in out.split("\n"))
    return False


def parse_version(stdout: str, pattern: str) -> Optional[str]:
    m = re.search(pattern, stdout)
    return m.group(1) if m else None


def get_docker_container(ancestry: str) -> Optional[dict]:
    """Check if docker container with given ancestry is running."""
    out, _, rc = run_cmd(["docker", "ps", "--filter", f"ancestor={ancestry}", "--format", "{{.ID}}"])
    if rc != 0 or not out.strip():
        return None
    cid = out.strip()
    # Get stats
    stats_out, _, _ = run_cmd(["docker", "stats", "--no-stream", "--format", "{{.CPUPerc}}|{{.MemUsage}}", cid])
    if stats_out.strip():
        parts = stats_out.strip().split("|")
        cpu = parts[0].rstrip("%") if len(parts) > 0 else "0"
        mem = parts[1].split("/")[0].strip() if len(parts) > 1 else "0"
        return {"id": cid, "cpu_pct": cpu, "mem": mem}
    return {"id": cid, "cpu_pct": "?", "mem": "?"}


# ─────────────────────────────────────────────────────────────────
# Health check per service type
# ─────────────────────────────────────────────────────────────────

def check_openclaw(tool: dict) -> dict:
    proc = get_proc_by_patterns(tool["process_patterns"], tool.get("process_comm_filter"))
    listening = port_listening(tool["default_port"])
    status = "up" if (proc and listening) else ("warning" if (proc or listening) else "down")
    rss, uptime = None, None
    version = None
    if proc:
        info = get_proc_info(proc["pid"])
        rss = round(info["rss_kb"] / 1024, 1) if info["rss_kb"] else None
        uptime = info["uptime_s"]
    out, _, _ = run_cmd(tool["version_cmd"])
    version = parse_version(out, tool["version_pattern"])
    return {
        "tool_id": tool["id"],
        "name": tool["name"],
        "category": tool["category"],
        "icon": tool["icon"],
        "status": status,
        "port": tool["default_port"],
        "port_listening": listening,
        "pid": proc["pid"] if proc else None,
        "rss_mb": rss,
        "uptime_s": uptime,
        "version": version,
        "checked_at": now_iso(),
    }


def check_hermes_gateway(tool: dict) -> dict:
    proc = get_proc_by_patterns(tool["process_patterns"], tool.get("process_comm_filter"))
    listening = port_listening(tool["default_port"])
    status = "up" if (proc and listening) else ("warning" if (proc or listening) else "down")
    rss, uptime = None, None
    version = None
    if proc:
        info = get_proc_info(proc["pid"])
        rss = round(info["rss_kb"] / 1024, 1) if info["rss_kb"] else None
        uptime = info["uptime_s"]
    out, _, _ = run_cmd(tool["version_cmd"])
    version = parse_version(out, tool["version_pattern"])
    return {
        "tool_id": tool["id"],
        "name": tool["name"],
        "category": tool["category"],
        "icon": tool["icon"],
        "status": status,
        "port": tool["default_port"],
        "port_listening": listening,
        "pid": proc["pid"] if proc else None,
        "rss_mb": rss,
        "uptime_s": uptime,
        "version": version,
        "checked_at": now_iso(),
    }


def check_n8n(tool: dict) -> dict:
    container = get_docker_container(tool["docker_ancestry"])
    listening = port_listening(tool["default_port"])
    if container:
        status = "up" if listening else "warning"
    else:
        status = "down"
    version = None
    out, _, _ = run_cmd(tool["version_cmd"])
    version = parse_version(out, tool["version_pattern"])
    return {
        "tool_id": tool["id"],
        "name": tool["name"],
        "category": tool["category"],
        "icon": tool["icon"],
        "status": status,
        "port": tool["default_port"],
        "port_listening": listening,
        "container_id": container["id"] if container else None,
        "cpu_pct": container.get("cpu_pct") if container else None,
        "mem": container.get("mem") if container else None,
        "version": version,
        "checked_at": now_iso(),
    }


def check_prayer_server(tool: dict) -> dict:
    proc = get_proc_by_patterns(tool["process_patterns"], tool.get("process_comm_filter"))
    listening = port_listening(tool["default_port"])
    status = "up" if (proc and listening) else ("warning" if (proc or listening) else "down")
    rss, uptime = None, None
    if proc:
        info = get_proc_info(proc["pid"])
        rss = round(info["rss_kb"] / 1024, 1) if info["rss_kb"] else None
        uptime = info["uptime_s"]
    return {
        "tool_id": tool["id"],
        "name": tool["name"],
        "category": tool["category"],
        "icon": tool["icon"],
        "status": status,
        "port": tool["default_port"],
        "port_listening": listening,
        "pid": proc["pid"] if proc else None,
        "rss_mb": rss,
        "uptime_s": uptime,
        "checked_at": now_iso(),
    }


CHECKERS = {
    "openclaw": check_openclaw,
    "hermes_gateway": check_hermes_gateway,
    "hermes_dashboard": check_hermes_gateway,
    "n8n": check_n8n,
    "prayer_server": check_prayer_server,
}


# ─────────────────────────────────────────────────────────────────
# API routes
# ─────────────────────────────────────────────────────────────────

@router.get("/tools")
async def all_tools():
    """Return all tools with last-known health (no live probe here)."""
    summaries = []
    for tool in TOOLS:
        checker = CHECKERS.get(tool["id"])
        if checker:
            health = checker(tool)
            summaries.append(health)
        else:
            summaries.append({
                "tool_id": tool["id"],
                "name": tool["name"],
                "category": tool["category"],
                "icon": tool["icon"],
                "status": "unknown",
                "checked_at": now_iso(),
            })
    return {
        "tools": summaries,
        "categories": CATEGORIES,
        "version": "0.2.0",
        "checked_at": now_iso(),
    }


@router.get("/tools/{tool_id}/health")
async def tool_health(tool_id: str):
    """Live health probe for one tool."""
    tool = get_tool(tool_id)
    if not tool:
        return {"error": f"Unknown tool: {tool_id}", "status": "error"}
    checker = CHECKERS.get(tool_id)
    if not checker:
        return {"error": f"No checker for {tool_id}", "status": "error"}
    return checker(tool)


@router.post("/tools/{tool_id}/action")
async def tool_action(tool_id: str, action: str = None, confirm: bool = False):
    """Execute Start/Stop/Restart. Requires confirm=true."""
    if not confirm:
        return {"ok": False, "error": "confirm required", "tool_id": tool_id}
    tool = get_tool(tool_id)
    if not tool:
        return {"ok": False, "error": f"Unknown tool: {tool_id}", "tool_id": tool_id}
    start_cmd = tool.get("start_cmd") or tool.get("launch")
    stop_cmd = tool.get("stop_cmd")
    restart_cmd = tool.get("restart_cmd")
    action_cmd = None
    if action == "start":
        action_cmd = start_cmd
    elif action == "stop":
        action_cmd = stop_cmd
    elif action == "restart":
        action_cmd = restart_cmd
    else:
        return {"ok": False, "error": f"Unknown action: {action}", "tool_id": tool_id}
    if not action_cmd:
        return {"ok": False, "error": f"No action cmd for {action}", "tool_id": tool_id}
    start_time = datetime.now(timezone.utc)
    out, err, rc = run_cmd(action_cmd.split(" ") if isinstance(action_cmd, str) else action_cmd, timeout_s=30)
    duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
    return {
        "ok": rc == 0,
        "stdout": out[:500],
        "stderr": err[:500],
        "exit_code": rc,
        "duration_ms": duration_ms,
        "tool_id": tool_id,
        "action": action,
        "new_status": "unknown",
    }