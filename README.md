# AI Tool Portal

Hermes dashboard plugin for health monitoring + control of AI tools and long-running services.

## Changelog

| Version | Changes |
|---|---|
| v1.2 | n8n detection fixed (port-based, not ancestry); all 9 ComfyUI show down/not unknown; icon-only action buttons; status-color card borders |
| v1.1 | Start/Stop/Restart with confirm modal |
| v1.0 | Initial 14-tool health dashboard |

## Services (17 total)

| Category | Tools |
|---|---|
| Gateways | OpenClaw (18789), Hermes Gateway (9119), Hermes Dashboard (9119) |
| Workflow | n8n (5678, Docker) |
| Scheduler | Prayer Pipeline v3 (5000) |
| Local LLM | Qwen 27B (8080), Qwen 35B-A3B (8080) |
| AI Image | ComfyUI 3D (8190), Documents (8188), Heartmula (8189), Ideogram (8194), Krita (8188), Mie (8188), Standard (8188), win_data (8188) |
| AI Video | ComfyUI LTX (8183) |
| AI Audio | Qwen3-TTS (8189) |

## Features

- **Health monitoring**: up/warning/down status, PID, RSS, uptime, version
- **Start/Stop/Restart**: confirm modal prevents accidents
- **30s auto-refresh** + manual ↻ Refresh button
- **Categorized view**: tools grouped by type (Gateways, AI Image, etc.)

## Xquik Companion Integration

Pair this portal with
[Hermes Tweet](https://github.com/Xquik-dev/hermes-tweet), the native Hermes
Agent plugin for X automation through [Xquik](https://xquik.com). Hermes Tweet
provides structured X search, account, post, trend, monitor, and action tools.
This portal keeps the supporting Hermes gateway and dashboard services visible
during launch, support, or incident workflows.

```bash
hermes plugins install Xquik-dev/hermes-tweet --enable
```

Hermes Tweet is maintained by Xquik-dev, not by this repository. Xquik is an
independent third-party service. Not affiliated with X Corp. "Twitter" and "X"
are trademarks of X Corp.

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
- Frontend: `dashboard/index.html` (standalone dashboard using SDK.fetchJSON)
- Auth: uses SPA session token via `SDK.fetchJSON` (NOT raw fetch)
- `run_cmd()` catches all exceptions to prevent 500 on missing commands
