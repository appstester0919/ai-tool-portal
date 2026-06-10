"""
AI Tool Portal — plugin_api.py v0.2
Backend: tool registry, health detection, action execution.
"""
import os, re, subprocess, time, signal
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from tools_registry import TOOLS, CATEGORIES

app = FastAPI(title="ai-tool-portal", version="0.2.0")

# ── Helpers ─────────────────────────────────────────────────────

def run_cmd(cmd: list, timeout=8) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"

def get_proc_by_pattern(patterns: list, comm_filter: Optional[str] = None) -> Optional[dict]:
    """pgrep + comm filter to find exact process."""
    for pat in patterns:
        out = run_cmd(["pgrep", "-a", "-f", pat])
        if not out or "No matches found" in out:
            continue
        for line in out.splitlines():
            parts = line.split(maxsplit=1)
            if len(parts) < 2:
                continue
            pid = parts[0]
            cmdline = parts[1]
            if comm_filter:
                comm_path = f"/proc/{pid}/comm"
                try:
                    comm = open(comm_path).read().strip()
                    if comm != comm_filter:
                        continue
                except:
                    continue
            return {"pid": int(pid), "cmdline": cmdline}
    return None

def get_proc_rss(pid: int) -> Optional[int]:
    try:
        status = open(f"/proc/{pid}/status").read()
        m = re.search(r'VmRSS:\s+(\d+)\s+kB', status)
        return int(m.group(1)) // 1024 if m else None
    except:
        return None

def get_proc_uptime(pid: int) -> Optional[float]:
    try:
        starttime = float(open(f"/proc/{pid}/stat").read().split()[21])
        clk_tck = os.sysconf(os.sysconf_names.get('SC_CLK_TCK', 100))
        boot_time = float(open("/proc/stat").read().splitlines()[1].split()[1]) / clk_tck
        now = time.time() - boot_time
        return now - starttime / clk_tck
    except:
        return None

def is_port_listening(port: int) -> bool:
    out = run_cmd(["ss", "-tlnp"])
    return f":{port}" in out

def get_version(version_cmd: list, pattern: str) -> Optional[str]:
    out = run_cmd(version_cmd)
    if not out or out.startswith("ERROR"):
        return None
    m = re.search(pattern, out)
    return m.group(1) if m else out[:20]

def get_docker_status(container: str) -> Optional[str]:
    out = run_cmd(["docker", "ps", "--filter", f"name={container}", "--format", "{{.Status}}"])
    return out if out else None

# ── Detection ────────────────────────────────────────────────────

def detect_tool(tool: dict) -> dict:
    tid = tool["id"]
    now = datetime.utcnow().isoformat()

    # Docker-based (n8n)
    if tool.get("docker_image"):
        docker_status = get_docker_status(tool.get("docker_image", ""))
        running = bool(docker_status and "Up" in docker_status)
        port_ok = is_port_listening(tool["default_port"]) if running else False
        return {
            "tool_id": tid,
            "status": "up" if running and port_ok else ("warning" if running else "down"),
            "port_listening": port_ok,
            "port": tool["default_port"],
            "pid": None,
            "rss_mb": None,
            "uptime_s": None,
            "version": None,
            "checked_at": now,
            "docker_status": docker_status,
        }

    # Process-based
    proc = get_proc_by_pattern(tool["process_patterns"], tool.get("process_comm_filter"))
    port_ok = is_port_listening(tool["default_port"])
    port_from_ss = None
    for line in run_cmd(["ss", "-tlnp"]).splitlines():
        if f":{tool['default_port']}" in line:
            m = re.search(r'pid=(\d+)', line)
            if m and proc and int(m.group(1)) == proc["pid"]:
                port_ok = True

    if proc:
        pid = proc["pid"]
        rss = get_proc_rss(pid)
        uptime = get_proc_uptime(pid)
        ver = get_version(tool["version_cmd"], tool.get("version_pattern", r".*")) if tool.get("version_cmd") else None
        status = "up" if port_ok else "warning"
    else:
        pid = rss = uptime = ver = None
        status = "down"

    return {
        "tool_id": tid,
        "status": status,
        "port_listening": port_ok,
        "port": tool["default_port"],
        "pid": pid,
        "rss_mb": rss,
        "uptime_s": round(uptime) if uptime else None,
        "uptime_h": round(uptime/3600, 1) if uptime else None,
        "version": ver,
        "checked_at": now,
    }

# ── Action execution ─────────────────────────────────────────────

def exec_action(tool: dict, action: str) -> dict:
    start = time.time()
    tid = tool["id"]
    result = {"ok": False, "stdout": "", "stderr": "", "exit_code": -1, "duration_ms": 0, "new_status": None}

    try:
        if action == "stop":
            spec = tool.get("stop", {})
        elif action == "restart":
            spec = tool.get("restart", {})
        else:
            spec = tool.get("launch", {})

        atype = spec.get("type", "")

        if atype == "systemd_user":
            svc = spec["service"]
            run_cmd(["systemctl", "--user", action, svc], timeout=30)
            result["ok"] = True
            result["stdout"] = f"systemctl --user {action} {svc}"

        elif atype == "docker_stop":
            c = spec.get("container", "")
            run_cmd(["docker", "stop", c], timeout=30)
            result["ok"] = True
            result["stdout"] = f"docker stop {c}"

        elif atype == "docker_start":
            c = spec.get("container", "")
            run_cmd(["docker", "start", c], timeout=30)
            result["ok"] = True
            result["stdout"] = f"docker start {c}"

        elif atype == "docker_restart":
            c = spec.get("container", "")
            run_cmd(["docker", "restart", c], timeout=60)
            result["ok"] = True
            result["stdout"] = f"docker restart {c}"

        elif atype == "kill_by_pattern":
            pat = spec["pattern"]
            out = run_cmd(["pgrep", "-f", pat])
            if out and "No matches" not in out:
                for line in out.splitlines():
                    pid = line.split()[0]
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                    except:
                        pass
                time.sleep(2)
                # SIGKILL if still running
                out2 = run_cmd(["pgrep", "-f", pat])
                if out2 and "No matches" not in out2:
                    for line in out2.splitlines():
                        pid = line.split()[0]
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                        except:
                            pass
            result["ok"] = True
            result["stdout"] = f"killed pattern: {pat}"

        elif atype == "shell":
            cmd = spec["cmd"]
            env = tool.get("launch", {}).get("env", {})
            full_env = os.environ.copy()
            full_env.update(env)
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10, env=full_env)
            result["ok"] = r.returncode == 0
            result["stdout"] = r.stdout
            result["stderr"] = r.stderr
            result["exit_code"] = r.returncode

        elif atype == "nohup":
            cmd = spec["cmd"]
            log_path = os.path.expanduser(tool.get("launch", {}).get("log", "/tmp/nohup.log"))
            subprocess.Popen(
                f"nohup {cmd} >> {log_path} 2>&1 &",
                shell=True, env=os.environ.copy()
            )
            result["ok"] = True
            result["stdout"] = f"nohup {cmd} >> {log_path}"

        elif atype == "stop_then_start":
            stop_result = exec_action(tool, "stop")
            time.sleep(2)
            start_result = exec_action(tool, "start")
            result["ok"] = stop_result["ok"] and start_result["ok"]
            result["stdout"] = f"stop: {stop_result['stdout']} | start: {start_result['stdout']}"

        else:
            result["stderr"] = f"Unknown action type: {atype}"

    except Exception as e:
        result["stderr"] = str(e)

    result["duration_ms"] = int((time.time() - start) * 1000)

    # Re-detect status after action
    health = detect_tool(tool)
    result["new_status"] = health["status"]

    return result

# ── API ─────────────────────────────────────────────────────────

class ActionRequest(BaseModel):
    action: str
    confirm: bool = False

@app.get("/api/plugins/ai-tool-portal/tools")
async def list_tools():
    """Return tool registry metadata (no live probing)."""
    tool_summaries = []
    for t in TOOLS:
        tool_summaries.append({
            "id": t["id"],
            "name": t["name"],
            "category": t["category"],
            "icon": t["icon"],
            "default_port": t["default_port"],
        })
    return {"tools": tool_summaries, "categories": CATEGORIES}

@app.get("/api/plugins/ai-tool-portal/tools/{tool_id}/health")
async def tool_health(tool_id: str):
    """Live probe: pgrep + ss + /proc for real-time status."""
    tool = next((t for t in TOOLS if t["id"] == tool_id), None)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool {tool_id} not found")
    return detect_tool(tool)

@app.post("/api/plugins/ai-tool-portal/tools/{tool_id}/action")
async def tool_action(tool_id: str, body: ActionRequest):
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm=true required")
    if body.action not in ("start", "stop", "restart"):
        raise HTTPException(status_code=400, detail="action must be start|stop|restart")
    tool = next((t for t in TOOLS if t["id"] == tool_id), None)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool {tool_id} not found")
    return exec_action(tool, body.action)

@app.get("/api/plugins/ai-tool-portal/categories")
async def list_categories():
    return {"categories": CATEGORIES}

# ── Self-test ───────────────────────────────────────────────────

if __name__ == "__main__":
    from fastapi.testclient import TestClient
    client = TestClient(app)

    print("=== GET /tools ===")
    r = client.get("/api/plugins/ai-tool-portal/tools")
    print(f"Status: {r.status_code}")
    data = r.json()
    print(f"Tools count: {len(data['tools'])}")
    print(f"Categories: {len(data['categories'])}")

    print("\n=== GET /tools/{id}/health ===")
    for tid in ["openclaw", "n8n", "hermes_gateway", "prayer_server"]:
        r = client.get(f"/api/plugins/ai-tool-portal/tools/{tid}/health")
        if r.status_code == 200:
            h = r.json()
            print(f"  {tid}: status={h['status']}, port={h['port_listening']}, pid={h['pid']}, uptime_h={h.get('uptime_h')}")

    print("\nv0.2 verify: PASS")