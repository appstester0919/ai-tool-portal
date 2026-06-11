/* eslint-disable */
/**
 * AI Tool Portal — Dashboard Plugin
 *
 * Health dashboard for all AI tools and long-running services.
 * Calls /api/plugins/ai-tool-portal/tools for the full tool list + live health.
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

  // ── Tool Card ──────────────────────────────────────────────────

  function ToolCard({ tool, health }) {
    const status = health?.status || "down";
    const isRunning = status === "up" || status === "warning";

    const statusBadgeCls = {
      up: "bg-green-500/10 text-green-500 border-green-500/20",
      warning: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
      down: "bg-gray-500/10 text-gray-400 border-gray-500/20",
      unknown: "bg-gray-500/10 text-gray-400 border-gray-500/20",
    }[status] || statusBadgeCls.down;

    return React.createElement("div", {
      className: `flex flex-col gap-3 p-4 rounded-xl border bg-card text-card-foreground shadow-sm hover:border-primary/30 transition-colors`,
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
          React.createElement("span", { className: "font-mono" }, tool.default_port)
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

    return React.createElement("div", { className: "flex flex-col gap-5 p-5" },
      // Header
      React.createElement("div", { className: "flex items-center justify-between" },
        React.createElement("div", { className: "flex items-center gap-2" },
          React.createElement("span", { className: "font-bold text-sm uppercase tracking-wider" }, "AI Tool Portal"),
          React.createElement("span", { className: "text-xs text-muted-foreground" },
            `${upCount}/${totalCount} up`
          )
        ),
        React.createElement("div", { className: "flex items-center gap-3 text-xs text-muted-foreground" },
          lastUpdated && React.createElement("span", null, "Updated " + lastUpdated.toLocaleTimeString()),
          React.createElement("button", {
            onClick: fetchData,
            className: "px-3 py-1.5 border border-border rounded-md text-xs hover:bg-muted transition-colors uppercase tracking-wider"
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
          React.createElement("div", { className: "flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground font-medium border-b border-border pb-1" },
            React.createElement("span", null, cat.label || cat.id),
            React.createElement("span", { className: "text-[10px] px-1.5 py-0.5 rounded bg-muted" }, catTools.length)
          ),
          React.createElement("div", { className: "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3" },
            catTools.map(t => React.createElement(ToolCard, { key: t.tool_id, tool: t, health: healthMap[t.tool_id] }))
          )
        );
      })
    );
  }

  // Register the plugin component
  register("ai-tool-portal", AiToolPortalPage);
}());
