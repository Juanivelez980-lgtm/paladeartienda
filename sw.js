// ════════════════════════════════════════════════════════
// sw.js — Service Worker de Paladear Mercado de Sabores
// Versión: 1.2  |  Fix: cacheo de respuestas opacas (JSONP)
// ════════════════════════════════════════════════════════

const CACHE_VERSION = 'paladear-v3';

const SHELL_FILES = [
  '/paladeartienda/',
  '/paladeartienda/index.html',
  '/paladeartienda/assets/android-chrome-192x192.png',
  '/paladeartienda/assets/android-chrome-512x512.png',
  '/paladeartienda/assets/apple-touch-icon.png',
  '/paladeartienda/assets/favicon-32x32.png',
  '/paladeartienda/assets/favicon.ico',
  '/paladeartienda/assets/favicon-16x16.png',
  '/paladeartienda/assets/favicon-48x48.png',
  '/paladeartienda/assets/favicon-96x96.png',
  '/paladeartienda/assets/favicon-128x128.png',
  '/paladeartienda/manifest.json',
  '/paladeartienda/robots.txt',
  '/paladeartienda/sitemap.txt',
  '/paladeartienda/assets/og-image.jpg',
];

// ── INSTALL ─────────────────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_VERSION)
      .then(cache => cache.addAll(SHELL_FILES))
      .catch(err => console.error('[SW] Error cacheando shell:', err))
  );
  self.skipWaiting();
});

// ── ACTIVATE: limpiar caches viejos ────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k !== CACHE_VERSION)
          .map(k => {
            console.log('[SW] Eliminando cache viejo:', k);
            return caches.delete(k);
          })
      )
    )
  );
  self.clients.claim();
});

// ── FETCH: network-first para todo ─────────────────────
//
// Con internet  → sirve datos frescos y actualiza el caché.
// Sin internet  → sirve los últimos datos cacheados.
//
// IMPORTANTE: los datos del Sheet vienen via JSONP (<script>
// cross-origin), lo que produce respuestas "opacas" con
// status=0 en el SW. Por eso cacheamos también response.type
// === 'opaque' y no solo status === 200.
//
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;

  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Cachear respuestas exitosas normales Y respuestas opacas
        // (las opacas son los JSONP de Google Apps Script)
        const cacheable = response && (response.status === 200 || response.type === 'opaque');
        if (cacheable) {
          const clone = response.clone();
          caches.open(CACHE_VERSION)
            .then(cache => cache.put(event.request, clone))
            .catch(() => {});
        }
        return response;
      })
      .catch(() => {
        return caches.match(event.request).then(cached => {
          if (cached) return cached;
          return caches.match('/paladeartienda/index.html');
        });
      })
  );
});

// ── PUSH: placeholder para Fase 2 (OneSignal) ──────────
self.addEventListener('push', event => {
  console.log('[SW] Push recibido (OneSignal no configurado aún)');
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(clients.openWindow('/paladeartienda/'));
});
