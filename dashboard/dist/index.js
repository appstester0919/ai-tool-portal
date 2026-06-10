/**
 * AI Tool Portal — v0.1
 * IIFE: calls register() when SDK is available.
 * Full component in v0.4.
 */
(function () {
  var register = window.__HERMES_PLUGINS__?.register;
  if (!register) {
    console.warn("[ai-tool-portal] register not ready, will not load");
    return;
  }

  var SDK = window.__HERMES_PLUGIN_SDK__;

  function PortalComponent() {
    return SDK.React.createElement('div', {
      style: { padding: '24px', fontFamily: 'system-ui, sans-serif' }
    },
      SDK.React.createElement('h2', null, 'AI Tool Portal'),
      SDK.React.createElement('p', { style: { color: '#888' } }, 'v0.1 — scaffold. Full implementation in v0.4.')
    );
  }

  register("ai-tool-portal", PortalComponent);
})();