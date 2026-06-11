"""
AI Tool Portal — v0.3
Backend API with health checks for 14 tools.
v0.3: fixed n8n detection (port-based), added ComfyUI generic checker.
"""
import subprocess, re, json, sys, time, os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter

# ── Inline tool registry ───────────────────────────────────────────

HOME = Path.home()
DRIVE_AI = Path("/mnt/d/AI")

TOOLS = [
    {"id": "openclaw", "name": "OpenClaw", "category": "gateway", "icon": "Bot",
     "default_port": 18789, "version_cmd": ["openclaw", "--version"],
     "version_pattern": r"OpenClaw\s+([0-9.]+)",
     "process_patterns": ["openclaw-gateway", "dist/index.js gateway --port"],
     "process_comm_filter": "node",
     "rss_warn_mb": 800, "rss_max_mb": 1500,
     "start_cmd": "systemctl --user start openclaw-gateway",
     "stop_cmd": "systemctl --user stop openclaw-gateway",
     "restart_cmd": "systemctl --user restart openclaw-gateway"},
    {"id": "hermes_gateway", "name": "Hermes Gateway", "category": "gateway", "icon": "Gateway",
     "default_port": 9119, "version_cmd": ["hermes", "--version"],
     "version_pattern": r"hermes\s+([0-9.]+)",
     "process_patterns": ["hermes_cli.main gateway"],
     "process_comm_filter": "python",
     "rss_warn_mb": 200, "rss_max_mb": 400,
     "start_cmd": f"cd {HOME}/.hermes/hermes-agent && {HOME}/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main gateway run --replace",
     "stop_cmd": "pkill -f 'hermes_cli.main gateway'",
     "restart_cmd": "pkill -f 'hermes_cli.main gateway' && sleep 2"},
    {"id": "hermes_dashboard", "name": "Hermes Dashboard", "category": "gateway", "icon": "LayoutDashboard",
     "default_port": 9119, "version_cmd": ["hermes", "--version"],
     "version_pattern": r"hermes\s+([0-9.]+)",
     "process_patterns": ["hermes dashboard"],
     "process_comm_filter": "python",
     "rss_warn_mb": 300, "rss_max_mb": 600,
     "start_cmd": "hermes dashboard --port 9119",
     "stop_cmd": "pkill -f 'hermes dashboard'",
     "restart_cmd": "pkill -f 'hermes dashboard' && sleep 2"},
    {"id": "n8n", "name": "n8n", "category": "workflow", "icon": "Workflow",
     "default_port": 5678,
     "version_cmd": ["n8n", "--version"],
     "version_pattern": r"([0-9.]+)",
     "process_patterns": [],
     "rss_warn_mb": 1024, "rss_max_mb": 2048,
     "start_cmd": "cd /mnt/d/Docker && docker compose -f n8n-restored.yml up -d",
     "stop_cmd": "cd /mnt/d/Docker && docker compose -f n8n-restored.yml down",
     "restart_cmd": "cd /mnt/d/Docker && docker compose -f n8n-restored.yml restart"},
    {"id": "prayer_server", "name": "Prayer Pipeline v3", "category": "scheduler", "icon": "Prayer",
     "default_port": 5000, "version_pattern": r"v([0-9.]+)",
     "process_patterns": ["prayer_server_v3"],
     "process_comm_filter": "python",
     "rss_warn_mb": 150, "rss_max_mb": 300,
     "start_cmd": f"cd {HOME}/.hermes/scripts && nohup {HOME}/.hermes/hermes-agent/venv/bin/python prayer_server_v3.py > {HOME}/.hermes/logs/prayer_server.log 2>&1 &",
     "stop_cmd": "pkill -f 'prayer_server_v3'",
     "restart_cmd": "pkill -f 'prayer_server_v3' && sleep 2"},
    {"id": "comfyui_3d", "name": "ComfyUI — 3D", "category": "ai_image", "icon": "Image",
     "dir": str(DRIVE_AI / "ComfyUI_3D"),
     "default_port": 8190, "version_pattern": r"ComfyUI[_\s]([0-9.]+)",
     "process_patterns": ["ComfyUI_3D"],
     "process_comm_filter": "python",
     "rss_warn_mb": 4000, "rss_max_mb": 8000},
    {"id": "comfyui_ideogram", "name": "ComfyUI — Ideogram", "category": "ai_image", "icon": "Image",
     "dir": str(DRIVE_AI / "ComfyUI_Ideogram"),
     "default_port": 8194, "version_pattern": r"ComfyUI[_\s]([0-9.]+)",
     "process_patterns": ["ComfyUI_Ideogram"],
     "process_comm_filter": "python",
     "rss_warn_mb": 4000, "rss_max_mb": 8000},
    {"id": "comfyui_ltx", "name": "ComfyUI — LTX Video", "category": "ai_video", "icon": "Video",
     "dir": str(DRIVE_AI / "ComfyUI_LTX"),
     "default_port": 8183, "version_pattern": r"ComfyUI[_\s]([0-9.]+)",
     "process_patterns": ["ComfyUI_LTX"],
     "process_comm_filter": "python",
     "rss_warn_mb": 6000, "rss_max_mb": 12000},
    {"id": "comfyui_heartmula", "name": "ComfyUI — Heartmula", "category": "ai_audio", "icon": "Music",
     "dir": str(DRIVE_AI / "ComfyUI_Heartmula"),
     "default_port": 8189, "version_pattern": r"ComfyUI[_\s]([0-9.]+)",
     "process_patterns": ["ComfyUI_Heartmula"],
     "process_comm_filter": "python",
     "rss_warn_mb": 4000, "rss_max_mb": 8000},
    {"id": "comfyui_krita", "name": "ComfyUI — Krita", "category": "ai_image", "icon": "Image",
     "dir": str(DRIVE_AI / "ComfyUI_Krita"),
     "default_port": 8192, "version_pattern": r"ComfyUI[_\s]([0-9.]+)",
     "process_patterns": ["ComfyUI_Krita"],
     "process_comm_filter": "python",
     "rss_warn_mb": 4000, "rss_max_mb": 8000},
    {"id": "comfyui_standard", "name": "ComfyUI — Standard", "category": "ai_image", "icon": "Image",
     "dir": str(DRIVE_AI / "ComfyUI_Standard"),
     "default_port": 8188, "version_pattern": r"ComfyUI[_\s]([0-9.]+)",
     "process_patterns": ["ComfyUI_Standard"],
     "process_comm_filter": "python",
     "rss_warn_mb": 4000, "rss_max_mb": 8000},
    {"id": "comfyui_qwen3tts", "name": "ComfyUI — Qwen3-TTS", "category": "ai_audio", "icon": "Music",
     "dir": str(DRIVE_AI / "ComfyUI_Qwen3-TTS"),
     "default_port": 8189, "version_pattern": r"ComfyUI[_\s]([0-9.]+)",
     "process_patterns": ["ComfyUI_Qwen3-TTS"],
     "process_comm_filter": "python",
     "rss_warn_mb": 4000, "rss_max_mb": 8000},
    {"id": "comfyui_win_data", "name": "ComfyUI — win_data", "category": "ai_image", "icon": "Image",
     "dir": str(DRIVE_AI / "ComfyUI_win_data"),
     "default_port": 8186, "version_pattern": r"ComfyUI[_\s]([0-9.]+)",
     "process_patterns": ["ComfyUI_win_data"],
     "rss_warn_mb": 4000, "rss_max_mb": 8000},
    {"id": "comfyui_documents", "name": "ComfyUI — Documents", "category": "ai_image", "icon": "Image",
     "dir": str(DRIVE_AI / "ComfyUI_Documents"),
     "default_port": 8191, "version_pattern": r"ComfyUI[_\s]([0-9.]+)",
     "process_patterns": ["ComfyUI_Documents"],
     "process_comm_filter": "python",
     "rss_warn_mb": 4000, "rss_max_mb": 8000},
]

CATEGORIES = [
    {"id": "gateway", "label": "Gateways", "icon": "Gateway"},
    {"id": "workflow", "label": "Workflow Engines", "icon": "Workflow"},
    {"id": "scheduler", "label": "Schedulers", "icon": "Clock"},
    {"id": "ai_image", "label": "AI Image", "icon": "Image"},
    {"id": "ai_video", "label": "AI Video", "icon": "Video"},
    {"id": "ai_audio", "label": "AI Audio", "icon": "Music"},
]

def get_tool(id: str):
    return next((t for t in TOOLS if t["id"] == id), None)

router = APIRouter()

# ── Helpers ──────────────────────────────────────────────────────

def run_cmd(cmd: list[str], timeout_s: int = 15) -> tuple[str, str, int]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", f"timeout after {timeout_s}s", 124
    except Exception as e:
        return "", str(e), 1


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
    """Read RSS (KB) and uptime (s) from /proc/$pid.
    
    Uptime calculation: /proc/uptime gives system uptime in seconds.
    starttime from /proc/[pid]/stat is in clock ticks since boot.
    Correct formula: uptime - (starttime / CLK_TCK)
    CLK_TCK on Linux is usually 100.
    """
    info = {"pid": pid, "rss_kb": None, "uptime_s": None}
    try:
        status = open(f"/proc/{pid}/status").read()
        m = re.search(r"VmRSS:\s+(\d+)\s+kB", status)
        if m:
            info["rss_kb"] = int(m.group(1))
        
        # Parse stat — comm field (field 2) can contain spaces and parens.
        # Find the last ')' which ends the comm field, then split from there.
        stat_raw = open(f"/proc/{pid}/stat").read()
        last_paren = stat_raw.rfind(")")
        if last_paren == -1:
            raise ValueError("Cannot find ')' in stat")
        # Fields after ')' are: state(1) ppid(2) pgrp(3) session(4) tty(5) tpgid(6)
        # flags(7) minflt(8) cminflt(9) cmajflt(10) utime(11) stime(12)
        # cutime(13) cstime(14) priority(15) nice(16) num_threads(17)
        # itrealvalue(18) starttime(19) vsize(20) rss(21)
        # starttime is field 20 (1-indexed) = index 19 (0-indexed) after ')'
        stat_parts = stat_raw[last_paren+1:].split()
        if len(stat_parts) >= 19:
            starttime_ticks = float(stat_parts[18])   # stat[18] = starttime
            clk_tck = os.sysconf('SC_CLK_TCK')
            if clk_tck <= 0:
                clk_tck = 100  # fallback for WSL where sysconf may return -1
            uptime_str = open("/proc/uptime").read().split()[0]
            info["uptime_s"] = round(float(uptime_str) - starttime_ticks / clk_tck, 1)
    except (IOError, ValueError, IndexError, OSError):
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


def rss_status(rss_mb: Optional[float], warn: Optional[float], maxv: Optional[float]) -> str:
    """Classify actual RSS against per-tool thresholds.

    Returns one of: "unknown" (no thresholds or no reading),
                    "ok"     (within warn),
                    "warn"   (above warn but below max),
                    "crit"   (above max — process likely leaking or model loaded too big).
    Thresholds are set in TOOLS[*].rss_warn_mb / rss_max_mb.
    """
    if rss_mb is None or not warn or not maxv:
        return "unknown"
    if rss_mb >= maxv:
        return "crit"
    if rss_mb >= warn:
        return "warn"
    return "ok"


def get_docker_container(ancestry_or_port: str, by_port: bool = False) -> Optional[dict]:
    """Lookup docker container by ancestry name OR publish port.

    by_port=True: uses docker ps --filter publish=<port>
    by_port=False: uses docker ps --filter ancestor=<image>
    """
    if by_port:
        filter_arg = f"publish={ancestry_or_port}"
    else:
        filter_arg = f"ancestor={ancestry_or_port}"
    out, _, rc = run_cmd(["docker", "ps", "--filter", filter_arg, "--format", "{{.ID}}|{{.Image}}|{{.Names}}"])
    if rc != 0 or not out.strip():
        return None
    line = out.strip().split("\n")[0]
    parts = line.split("|")
    cid = parts[0]
    image = parts[1] if len(parts) > 1 else "?"
    name = parts[2] if len(parts) > 2 else "?"
    stats_out, _, _ = run_cmd(["docker", "stats", "--no-stream", "--format", "{{.CPUPerc}}|{{.MemUsage}}", cid])
    if stats_out.strip():
        sparts = stats_out.strip().split("|")
        cpu = sparts[0].rstrip("%") if len(sparts) > 0 else "0"
        mem = sparts[1].split("/")[0].strip() if len(sparts) > 1 else "0"
        return {"id": cid, "image": image, "name": name, "cpu_pct": cpu, "mem": mem}
    return {"id": cid, "image": image, "name": name, "cpu_pct": "?", "mem": "?"}


# ── Health check functions ─────────────────────────────────────────

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
    if tool.get("version_cmd"):
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
        "rss_status": rss_status(rss, tool.get("rss_warn_mb"), tool.get("rss_max_mb")),
        "rss_warn_mb": tool.get("rss_warn_mb"),
        "rss_max_mb": tool.get("rss_max_mb"),
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
    if tool.get("version_cmd"):
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
        "rss_status": rss_status(rss, tool.get("rss_warn_mb"), tool.get("rss_max_mb")),
        "rss_warn_mb": tool.get("rss_warn_mb"),
        "rss_max_mb": tool.get("rss_max_mb"),
        "uptime_s": uptime,
        "version": version,
        "checked_at": now_iso(),
    }


def check_n8n(tool: dict) -> dict:
    # Use port-based lookup (works for custom image names like n8nio-restored)
    container = get_docker_container(str(tool["default_port"]), by_port=True)
    listening = port_listening(tool["default_port"])
    if container:
        status = "up" if listening else "warning"
    else:
        status = "down"
    version = None
    if tool.get("version_cmd"):
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
        "rss_status": rss_status(rss, tool.get("rss_warn_mb"), tool.get("rss_max_mb")),
        "rss_warn_mb": tool.get("rss_warn_mb"),
        "rss_max_mb": tool.get("rss_max_mb"),
        "uptime_s": uptime,
        "checked_at": now_iso(),
    }


def check_comfyui(tool: dict) -> dict:
    """Generic checker for all ComfyUI instances."""
    proc = get_proc_by_patterns(tool["process_patterns"], tool.get("process_comm_filter"))
    listening = port_listening(tool["default_port"])
    # ComfyUI: process running but port not ready = warning (starting up)
    # both = up, neither = down
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
        "rss_status": rss_status(rss, tool.get("rss_warn_mb"), tool.get("rss_max_mb")),
        "rss_warn_mb": tool.get("rss_warn_mb"),
        "rss_max_mb": tool.get("rss_max_mb"),
        "uptime_s": uptime,
        "checked_at": now_iso(),
    }


CHECKERS = {
    "openclaw": check_openclaw,
    "hermes_gateway": check_hermes_gateway,
    "hermes_dashboard": check_hermes_gateway,
    "n8n": check_n8n,
    "prayer_server": check_prayer_server,
    # ComfyUI instances — all use same generic checker
    "comfyui_3d": check_comfyui,
    "comfyui_ideogram": check_comfyui,
    "comfyui_ltx": check_comfyui,
    "comfyui_heartmula": check_comfyui,
    "comfyui_krita": check_comfyui,
    "comfyui_standard": check_comfyui,
    "comfyui_qwen3tts": check_comfyui,
    "comfyui_win_data": check_comfyui,
    "comfyui_documents": check_comfyui,
}


# ── API routes ───────────────────────────────────────────────────

@router.get("/tools")
async def all_tools():
    """Return all 14 tools with live health checks."""
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
        "version": "0.3.0",
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
        return {"ok": False, "error": f"No {action} cmd for {tool_id}", "tool_id": tool_id}
    start_time = time.time()
    out, err, rc = run_cmd(action_cmd.split(" ") if isinstance(action_cmd, str) else action_cmd, timeout_s=30)
    return {
        "ok": rc == 0,
        "stdout": out[:500],
        "stderr": err[:500],
        "exit_code": rc,
        "duration_ms": int((time.time() - start_time) * 1000),
        "tool_id": tool_id,
        "action": action,
    }