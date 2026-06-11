# AI Tool Portal

Hermes dashboard plugin for health monitoring + control of AI tools and long-running services.

## Services (14 total)

| Category | Tools |
|---|---|
| Gateways | OpenClaw (18789), Hermes Gateway (9119), Hermes Dashboard (9119) |
| Workflow | n8n (5678, Docker) |
| Scheduler | Prayer Pipeline v3 (5000) |
| AI Image | ComfyUI 3D (8190), Ideogram (8194), Krita (8192), Standard (8188), win_data (8186), Documents (8191) |
| AI Video | ComfyUI LTX (8183) |
| AI Audio | ComfyUI Heartmula (8189), Qwen3-TTS (8189) |

## Features

- **Health monitoring**: up/warning/down status, PID, RSS, uptime, version
- **Start/Stop/Restart**: confirm modal prevents accidents
- **30s auto-refresh** + manual ↻ Refresh button
- **Categorized view**: tools grouped by type (Gateways, AI Image, etc.)

## Actions

Each tool card has 3 buttons:
- **▶ Start**: enabled when status is down/unknown
- **■ Stop**: enabled when status is up/warning
- **↻ Restart**: enabled when status is up/warning

Click any button → confirm modal → Confirm to execute.

## Replacing personal-stack-health

This plugin supersedes `personal-stack-health`. All 5 core services from that plugin are included here, plus 9 ComfyUI instances.

## Tech notes

- Backend: `plugin_api.py` (FastAPI router, self-contained inline registry)
- Frontend: `dist/index.js` (React IIFE, SDK.fetchJSON for API calls)
- Auth: uses SPA session token via `SDK.fetchJSON` (NOT raw fetch)
- `run_cmd()` catches all exceptions to prevent 500 on missing commands
