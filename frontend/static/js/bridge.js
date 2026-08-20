(function() {
  window.addEventListener('DOMContentLoaded', () => {
    emitHostEvent('stock-module:ready', {
      timestamp: new Date().toISOString(),
      url: window.location.href
    });
  });

  window.addEventListener('message', (event) => {
    const data = event.data;
    if (!data || typeof data !== 'object') return;

    if (data.type === 'stock-module:set-theme') {
      if (data.theme) {
        document.documentElement.setAttribute('data-theme', data.theme);
      }
      if (data.palette) {
        applyCustomPalette(data.palette);
      }
    }
  });

  window.emitHostEvent = function(eventType, payload = {}) {
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({
        type: eventType,
        payload: payload
      }, '*');
    }
  };

  window.closePanel = function() {
    emitHostEvent('stock-module:close', {
      reason: 'user_action'
    });
  };

  function applyCustomPalette(palette) {
    const root = document.documentElement;
    if (palette.bgPrimary) root.style.setProperty('--bg-primary', palette.bgPrimary);
    if (palette.bgCard) root.style.setProperty('--bg-card', palette.bgCard);
    if (palette.accentIndigo) root.style.setProperty('--accent-indigo', palette.accentIndigo);
    if (palette.textPrimary) root.style.setProperty('--text-primary', palette.textPrimary);
  }

  document.addEventListener('htmx:responseError', (evt) => {
    emitHostEvent('stock-module:error', {
      statusCode: evt.detail.xhr.status,
      error: evt.detail.xhr.responseText
    });
  });
})();
