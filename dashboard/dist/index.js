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

  const React = SDK.React;
  const { useState, useEffect, useCallback } = SDK.hooks;

  // ── Helpers ────────────────────────────────────────────────────

  function fmtUptime(s) {
    if (s == null || s < 0) return "—";
    if (s < 60) return s + "s";
    if (s < 3600) return Math.floor(s / 60) + "m";
    if (s < 86400) return (s / 3600).toFixed(1) + "h";
    return (s / 86400).toFixed(1) + "d";
  }

  function StatusDot({ status }) {
    const colors = {
      up: "bg-green-500",
      warning: "bg-yellow-500",
      down: "bg-gray-400",
      unknown: "bg-gray-400",
    };
    const cls = colors[status] || colors.unknown;
    return React.createElement("span", { className: `inline-block h-2 w-2 rounded-full ${cls}` });
  }

  // ── Icon-only Action Buttons ───────────────────────────────────

  function ActionButtons({ tool, health, onAction }) {
    const status = health?.status || "down";
    const canStart  = status === "down" || status === "unknown";
    const canStop   = status === "up"   || status === "warning";
    const canRestart = status === "up"  || status === "warning";

    const btn = (label, action, enabled, colorCls, hoverCls, title) =>
      React.createElement("button", {
        key: action,
        onClick: () => onAction(tool.tool_id || tool.id, action),
        disabled: !enabled,
        title,
        className: `w-7 h-7 rounded flex items-center justify-center text-xs transition-colors border ${colorCls} ${hoverCls} ${enabled ? "cursor-pointer" : "cursor-not-allowed opacity-30"}`
      }, label);

    return React.createElement("div", {
      className: "flex items-center gap-1 pt-2 border-t border-border mt-2"
    },
      btn("▶", "start",   canStart,  "text-green-500 border-green-500/20 hover:bg-green-500/20",  "text-green-500/10",  "Start "  + tool.name),
      btn("■", "stop",    canStop,   "text-red-500   border-red-500/20    hover:bg-red-500/20",    "text-red-500/10",    "Stop "   + tool.name),
      btn("↻", "restart", canRestart,"text-blue-500  border-blue-500/20   hover:bg-blue-500/20",   "text-blue-500/10",   "Restart "+ tool.name)
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
    const borderCls = STATUS_BORDER[status] || STATUS_BORDER.down;
    const badgeCls  = STATUS_BADGE[status]  || STATUS_BADGE.down;

    return React.createElement("div", {
      className: `flex flex-col gap-2 p-3 rounded-xl border bg-card text-card-foreground shadow-sm hover:border-primary/30 transition-colors ${borderCls}`
    },
      // Header row
      React.createElement("div", { className: "flex items-center justify-between" },
        React.createElement("div", { className: "flex items-center gap-2" },
          React.createElement("span", { className: "text-base" }, tool.icon || "⚙️"),
          React.createElement("span", { className: "font-semibold text-sm" }, tool.name)
        ),
        React.createElement("span", {
          className: `text-[10px] px-1.5 py-0.5 rounded-full border uppercase tracking-wider font-medium ${badgeCls}`
        }, status)
      ),
      // Meta grid
      React.createElement("div", { className: "grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px]" },
        React.createElement("div", { className: "flex flex-col" },
          React.createElement("span", { className: "text-muted-foreground uppercase tracking-wider text-[9px]" }, "Port"),
          React.createElement("span", { className: "font-mono" }, tool.port || tool.default_port || "—")
        ),
        React.createElement("div", { className: "flex flex-col" },
          React.createElement("span", { className: "text-muted-foreground uppercase tracking-wider text-[9px]" }, "PID"),
          React.createElement("span", { className: `font-mono ${health?.pid ? "" : "text-muted-foreground"}` },
            health?.pid || "—")
        ),
        React.createElement("div", { className: "flex flex-col" },
          React.createElement("span", { className: "text-muted-foreground uppercase tracking-wider text-[9px]" }, "RSS"),
          React.createElement("span", { className: `font-mono ${health?.rss_mb ? "" : "text-muted-foreground"}` },
            health?.rss_mb != null ? health.rss_mb.toFixed(1) + " MB" : "—")
        ),
        React.createElement("div", { className: "flex flex-col" },
          React.createElement("span", { className: "text-muted-foreground uppercase tracking-wider text-[9px]" }, "Uptime"),
          React.createElement("span", { className: `font-mono ${health?.uptime_s != null ? "" : "text-muted-foreground"}` },
            fmtUptime(health?.uptime_s))
        )
      ),
      // Action buttons
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

    // Action modal state
    const [pendingAction, setPendingAction] = useState(null);
    const [actionLoading, setActionLoading] = useState(false);
    const [actionError, setActionError]     = useState(null);

    const fetchData = useCallback(async () => {
      try {
        const json = await SDK.fetchJSON("/api/plugins/ai-tool-portal/tools");
        setTools(json.tools || []);
        setCategories(json.categories || []);
        setError(null);
        setLastUpdated(new Date());
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }, []);

    useEffect(() => {
      fetchData();
      const id = setInterval(fetchData, 30000);
      return () => clearInterval(id);
    }, [fetchData]);

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
        const result = await SDK.fetchJSON(
          `/api/plugins/ai-tool-portal/tools/${toolId}/action?action=${action}&confirm=true`,
          { method: "POST" }
        );
        if (result.ok) {
          setTimeout(() => { closeModal(); fetchData(); }, 1500);
        } else {
          setActionError(result.stderr || result.error || `Action failed (exit ${result.exit_code})`);
          setActionLoading(false);
        }
      } catch (e) {
        setActionError(e.message);
        setActionLoading(false);
      }
    }, [pendingAction, closeModal, fetchData]);

    // Build health map for O(1) lookup
    const healthMap = {};
    tools.forEach(t => { healthMap[t.tool_id || t.id] = t; });

    const upCount   = tools.filter(t => t.status === "up").length;
    const totalCount = tools.length;

    // Group tools by category
    const byCategory = {};
    categories.forEach(c => { byCategory[c.id] = []; });
    tools.forEach(t => {
      const cat = t.category || "other";
      if (!byCategory[cat]) byCategory[cat] = [];
      byCategory[cat].push(t);
    });

    return React.createElement(React.Fragment, null,
      React.createElement("div", { className: "flex flex-col gap-5 p-5" },
        // Header
        React.createElement("div", { className: "flex items-center justify-between" },
          React.createElement("div", { className: "flex items-center gap-2" },
            React.createElement("span", { className: "font-bold text-sm uppercase tracking-wider" }, "AI Tool Portal"),
            React.createElement("span", { className: "text-xs text-muted-foreground" },
              `${upCount}/${totalCount} up`)
          ),
          React.createElement("div", { className: "flex items-center gap-3 text-xs text-muted-foreground" },
            lastUpdated && React.createElement("span", null, "Updated " + lastUpdated.toLocaleTimeString()),
            React.createElement("button", {
              onClick: fetchData,
              className: "px-3 py-1.5 border border-border rounded-md text-xs hover:bg-muted transition-colors uppercase tracking-wider cursor-pointer"
            }, "↻ Refresh")
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
          return React.createElement("div", { key: cat.id, className: "flex flex-col gap-3" },
            React.createElement("div", {
              className: "flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground font-medium border-b border-border pb-1"
            },
              React.createElement("span", null, cat.label || cat.id),
              React.createElement("span", { className: "text-[10px] px-1.5 py-0.5 rounded bg-muted" }, catTools.length)
            ),
            React.createElement("div", { className: "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3" },
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