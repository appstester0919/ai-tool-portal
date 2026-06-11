/* eslint-disable */
/**
 * AI Tool Portal v1.1 — Dashboard Plugin
 *
 * Health dashboard + Start/Stop/Restart for AI tools and long-running services.
 * Calls /api/plugins/ai-tool-portal/tools for full tool list + live health.
 * Auto-refresh every 30s.
 *
 * Plain IIFE, no build step. Uses window.__HERMES_PLUGIN_SDK__ for React.
 */
(function () {
  "use strict";

  const SDK = window.__HERMES_PLUGIN_SDK__;
  const register = window.__HERMES_PLUGINS__?.register;
  if (!SDK && !register) {
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

  // ── Action Buttons ─────────────────────────────────────────────

  function ActionButtons({ tool, health, onAction }) {
    const status = health?.status || "down";
    const canStart = status === "down" || status === "unknown";
    const canStop = status === "up" || status === "warning";
    const canRestart = status === "up" || status === "warning";

    return React.createElement("div", { className: "flex items-center gap-1.5 pt-2 border-t border-border mt-2" },
      React.createElement("button", {
        onClick: () => onAction(tool.tool_id || tool.id, "start"),
        disabled: !canStart,
        className: `flex-1 px-2 py-1 rounded text-xs font-medium transition-colors uppercase tracking-wider border ${
          canStart
            ? "bg-green-500/10 text-green-500 border-green-500/20 hover:bg-green-500/20 cursor-pointer"
            : "bg-gray-500/5 text-gray-500 border-gray-500/10 cursor-not-allowed opacity-40"
        }`
      }, "▶ Start"),
      React.createElement("button", {
        onClick: () => onAction(tool.tool_id || tool.id, "stop"),
        disabled: !canStop,
        className: `flex-1 px-2 py-1 rounded text-xs font-medium transition-colors uppercase tracking-wider border ${
          canStop
            ? "bg-red-500/10 text-red-500 border-red-500/20 hover:bg-red-500/20 cursor-pointer"
            : "bg-gray-500/5 text-gray-500 border-gray-500/10 cursor-not-allowed opacity-40"
        }`
      }, "■ Stop"),
      React.createElement("button", {
        onClick: () => onAction(tool.tool_id || tool.id, "restart"),
        disabled: !canRestart,
        className: `flex-1 px-2 py-1 rounded text-xs font-medium transition-colors uppercase tracking-wider border ${
          canRestart
            ? "bg-blue-500/10 text-blue-500 border-blue-500/20 hover:bg-blue-500/20 cursor-pointer"
            : "bg-gray-500/5 text-gray-500 border-gray-500/10 cursor-not-allowed opacity-40"
        }`
      }, "↻ Restart")
    );
  }

  // ── Tool Card ──────────────────────────────────────────────────

  function ToolCard({ tool, health, onAction }) {
    const status = health?.status || "down";

    const statusBadgeCls = {
      up: "bg-green-500/10 text-green-500 border-green-500/20",
      warning: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
      down: "bg-gray-500/10 text-gray-400 border-gray-500/20",
      unknown: "bg-gray-500/10 text-gray-400 border-gray-500/20",
    }[status] || statusBadgeCls.down;

    return React.createElement("div", {
      className: "flex flex-col gap-3 p-4 rounded-xl border bg-card text-card-foreground shadow-sm hover:border-primary/30 transition-colors",
    },
      // Header
      React.createElement("div", { className: "flex items-center justify-between" },
        React.createElement("div", { className: "flex items-center gap-2" },
          React.createElement("span", { className: "text-lg" }, tool.icon || "⚙️"),
          React.createElement("span", { className: "font-semibold text-sm" }, tool.name)
        ),
        React.createElement("span", {
          className: `text-xs px-2 py-0.5 rounded-full border uppercase tracking-wider font-medium ${statusBadgeCls}`
        }, status)
      ),
      // Meta grid
      React.createElement("div", { className: "grid grid-cols-2 gap-x-4 gap-y-1 text-xs" },
        React.createElement("div", { className: "flex flex-col" },
          React.createElement("span", { className: "text-muted-foreground uppercase tracking-wider text-[10px]" }, "Port"),
          React.createElement("span", { className: "font-mono" }, tool.port || tool.default_port)
        ),
        React.createElement("div", { className: "flex flex-col" },
          React.createElement("span", { className: "text-muted-foreground uppercase tracking-wider text-[10px]" }, "PID"),
          React.createElement("span", { className: `font-mono ${health?.pid ? "" : "text-muted-foreground"}` }, health?.pid || "—")
        ),
        React.createElement("div", { className: "flex flex-col" },
          React.createElement("span", { className: "text-muted-foreground uppercase tracking-wider text-[10px]" }, "RSS"),
          React.createElement("span", { className: `font-mono ${health?.rss_mb ? "" : "text-muted-foreground"}` },
            health?.rss_mb != null ? health.rss_mb.toFixed(1) + " MB" : "—")
        ),
        React.createElement("div", { className: "flex flex-col" },
          React.createElement("span", { className: "text-muted-foreground uppercase tracking-wider text-[10px]" }, "Uptime"),
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
      start: `Start ${tool?.name}? This may launch a background service on port ${tool?.port}.`,
      stop: `Stop ${tool?.name}? This will interrupt any active workflows or sessions.`,
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
        // Title
        React.createElement("div", { className: "flex items-center gap-3 mb-4" },
          React.createElement("span", { className: "text-2xl" }, iconMap[action] || "?"),
          React.createElement("span", { className: "font-semibold text-base" },
            `${action.charAt(0).toUpperCase() + action.slice(1)} ${tool?.name}?`)
        ),
        // Warning text
        React.createElement("p", { className: "text-muted-foreground text-sm mb-4" },
          warnings[action] || `${action} ${tool?.name}?`
        ),
        // Port info
        React.createElement("div", { className: "text-xs font-mono text-muted-foreground mb-4" },
          `Port: ${tool?.port}`
        ),
        // Error display
        actionError && React.createElement("div", {
          className: "mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-500 font-mono"
        }, `Error: ${actionError}`),
        // Buttons
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
    const [tools, setTools] = useState([]);
    const [healthMap, setHealthMap] = useState({});
    const [categories, setCategories] = useState([]);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);

    // Action modal state
    const [pendingAction, setPendingAction] = useState(null); // { tool, action }
    const [actionLoading, setActionLoading] = useState(false);
    const [actionError, setActionError] = useState(null);

    const fetchData = useCallback(async () => {
      try {
        const json = await SDK.fetchJSON("/api/plugins/ai-tool-portal/tools");
        setTools(json.tools || []);
        const map = {};
        (json.tools || []).forEach(t => { map[t.tool_id] = t; });
        setHealthMap(map);
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

    // Open action confirmation modal
    const doAction = useCallback((toolId, action) => {
      // tools is the healthMap keys list — each has tool_id (not id)
      const registryTool = tools.find(t => t.tool_id === toolId);
      if (!registryTool) return;
      setPendingAction({ tool: registryTool, action });
      setActionError(null);
      setActionLoading(false);
    }, [tools]);

    // Close modal
    const closeModal = useCallback(() => {
      setPendingAction(null);
      setActionError(null);
      setActionLoading(false);
    }, []);

    // Confirm and execute action
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
          // Success — close modal + refresh after 1.5s
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

    const upCount = tools.filter(t => healthMap[t.tool_id]?.status === "up").length;
    const totalCount = tools.length;

    // Group by category
    const cats = categories.length ? categories : [];
    const byCategory = {};
    cats.forEach(c => { byCategory[c.id] = []; });
    tools.forEach(t => {
      const cat = t.category || "other";
      if (!byCategory[cat]) byCategory[cat] = [];
      byCategory[cat].push(t);
    });

    return React.createElement(React.Fragment, null,
      // Main content
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

        // Error
        error && React.createElement("div", {
          className: "p-3 border border-red-500/30 bg-red-500/10 rounded-lg text-xs text-red-500 font-mono"
        }, "Failed to load: " + error),

        // Loading
        loading && !tools.length && React.createElement("div", {
          className: "flex items-center justify-center py-12 text-muted-foreground text-xs uppercase tracking-wider"
        }, "Loading..."),

        // Categories
        !loading && cats.map(cat => {
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
              catTools.map(t => React.createElement(ToolCard, {
                key: t.tool_id,
                tool: t,
                health: healthMap[t.tool_id],
                onAction: doAction
              }))
            )
          );
        })
      ),

      // Modal overlay
      React.createElement(ConfirmModal, {
        pendingAction,
        actionLoading,
        actionError,
        onConfirm: confirmAction,
        onCancel: closeModal
      })
    );
  }

  // Register the plugin component
  register("ai-tool-portal", AiToolPortalPage);
}());