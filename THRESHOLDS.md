# AI Tool Portal — RAM Thresholds & Adding New Apps

This doc is the **canonical guide** for any future agent (or human) who needs to
add a new AI tool to the dashboard, or retune RAM thresholds for an existing one.

## How RAM monitoring works

The backend (`plugin_api.py`) does the following for every tool that has a PID:

1. Reads `/proc/<pid>/status` → `VmRSS` (Resident Set Size = physical RAM held)
2. Compares actual RSS to two per-tool thresholds set in `TOOLS[*]`:
   - `rss_warn_mb`  — yellow dot, RSS value coloured yellow
   - `rss_max_mb`   — red dot, RSS value coloured red & bold
3. Returns `rss_status` ∈ `ok` | `warn` | `crit` | `unknown`

If a tool has no `rss_warn_mb`/`rss_max_mb` set, `rss_status = "unknown"` and the
UI just shows a neutral gray dot and the raw MB number. (Used for things where
RAM is fine to ignore, e.g. the Hermes CLI shells which all share the parent
python process.)

## Setting thresholds (existing tool)

Open `dashboard/plugin_api.py`, find the tool's entry in `TOOLS = [...]`, and
edit two lines:

```python
{"id": "openclaw", ...
 "rss_warn_mb":  800,    # yellow above this
 "rss_max_mb":  1500,    # red above this
 ...}
```

Then restart the dashboard (`hermes dashboard --skip-build` is enough — the
backend re-imports on each request).

### How to pick the numbers

You need a sense of the **typical idle RSS** and the **peak RSS** during real
workloads. Three methods, in order of preference:

1. **Look at history.** Open the portal, let the tool run through one full
   real workflow, and read the RSS at idle vs peak. Pick `rss_warn_mb` ≈
   `idle × 2` and `rss_max_mb` ≈ `peak × 1.3`.
2. **Ask the upstream docs / release notes.** ComfyUI/SD/etc. typically quote
   "X GB VRAM" — that maps roughly to `rss_max_mb` for the python process.
3. **If unknown, set `rss_warn_mb: 0` / `rss_max_mb: 0` to skip RAM
   monitoring** for that tool until you have data. The UI will show
   "No threshold set" as the RSS tooltip.

### Rule of thumb numbers (already calibrated for the 2026-06 install)

| Tool type              | rss_warn_mb | rss_max_mb | Why                                    |
|------------------------|-------------|------------|----------------------------------------|
| Node.js gateway        | 800         | 1500       | V8 heap, baseline ~300 MB, working set |
| Python CLI daemon      | 150         | 300        | Lightweight, leaks are obvious         |
| Python web dashboard   | 300         | 600        | uvicorn + react assets                 |
| n8n Docker container   | 1024        | 2048       | Workflows + queue cache                |
| ComfyUI (image gen)    | 4000        | 8000       | Model + VAE + intermediate latents     |
| ComfyUI (video gen)    | 6000        | 12000      | Latent frames eat 4-8× more RAM         |
| ComfyUI (audio gen)    | 4000        | 8000       | Like image, smaller pipelines          |

If you install a new model that doubles a ComfyUI's RAM, raise its thresholds
the same way.

## Adding a new tool — 7-step checklist

Edit `dashboard/plugin_api.py` and add a new dict to `TOOLS = [...]`. Template:

```python
{"id": "my_app",                     # unique slug, no spaces
 "name": "My App",                   # display name in card
 "category": "ai_image",             # gateway|workflow|scheduler|ai_image|ai_video|ai_audio (or new — add to CATEGORIES)
 "icon": "Image",                    # emoji or short word
 "default_port": 8500,               # port the service listens on
 "version_cmd": ["myapp", "--version"],  # optional
 "version_pattern": r"v([0-9.]+)",   # regex to extract version
 "process_patterns": ["myapp serve"], # substring used by `pgrep -f` to find PID
 "process_comm_filter": "python",    # required comm name (run `cat /proc/<pid>/comm` to find it)
 "rss_warn_mb": 1000,                # see table above
 "rss_max_mb":  2000,
 "start_cmd": "systemctl --user start myapp",
 "stop_cmd":  "systemctl --user stop myapp",
 "restart_cmd": "systemctl --user restart myapp"
},
```

Then verify, in order:

1. **PID detection works:** run
   `pgrep -f 'myapp serve' -a` and check a single PID comes back. If 0 or
   multiple, refine `process_patterns` and `process_comm_filter`.
2. **Port detection works:** `ss -tln | grep 8500` shows the port listening.
3. **Backend parses:** restart dashboard, open
   `http://localhost:9119/api/plugins/ai-tool-portal/tools` (or call
   `SDK.fetchJSON('/api/plugins/ai-tool-portal/tools')` from devtools) and
   find your tool. Check:
   - `status: "up"` (or "warning" if process up but port not ready)
   - `rss_mb` is a number
   - `rss_status` is `ok` / `warn` / `crit` (or `unknown` if you left
     thresholds blank)
4. **UI shows it:** open `/ai-tool-portal`, find the card, check the StatusDot
   colour matches the status, the action buttons (▶ ■ ↻) work and the confirm
   modal fires.
5. **Start/Stop/Restart actually run:** click ▶, confirm — the tool starts and
   the page refreshes to "up" within a few seconds. Click ■ to stop. Click ↻
   to restart.
6. **Commit & push:**
   ```bash
   cd ~/.hermes/plugins/ai-tool-portal
   git add dashboard/plugin_api.py
   git commit -m "feat: add My App to portal"
   git push origin master
   ```
7. **Memory:** update the AI Tool Portal entry to mention the new tool.

## Adding a new category

If your tool doesn't fit any existing `category`, add it to `CATEGORIES`:

```python
CATEGORIES = [
  {"id": "ai_search", "label": "AI Search", "icon": "Search"},
  ...
]
```

## Status semantics — quick reference

| Field         | Values                          | Meaning                                  |
|---------------|---------------------------------|------------------------------------------|
| `status`      | up / warning / down / unknown   | Process + port state                     |
| `rss_status`  | ok / warn / crit / unknown      | RAM usage against per-tool thresholds    |
| Combined dot  | effective in UI                 | down if down, else rss_status if rss>ok, else status |

So a process that is "up" but with `rss_status: "crit"` shows a **red** dot
and a red border — you'll spot it instantly even while the service is serving
traffic.
