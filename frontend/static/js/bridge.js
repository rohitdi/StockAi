/**
 * Host Application JS Bridge & Multi-Platform Alert Dispatcher
 * Handles bi-directional communication with native iOS, Android, React Native,
 * Flutter, Electron, and Mobile/Desktop Web Browsers with Web Audio and System Notifications.
 */
(function() {
  const originalDocumentTitle = document.title;
  let titleFlashTimer = null;

  window.addEventListener('DOMContentLoaded', () => {
    emitHostEvent('stock-module:ready', {
      timestamp: new Date().toISOString(),
      url: window.location.href
    });

    // Start background alert monitoring
    startAlertMonitor();
  });

  // Listen for host application inbound messages
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

  /**
   * Universal Host App Event Emitter
   */
  window.emitHostEvent = function(eventType, payload = {}) {
    // 1. PostMessage for Iframe Embeds
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({
        type: eventType,
        payload: payload
      }, '*');
    }

    // 2. React Native WebView Bridge
    if (window.ReactNativeWebView && typeof window.ReactNativeWebView.postMessage === 'function') {
      window.ReactNativeWebView.postMessage(JSON.stringify({
        type: eventType,
        payload: payload
      }));
    }

    // 3. iOS WebKit Native Message Handler
    if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.stockBridge) {
      window.webkit.messageHandlers.stockBridge.postMessage({
        type: eventType,
        payload: payload
      });
    }

    // 4. Android Javascript Interface
    if (window.AndroidBridge && typeof window.AndroidBridge.onHostEvent === 'function') {
      window.AndroidBridge.onHostEvent(eventType, JSON.stringify(payload));
    }
  };

  window.closePanel = function() {
    emitHostEvent('stock-module:close', {
      reason: 'user_action'
    });
  };

  /**
   * Request Notification Permission on Mobile / Web Browsers
   */
  window.requestMobileNotificationPermission = async function() {
    if ('Notification' in window) {
      if (Notification.permission === 'default') {
        try {
          const perm = await Notification.requestPermission();
          return perm === 'granted';
        } catch (e) {
          console.warn('[Alerts] Permission request error:', e);
        }
      }
      return Notification.permission === 'granted';
    }
    return false;
  };

  /**
   * Synthesized Web Audio Alert Chime (Crystal Ping)
   */
  function playAlertChime() {
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return;
      const ctx = new AudioContext();
      
      const now = ctx.currentTime;
      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gain = ctx.createGain();

      osc1.type = 'sine';
      osc1.frequency.setValueAtTime(880, now); // A5
      osc1.frequency.exponentialRampToValueAtTime(1760, now + 0.15); // A6

      osc2.type = 'triangle';
      osc2.frequency.setValueAtTime(1320, now); // E6
      osc2.frequency.exponentialRampToValueAtTime(2640, now + 0.18);

      gain.gain.setValueAtTime(0.35, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.45);

      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(ctx.destination);

      osc1.start(now);
      osc2.start(now);
      osc1.stop(now + 0.45);
      osc2.stop(now + 0.45);
    } catch (e) {
      console.warn('[Alerts] Web Audio chime playback error:', e);
    }
  }

  /**
   * Flash Browser Document Title for Background Tabs
   */
  function flashBrowserTabTitle(alertText) {
    if (titleFlashTimer) clearInterval(titleFlashTimer);
    let toggle = true;
    titleFlashTimer = setInterval(() => {
      document.title = toggle ? `🚨 [ALERT] ${alertText}` : originalDocumentTitle;
      toggle = !toggle;
    }, 850);

    const onFocus = () => {
      clearInterval(titleFlashTimer);
      document.title = originalDocumentTitle;
      window.removeEventListener('focus', onFocus);
    };
    window.addEventListener('focus', onFocus);
  }

  /**
   * Dispatch Cross-Tab / Desktop / Mobile System Notification + Audio + Vibration
   */
  window.triggerMobileNotification = function(title, body, data = {}) {
    // 1. Play High-Contrast Audio Cue (Web Audio Synth + Audio Element Fallback)
    playAlertChime();
    try {
      const sound = new Audio('/static/sounds/alert.wav');
      sound.play().catch(() => {});
    } catch (e) {}

    // 2. Trigger Mobile Haptic Vibration
    if ('vibrate' in navigator) {
      try {
        navigator.vibrate([250, 100, 250, 100, 250]);
      } catch (e) {}
    }

    // 3. Native Web / Desktop Notification (especially when tab is in background or document.hidden === true)
    if ('Notification' in window && Notification.permission === 'granted') {
      try {
        const notif = new Notification(title, {
          body: body,
          icon: '/static/img/icon.png',
          tag: 'stock-alert-' + (data.ticker || 'price'),
          renotify: true,
          requireInteraction: true,
          data: data
        });
        notif.onclick = function() {
          window.focus();
          notif.close();
        };
      } catch (e) {
        console.warn('[Alerts] Native desktop notification failed:', e);
      }
    }

    // 4. Flash Tab Title Indicator
    flashBrowserTabTitle(`${data.ticker || 'Stock'} Hit Target!`);

    // 5. Emit Native Mobile Host Event
    emitHostEvent('stock-module:alert-triggered', {
      title: title,
      body: body,
      data: data,
      timestamp: new Date().toISOString()
    });

    // 6. In-App Floating Toast Notification
    showInAppNotificationBanner(title, body);
  };

  /**
   * In-App Banner Display for Visual Alert
   */
  function showInAppNotificationBanner(title, body) {
    let banner = document.getElementById('in-app-alert-banner');
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'in-app-alert-banner';
      banner.style.cssText = `
        position: fixed;
        top: 16px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(15, 23, 42, 0.96);
        border: 2px solid #00E5FF;
        box-shadow: 0 10px 30px rgba(0, 229, 255, 0.35), 0 0 20px rgba(0,0,0,0.8);
        border-radius: 14px;
        padding: 14px 20px;
        z-index: 100000;
        display: flex;
        align-items: center;
        gap: 12px;
        color: #fff;
        max-width: 90vw;
        backdrop-filter: blur(16px);
        animation: modalFadeIn 0.3s ease;
      `;
      document.body.appendChild(banner);
    }

    banner.innerHTML = `
      <div style="font-size: 24px;">🚨</div>
      <div>
        <div style="font-weight: 800; font-size: 13px; color: #00E5FF;">${title}</div>
        <div style="font-size: 12px; color: #cbd5e1; margin-top: 2px;">${body}</div>
      </div>
      <button onclick="this.parentElement.remove()" style="background: none; border: none; color: #94a3b8; font-size: 16px; cursor: pointer; margin-left: 8px;">✕</button>
    `;

    setTimeout(() => {
      if (banner && banner.parentElement) banner.remove();
    }, 6000);
  }

  /**
   * Background Alert Polling Loop
   */
  function startAlertMonitor() {
    async function checkAlerts() {
      try {
        const res = await fetch('/api/alerts/check', { method: 'POST' });
        if (res.ok) {
          const data = await res.json();
          if (data.triggered_alerts && data.triggered_alerts.length > 0) {
            data.triggered_alerts.forEach(alert => {
              window.triggerMobileNotification(
                `⚡ Price Alert Triggered: ${alert.ticker}`,
                alert.message,
                alert
              );
            });
          }
        }
      } catch (e) {}
    }

    // Check every 15 seconds
    setInterval(checkAlerts, 15000);
  }

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
