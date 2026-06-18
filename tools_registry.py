"""
AI Tool Portal — tools_registry.py

NOTE: This file is the canonical registry consumed by the top-level
plugin_api.py (Hermes plugin manager). The user-facing dashboard UI
uses dashboard/plugin_api.py which has its own inline TOOLS list —
when adding/modifying tools, update BOTH files in lockstep, or the
dashboard will diverge from this registry.
"""
import os, re, subprocess
from typing import Optional

def get_openclaw_token() -> Optional[str]:
    """Get OpenClaw gateway token."""
    try:
        r = subprocess.run(['openclaw', 'token', 'cat'], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else None
    except:
        return None

def find_port_in_dir(dir_path: str) -> Optional[int]:
    """Scan .sh/.bat files for --port argument."""
    if not os.path.isdir(dir_path):
        return None
    for f in os.listdir(dir_path):
        if f.endswith(('.sh', '.bat')):
            path = os.path.join(dir_path, f)
            try:
                content = open(path, 'r', errors='ignore').read()
                m = re.search(r'--port\s+(\d+)', content)
                if m:
                    return int(m.group(1))
            except:
                pass
    return None

def find_running_comfyui_ports() -> dict:
    """Use ss to find active ComfyUI listening ports."""
    ports = {}
    try:
        r = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            for m in re.finditer(r':(81[0-9]{2})\s', line):
                port = int(m.group(1))
                if port not in ports:
                    ports[port] = "unknown"
    except:
        pass
    return ports

# ── Tool registry ──────────────────────────────────────────────
TOOLS = [
    # ── Gateway / Agent ──────────────────────────────────────
    {
        "id": "openclaw",
        "name": "OpenClaw",
        "category": "gateway",
        "icon": "🦎",
        "default_port": 18789,
        "process_patterns": ["openclaw-gateway", "dist/index.js gateway"],
        "process_comm_filter": "node",
        "version_cmd": ["openclaw", "--version"],
        "version_pattern": r"OpenClaw\s+([0-9.]+)",
        "launch": {"type": "systemd_user", "service": "openclaw-gateway"},
        "stop": {"type": "systemd_user_stop", "service": "openclaw-gateway"},
        "restart": {"type": "systemd_user_restart", "service": "openclaw-gateway"},
    },
    {
        "id": "n8n",
        "name": "n8n",
        "category": "scheduler",
        "icon": "🔧",
        "default_port": 5678,
        "process_patterns": [],
        "docker_image": "n8nio/n8n",
        "version_cmd": ["docker", "ps", "--filter", "ancestor=n8nio/n8n", "--format", "{{.Image}}"],
        "launch": {"type": "docker_start", "container": "n8n-restored"},
        "stop": {"type": "docker_stop", "container": "n8n-restored"},
        "restart": {"type": "docker_restart", "container": "n8n-restored"},
    },
    {
        "id": "hermes_gateway",
        "name": "Hermes Gateway",
        "category": "agent",
        "icon": "🏛️",
        "default_port": 9119,
        "process_patterns": ["hermes_cli.main gateway run", "-m hermes_cli.main gateway"],
        "process_comm_filter": "python",
        "version_cmd": ["hermes", "--version"],
        "version_pattern": r"([0-9.]+)",
        "launch": {"type": "nohup", "cmd": "hermes gateway run", "log": "~/.hermes/logs/hermes_gateway.log"},
        "stop": {"type": "kill_by_pattern", "pattern": "hermes_cli.main gateway run"},
        "restart": {"type": "stop_then_start"},
    },
    {
        "id": "hermes_dashboard",
        "name": "Hermes Dashboard",
        "category": "agent",
        "icon": "📊",
        "default_port": 9119,
        "process_patterns": ["hermes dashboard", "hermes_cli.main dashboard"],
        "process_comm_filter": "python",
        "version_cmd": ["hermes", "--version"],
        "version_pattern": r"([0-9.]+)",
        "launch": {"type": "nohup", "cmd": "hermes dashboard", "log": "~/.hermes/logs/hermes_dashboard.log"},
        "stop": {"type": "kill_by_pattern", "pattern": "hermes_cli.main dashboard"},
        "restart": {"type": "stop_then_start"},
    },
    {
        "id": "prayer_server",
        "name": "Prayer Pipeline v3",
        "category": "pipeline",
        "icon": "🙏",
        "default_port": 5000,
        "process_patterns": ["prayer_server_v3.py", "prayer_server"],
        "process_comm_filter": "python",
        "version_pattern": r"v([0-9.]+)",
        "launch": {
            "type": "nohup",
            "cmd": "python3 $HOME/.hermes/scripts/prayer_server_v3.py",
            "cwd": "$HOME/.hermes/scripts",
            "log": "$HOME/.hermes/logs/prayer_server.log",
            "env": {"FLASK_ENV": "production", "HOME": "/home/appstester0919"},
        },
        "stop": {"type": "kill_by_pattern", "pattern": "prayer_server_v3.py"},
        "restart": {"type": "stop_then_start"},
    },
    # ── ComfyUI instances ───────────────────────────────────
    {
        "id": "comfyui_3d",
        "name": "ComfyUI — 3D",
        "category": "ai_image",
        "icon": "🎨",
        "default_port": 8190,
        "base_dir": "/mnt/d/AI/ComfyUI_3D",
        "process_patterns": ["ComfyUI_3D/main.py", "main.py.*3D"],
        "process_comm_filter": "python",
        "launch": {"type": "shell", "cmd": ["bash", "/mnt/d/AI/ComfyUI_3D/run_3d.sh"]},
        "stop": {"type": "kill_by_pattern", "pattern": "ComfyUI_3D/main.py"},
        "restart": {"type": "stop_then_start"},
    },
    {
        "id": "comfyui_documents",
        "name": "ComfyUI — Documents",
        "category": "ai_image",
        "icon": "📄",
        "default_port": 8188,  # default if not found
        "base_dir": "/mnt/d/AI/ComfyUI_Documents",
        "process_patterns": ["ComfyUI_Documents/main.py", "main.py.*Documents"],
        "process_comm_filter": "python",
        "launch": {"type": "shell", "cmd": ["bash", "/mnt/d/AI/ComfyUI_Documents/run_documents.sh"]},
        "stop": {"type": "kill_by_pattern", "pattern": "ComfyUI_Documents/main.py"},
        "restart": {"type": "stop_then_start"},
    },
    {
        "id": "comfyui_heartmula",
        "name": "ComfyUI — Heartmula",
        "category": "ai_image",
        "icon": "🎵",
        "default_port": 8189,
        "base_dir": "/mnt/d/AI/ComfyUI_Heartmula",
        "process_patterns": ["ComfyUI_Heartmula/main.py", "main.py.*Heartmula"],
        "process_comm_filter": "python",
        "launch": {"type": "shell", "cmd": ["bash", "/mnt/d/AI/ComfyUI_Heartmula/run_audio.sh"]},
        "stop": {"type": "kill_by_pattern", "pattern": "ComfyUI_Heartmula/main.py"},
        "restart": {"type": "stop_then_start"},
    },
    {
        "id": "comfyui_ideogram",
        "name": "ComfyUI — Ideogram",
        "category": "ai_image",
        "icon": "✒️",
        "default_port": 8194,
        "base_dir": "/mnt/d/AI/ComfyUI_Ideogram",
        "process_patterns": ["ComfyUI_Ideogram/main.py", "main.py.*Ideogram"],
        "process_comm_filter": "python",
        "launch": {"type": "shell", "cmd": ["bash", "/mnt/d/AI/ComfyUI_Ideogram/start_ideogram.sh"]},
        "stop": {"type": "kill_by_pattern", "pattern": "ComfyUI_Ideogram/main.py"},
        "restart": {"type": "stop_then_start"},
    },
    {
        "id": "comfyui_krita",
        "name": "ComfyUI — Krita",
        "category": "ai_image",
        "icon": "🖌️",
        "default_port": 8188,
        "base_dir": "/mnt/d/AI/ComfyUI_Krita",
        "process_patterns": ["ComfyUI_Krita/main.py", "main.py.*Krita"],
        "process_comm_filter": "python",
        "launch": {"type": "shell", "cmd": ["bash", "/mnt/d/AI/ComfyUI_Krita/run_krita.sh"]},
        "stop": {"type": "kill_by_pattern", "pattern": "ComfyUI_Krita/main.py"},
        "restart": {"type": "stop_then_start"},
    },
    {
        "id": "comfyui_ltx",
        "name": "ComfyUI — LTX Video",
        "category": "ai_video",
        "icon": "🎬",
        "default_port": 8183,
        "base_dir": "/mnt/d/AI/ComfyUI_LTX",
        "process_patterns": ["ComfyUI_LTX/main.py", "main.py.*LTX"],
        "process_comm_filter": "python",
        "launch": {"type": "shell", "cmd": ["bash", "/mnt/d/AI/ComfyUI_LTX/run_ltxv23.bat"]},
        "stop": {"type": "kill_by_pattern", "pattern": "ComfyUI_LTX/main.py"},
        "restart": {"type": "stop_then_start"},
    },
    {
        "id": "comfyui_mie",
        "name": "ComfyUI — Mie 2026 V8",
        "category": "ai_image",
        "icon": "🤖",
        "default_port": 8188,
        "base_dir": "/mnt/d/AI/ComfyUI_Mie_2026_V8.0_Base",
        "process_patterns": ["ComfyUI_Mie_2026/main.py", "main.py.*Mie"],
        "process_comm_filter": "python",
        "launch": {"type": "shell", "cmd": ["bash", "/mnt/d/AI/ComfyUI_Mie_2026_V8.0_Base/run_mie.sh"]},
        "stop": {"type": "kill_by_pattern", "pattern": "ComfyUI_Mie_2026/main.py"},
        "restart": {"type": "stop_then_start"},
    },
    {
        "id": "comfyui_qwen3tts",
        "name": "ComfyUI — Qwen3-TTS",
        "category": "ai_audio",
        "icon": "🗣️",
        "default_port": 8189,
        "base_dir": "/mnt/d/AI/ComfyUI_Qwen3-TTS",
        "process_patterns": ["ComfyUI_Qwen3-TTS/main.py", "main.py.*Qwen3"],
        "process_comm_filter": "python",
        "launch": {"type": "shell", "cmd": ["bash", "/mnt/d/AI/ComfyUI_Qwen3-TTS/run_qwen_tts.sh"]},
        "stop": {"type": "kill_by_pattern", "pattern": "ComfyUI_Qwen3-TTS/main.py"},
        "restart": {"type": "stop_then_start"},
    },
    {
        "id": "comfyui_standard",
        "name": "ComfyUI — Standard",
        "category": "ai_image",
        "icon": "🖼️",
        "default_port": 8188,
        "base_dir": "/mnt/d/AI/ComfyUI_Standard",
        "process_patterns": ["ComfyUI_Standard/main.py", "main.py.*Standard"],
        "process_comm_filter": "python",
        "launch": {"type": "shell", "cmd": ["bash", "/mnt/d/AI/ComfyUI_Standard/run_standard.bat"]},
        "stop": {"type": "kill_by_pattern", "pattern": "ComfyUI_Standard/main.py"},
        "restart": {"type": "stop_then_start"},
    },
    {
        "id": "comfyui_win_data",
        "name": "ComfyUI — win_data",
        "category": "ai_image",
        "icon": "💾",
        "default_port": 8188,
        "base_dir": "/mnt/d/AI/ComfyUI_win_data",
        "process_patterns": ["ComfyUI_win_data/main.py", "main.py.*win_data"],
        "process_comm_filter": "python",
        "launch": {"type": "shell", "cmd": ["bash", "/mnt/d/AI/ComfyUI_win_data/run_win_data.sh"]},
        "stop": {"type": "kill_by_pattern", "pattern": "ComfyUI_win_data/main.py"},
        "restart": {"type": "stop_then_start"},
    },
    # ── Local LLM ─────────────────────────────────────────────
    {
        "id": "qwen-27b",
        "name": "Qwen — 27B (IQ4_XS)",
        "category": "llm",
        "icon": "🧠",
        "default_port": 8080,
        "process_patterns": ["Qwen3.6-27B-IQ4_XS"],
        "process_comm_filter": "llama",
        "version_cmd": None,
        "launch": {
            "type": "nohup",
            "cmd": "/home/appstester0919/llama.cpp/build/bin/llama-server -m /mnt/d/Models/Qwen3.6-27B-IQ4_XS.gguf --host 0.0.0.0 --port 8080 -ngl 99 -t 8 -c 16384 -b 8 --reasoning off",
            "log": "$HOME/.hermes/logs/qwen-27b.log",
        },
        "stop": {"type": "kill_by_pattern", "pattern": "Qwen3.6-27B-IQ4_XS"},
        "restart": {"type": "stop_then_start"},
    },
    {
        "id": "qwen-35b",
        "name": "Qwen — 35B-A3B (UD-Q3)",
        "category": "llm",
        "icon": "⚡",
        "default_port": 8080,
        "process_patterns": ["Qwen3.6-35B-A3B-UD-Q3_K_XL"],
        "process_comm_filter": "llama",
        "version_cmd": None,
        "launch": {
            "type": "nohup",
            "cmd": "/home/appstester0919/llama.cpp/build/bin/llama-server -m /mnt/d/Models/Qwen3.6-35B-A3B-UD-Q3_K_XL.gguf --host 0.0.0.0 --port 8080 -ngl 99 -t 8 -c 16384 -b 8 --n-cpu-moe 14 --reasoning off",
            "log": "$HOME/.hermes/logs/qwen-35b.log",
        },
        "stop": {"type": "kill_by_pattern", "pattern": "Qwen3.6-35B-A3B-UD-Q3_K_XL"},
        "restart": {"type": "stop_then_start"},
    },
]

CATEGORIES = [
    {"id": "gateway",   "label": "Gateway / Agent",  "icon": "🔐", "tool_ids": ["openclaw", "hermes_gateway", "hermes_dashboard"]},
    {"id": "scheduler", "label": "Schedulers",       "icon": "📅", "tool_ids": ["n8n", "prayer_server"]},
    {"id": "llm",       "label": "Local LLM",        "icon": "🧠", "tool_ids": ["qwen-27b", "qwen-35b"]},
    {"id": "ai_image",  "label": "AI Image",         "icon": "🎨", "tool_ids": ["comfyui_3d", "comfyui_documents", "comfyui_heartmula", "comfyui_ideogram", "comfyui_krita", "comfyui_mie", "comfyui_standard", "comfyui_win_data"]},
    {"id": "ai_video",  "label": "AI Video",         "icon": "🎬", "tool_ids": ["comfyui_ltx"]},
    {"id": "ai_audio",  "label": "AI Audio",          "icon": "🔊", "tool_ids": ["comfyui_qwen3tts"]},
]