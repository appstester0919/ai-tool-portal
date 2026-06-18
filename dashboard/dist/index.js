/**
 * AI Tool Portal v1.2 — Dashboard Plugin
 *
 * Health dashboard + Start/Stop/Restart for AI tools and long-running services.
 * v1.2: Fixed LOADING bug, icon-only action buttons, status-color card borders.
 *
 * Plain IIFE, no build step. Uses window.__HERMES_PLUGIN_SDK__ for React.
 */
(function () {
  "use strict";

  const SDK = window.__HERMES_PLUGIN_SDK__;
  const register = window.__HERMES_PLUGINS__?.register;
  if (!SDK && !register) {
    console.error("[ai-tool-portal] SDK or register not found, aborting.");
    return;
  }

  const React = window.__HERMES_PLUGIN_SDK__.React;
  const { useState, useEffect, useCallback, useRef, startTransition } = window.__HERMES_PLUGIN_SDK__.hooks;

  // ── Helpers ────────────────────────────────────────────────────

  function fmtUptime(s) {
    if (s == null || s < 0) return "—";
    if (s < 60) return s + "s";
    if (s < 3600) return Math.floor(s / 60) + "m";
    if (s < 86400) return (s / 3600).toFixed(1) + "h";
    return (s / 86400).toFixed(1) + "d";
  }

  function StatusDot({ status }) {
    // Color: green=up, yellow=warning, red=crit (process up but RSS above max),
    //        gray=down/unknown. Larger size + inline glow style for visibility.
    const styles = {
      up:      { backgroundColor: "#22c55e", boxShadow: "0 0 8px rgba(34,197,94,0.8)" },
      warn:    { backgroundColor: "#eab308", boxShadow: "0 0 8px rgba(234,179,8,0.8)" },
      crit:    { backgroundColor: "#ef4444", boxShadow: "0 0 8px rgba(239,68,68,0.9)" },
      warning: { backgroundColor: "#eab308", boxShadow: "0 0 8px rgba(234,179,8,0.8)" },
      down:    { backgroundColor: "#6b7280", boxShadow: "none" },
      unknown: { backgroundColor: "#6b7280", boxShadow: "none" },
    };
    const s = styles[status] || styles.unknown;
    return React.createElement("span", {
      className: "inline-block rounded-full flex-shrink-0",
      style: { width: "14px", height: "14px", ...s },
      title: status,
    });
  }

  // ── Icon-only Action Buttons ───────────────────────────────────

  function ActionButtons({ tool, health, onAction }) {
    const status = health?.status || "down";
    const canStart  = status === "down" || status === "unknown";
    const canStop   = status === "up"   || status === "warning";
    const canRestart = status === "up"  || status === "warning";

    const btn = (label, action, enabled, colorCls, hoverCls, title, sizeCls = "w-9 h-9") =>
      React.createElement("button", {
        key: action,
        onClick: () => onAction(tool.tool_id || tool.id, action),
        disabled: !enabled,
        title,
        className: `${sizeCls} rounded-lg flex items-center justify-center text-sm transition-colors border ${colorCls} ${hoverCls} ${enabled ? "cursor-pointer" : "cursor-not-allowed opacity-30"}`
      }, label);

    return React.createElement("div", {
      className: `flex items-center justify-end gap-0.5 pt-1 mt-1 border-t border-border`
    },
      btn("▶", "start",   canStart,  "text-green-500 border-green-500/20 hover:bg-green-500/20",  "text-green-500/10",  "Start "  + tool.name, "h-7 w-7"),
      btn("■", "stop",    canStop,   "text-red-500   border-red-500/20    hover:bg-red-500/20",    "text-red-500/10",    "Stop "   + tool.name, "h-7 w-7"),
      btn("↻", "restart", canRestart,"text-blue-500  border-blue-500/20   hover:bg-blue-500/20",   "text-blue-500/10",   "Restart "+ tool.name, "h-7 w-7")
    );
  }

  // ── Tool Card ──────────────────────────────────────────────────

  const STATUS_BORDER = {
    up:      "border-green-500/40",
    warning: "border-yellow-500/40",
    down:    "border-gray-600/30",
    unknown: "border-gray-600/30",
  };
  const STATUS_BADGE = {
    up:      "bg-green-500/10 text-green-500 border-green-500/20",
    warning: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
    down:    "bg-gray-500/10 text-gray-400 border-gray-500/20",
    unknown: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  };

  function ToolCard({ tool, health, onAction }) {
    const status = health?.status || "down";
    const rssStatus = health?.rss_status || "unknown";
    // Effective status for the dot:
    //  - down/unknown: just show process status
    //  - up: show rss_status so we surface RAM issues even when service is up
    const effectiveDot = (status === "up" && rssStatus !== "unknown" && rssStatus !== "ok")
      ? rssStatus
      : status;
    const borderCls = STATUS_BORDER[effectiveDot] || STATUS_BORDER.down;
    const badgeCls  = STATUS_BADGE[effectiveDot]  || STATUS_BADGE.down;

    // RSS value colour
    const rssColor = {
      ok: "text-green-500",
      warn: "text-yellow-500",
      crit: "text-red-500 font-semibold",
      unknown: "",
    }[rssStatus] || "";

    return React.createElement("div", {
      className: `flex flex-col gap-1 p-2.5 rounded-lg border bg-card text-card-foreground shadow-sm hover:border-primary/30 transition-colors ${borderCls}`
    },
      // Row 1: icon + name (left) | status dot + badge (right)
      React.createElement("div", { className: "flex items-center justify-between gap-2" },
        React.createElement("div", { className: "flex items-center gap-1.5 min-w-0 flex-1" },
          React.createElement("span", { className: "text-sm flex-shrink-0" }, tool.icon || "⚙️"),
          React.createElement("span", { className: "font-semibold text-[13px] leading-tight truncate" }, tool.name)
        ),
        React.createElement("div", { className: "flex items-center gap-1 flex-shrink-0" },
          React.createElement(StatusDot, { status: effectiveDot }),
          React.createElement("span", {
            className: `text-[9px] px-1 py-0.5 rounded-full border uppercase tracking-wider font-medium ${badgeCls}`
          }, effectiveDot === "ok" ? "up" : (effectiveDot === "warn" ? "up-hi" : (effectiveDot === "crit" ? "up+ram" : effectiveDot)))
        )
      ),
      // Row 2: meta only (single line, allow wrap)
      React.createElement("div", { className: "flex items-center gap-x-1.5 gap-y-0.5 text-[10px] flex-wrap min-w-0" },
        (function() {
          const portVal = tool.port || tool.default_port;
          const portNode = (() => {
            if (!portVal) {
              return React.createElement("span", { className: "font-mono text-muted-foreground" }, "—");
            }
            const isUp = health?.status === "up" && health?.port_listening && tool.url;
            if (isUp) {
              return React.createElement("a", {
                href: tool.url,
                target: "_blank",
                rel: "noopener noreferrer",
                className: "font-mono text-primary hover:underline cursor-pointer",
                title: `Open ${tool.name} (${tool.url})`
              }, portVal);
            }
            return React.createElement("span", {
              className: "font-mono text-muted-foreground",
              title: "Start the service to open its URL"
            }, portVal);
          })();
          return React.createElement("span", { className: "flex items-center gap-0.5" },
            React.createElement("span", { className: "text-muted-foreground uppercase tracking-wider text-[8px]" }, "p"),
            portNode
          );
        })(),
        React.createElement("span", { className: "flex items-center gap-0.5" },
          React.createElement("span", { className: "text-muted-foreground uppercase tracking-wider text-[8px]" }, "pid"),
          React.createElement("span", { className: `font-mono ${health?.pid ? "" : "text-muted-foreground"}` },
            health?.pid || "—")
        ),
        React.createElement("span", {
          className: "flex items-center gap-0.5",
          title: health?.rss_warn_mb
            ? `Normal < ${health.rss_warn_mb}MB · Warn ≥ ${health.rss_warn_mb}MB · Crit ≥ ${health.rss_max_mb}MB`
            : "No threshold set"
        },
          React.createElement("span", { className: "text-muted-foreground uppercase tracking-wider text-[8px]" }, "rss"),
          React.createElement("span", { className: `font-mono ${rssColor || (health?.rss_mb ? "" : "text-muted-foreground")}` },
            health?.rss_mb != null ? health.rss_mb.toFixed(0) + "MB" : "—")
        ),
        React.createElement("span", { className: "flex items-center gap-0.5" },
          React.createElement("span", { className: "text-muted-foreground uppercase tracking-wider text-[8px]" }, "up"),
          React.createElement("span", { className: `font-mono ${health?.uptime_s != null ? "" : "text-muted-foreground"}` },
            fmtUptime(health?.uptime_s))
        )
      ),
      // Row 3: action buttons (right-aligned)
      React.createElement(ActionButtons, { tool, health, onAction })
    );
  }

  // ── Confirm Modal ─────────────────────────────────────────────

  function ConfirmModal({ pendingAction, actionLoading, actionError, onConfirm, onCancel }) {
    if (!pendingAction) return null;

    const { tool, action } = pendingAction;
    const warnings = {
      start:   `Start ${tool?.name}? This may launch a background service.`,
      stop:    `Stop ${tool?.name}? This will interrupt any active workflows or sessions.`,
      restart: `Restart ${tool?.name}? This will briefly disconnect all active sessions.`,
    };
    const iconMap = { start: "▶", stop: "■", restart: "↻" };

    return React.createElement("div", {
      className: "fixed inset-0 z-50 flex items-center justify-center",
      style: { background: "rgba(0,0,0,0.7)" },
      onClick: (e) => { if (e.target === e.currentTarget) onCancel(); }
    },
      React.createElement("div", {
        className: "bg-card border border-border rounded-xl shadow-xl p-6 max-w-sm w-full mx-4"
      },
        React.createElement("div", { className: "flex items-center gap-3 mb-4" },
          React.createElement("span", { className: "text-2xl" }, iconMap[action] || "?"),
          React.createElement("span", { className: "font-semibold text-base" },
            `${action.charAt(0).toUpperCase() + action.slice(1)} ${tool?.name}?`)
        ),
        React.createElement("p", { className: "text-muted-foreground text-sm mb-4" },
          warnings[action] || `${action} ${tool?.name}?`),
        actionError && React.createElement("div", {
          className: "mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-500 font-mono overflow-auto"
        }, `Error: ${actionError}`),
        React.createElement("div", { className: "flex gap-3 justify-end" },
          React.createElement("button", {
            onClick: onCancel,
            disabled: actionLoading,
            className: "px-4 py-2 rounded-lg border border-border text-sm hover:bg-muted transition-colors cursor-pointer"
          }, "Cancel"),
          React.createElement("button", {
            onClick: onConfirm,
            disabled: actionLoading,
            className: `px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              action === "stop" ? "bg-red-500 text-white hover:bg-red-600" :
              action === "start" ? "bg-green-500 text-white hover:bg-green-600" :
              "bg-blue-500 text-white hover:bg-blue-600"
            } ${actionLoading ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`
          }, actionLoading ? "Working..." : "Confirm")
        )
      )
    );
  }

  // ── Main Page ──────────────────────────────────────────────────

  function AiToolPortalPage() {
    const [tools, setTools]       = useState([]);      // health list from API
    const [categories, setCategories] = useState([]);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [error, setError]       = useState(null);
    const [loading, setLoading]   = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    // Action modal state
    const [pendingAction, setPendingAction] = useState(null);
    const [actionLoading, setActionLoading] = useState(false);
    const [actionError, setActionError]     = useState(null);

    // Track if component is still mounted to avoid state updates after unmount
    const mounted = useRef(false);
    useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; });

    // Store fetch function in ref so Refresh button can call it
    const fetchFnRef = useRef(null);

    useEffect(() => {
      if (!mounted.current) return;
      const sdk = window.__HERMES_PLUGIN_SDK__;
      if (!sdk?.fetchJSON) return;

      const doFetch = async () => {
        if (mounted.current) setRefreshing(true);
        try {
          const json = await sdk.fetchJSON("/api/plugins/ai-tool-portal/tools");
          setTools(json.tools || []);
          setCategories(json.categories || []);
          setError(null);
          setLastUpdated(new Date());
        } catch (e) {
          setError(e.message);
        } finally {
          setLoading(false);
          if (mounted.current) setRefreshing(false);
        }
      };

      fetchFnRef.current = doFetch;
      doFetch();

      const id = setInterval(doFetch, 30000);
      return () => clearInterval(id);
    }, []);

    const doAction = useCallback((toolId, action) => {
      const registryTool = tools.find(t => (t.tool_id || t.id) === toolId);
      if (!registryTool) return;
      setPendingAction({ tool: registryTool, action });
      setActionError(null);
      setActionLoading(false);
    }, [tools]);

    const closeModal = useCallback(() => {
      setPendingAction(null);
      setActionError(null);
      setActionLoading(false);
    }, []);

    const confirmAction = useCallback(async () => {
      if (!pendingAction) return;
      const { tool, action } = pendingAction;
      const toolId = tool.tool_id || tool.id;
      setActionLoading(true);
      setActionError(null);
      try {
        const sdk = window.__HERMES_PLUGIN_SDK__;
        const result = await sdk.fetchJSON(
          `/api/plugins/ai-tool-portal/tools/${toolId}/action?action=${action}&confirm=true`,
          { method: "POST" }
        );
        if (result.ok) {
          setTimeout(() => {
            closeModal();
            if (fetchFnRef.current) fetchFnRef.current();
          }, 1500);
        } else {
          setActionError(result.stderr || result.error || `Action failed (exit ${result.exit_code})`);
          setActionLoading(false);
        }
      } catch (e) {
        setActionError(e.message);
        setActionLoading(false);
      }
    }, [pendingAction, closeModal]);

    // Build health map for O(1) lookup
    const healthMap = {};
    tools.forEach(t => { healthMap[t.tool_id || t.id] = t; });

    // "Live" = process actually running (up + warn + crit — all means it's serving)
    const upCount   = tools.filter(t => t.status === "up" || t.status === "warning" || t.status === "warn" || t.status === "crit").length;
    const totalCount = tools.length;
    // True health: any of these is fine; down/unknown = problem
    const healthyCount = tools.filter(t => t.status === "up" || t.status === "warning").length;

    // Group tools by category
    const byCategory = {};
    categories.forEach(c => { byCategory[c.id] = []; });
    tools.forEach(t => {
      const cat = t.category || "other";
      if (!byCategory[cat]) byCategory[cat] = [];
      byCategory[cat].push(t);
    });

    return React.createElement(React.Fragment, null,
      React.createElement("div", { className: "flex flex-col gap-3 p-3" },
        // Header
        React.createElement("div", { className: "flex items-center justify-between" },
          React.createElement("div", { className: "flex items-center gap-2" },
            React.createElement("span", { className: "font-bold text-sm uppercase tracking-wider" }, "AI Tool Portal"),
            React.createElement("span", { className: "text-xs text-muted-foreground" },
              `${upCount}/${totalCount} up`),
            tools.filter(t => t.rss_status === "crit").length > 0 && React.createElement("span", {
              className: "text-xs px-1.5 py-0.5 rounded-full bg-red-500/15 text-red-500 border border-red-500/30 font-medium",
              title: "Processes with RSS above their per-tool rss_max_mb"
            }, `🔴 ${tools.filter(t => t.rss_status === "crit").length} RAM`),
            tools.filter(t => t.rss_status === "warn").length > 0 && React.createElement("span", {
              className: "text-xs px-1.5 py-0.5 rounded-full bg-yellow-500/15 text-yellow-500 border border-yellow-500/30 font-medium",
              title: "Processes with RSS above their per-tool rss_warn_mb"
            }, `🟡 ${tools.filter(t => t.rss_status === "warn").length} RAM`)
          ),
          React.createElement("div", { className: "flex items-center gap-3 text-xs text-muted-foreground" },
            lastUpdated && React.createElement("span", null, "Updated " + lastUpdated.toLocaleTimeString()),
            React.createElement("button", {
              onClick: () => { if (fetchFnRef.current) fetchFnRef.current(); },
              disabled: refreshing,
              className: `px-3 py-1.5 border border-border rounded-md text-xs uppercase tracking-wider transition-colors ${refreshing ? "bg-muted opacity-70 cursor-wait" : "hover:bg-muted cursor-pointer"}`
            }, React.createElement("span", { className: refreshing ? "inline-block animate-spin" : "inline-block" }, "↻"), " ", refreshing ? "Refreshing" : "Refresh")
          )
        ),

        // Error banner
        error && React.createElement("div", {
          className: "p-3 border border-red-500/30 bg-red-500/10 rounded-lg text-xs text-red-500 font-mono"
        }, "Failed to load: " + error),

        // Loading indicator
        loading && React.createElement("div", {
          className: "flex items-center justify-center py-12 text-muted-foreground text-xs uppercase tracking-wider"
        }, "Loading..."),

        // Category sections
        !loading && categories.map(cat => {
          const catTools = byCategory[cat.id] || [];
          if (!catTools.length) return null;
          return React.createElement("div", { key: cat.id, className: "flex flex-col gap-2" },
            React.createElement("div", {
              className: "flex items-center gap-2 text-[11px] uppercase tracking-wider text-muted-foreground font-medium border-b border-border/50 pb-0.5"
            },
              React.createElement("span", null, cat.label || cat.id),
              React.createElement("span", { className: "text-[10px] px-1.5 py-0.5 rounded bg-muted" }, catTools.length)
            ),
            React.createElement("div", { className: "grid grid-cols-2 lg:grid-cols-3 gap-2" },
              catTools.map(t =>
                React.createElement(ToolCard, {
                  key: t.tool_id || t.id,
                  tool: t,
                  health: t,   // each tool object already IS the health result
                  onAction: doAction
                })
              )
            )
          );
        })
      ),

      // Modal
      React.createElement(ConfirmModal, {
        pendingAction,
        actionLoading,
        actionError,
        onConfirm: confirmAction,
        onCancel: closeModal
      })
    );
  }

  register("ai-tool-portal", AiToolPortalPage);
}());