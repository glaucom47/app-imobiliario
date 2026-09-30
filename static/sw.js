/**
 * Service Worker - Fecho (fecho.pt)
 * Fornece suporte a cache estático e funcionamento 100% offline
 * para motores client-side (Calculadora IMT/Selo e Teleprompter).
 */

const CACHE_NAME = 'fecho-static-v12';
const ASSETS_TO_CACHE = [
  '/',
  '/backoffice',
  '/static/manifest.json',
  '/static/css/design-tokens.css',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/js/api.js',
  '/static/js/calculator.js',
  '/static/js/teleprompter.js',
  '/static/js/audio_recorder.js',
  '/static/img/screen.png',
  '/static/img/logo.png',
  '/static/img/hero/villa_exterior.jpg',
  '/static/img/hero/villa_interior.jpg',
  '/static/img/hero/villa_terrace.jpg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  // Ignora requisições de API para validações online ou métodos que não sejam GET
  if (event.request.method !== 'GET' || event.request.url.includes('/api/')) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request).then((networkResponse) => {
        if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
          return networkResponse;
        }
        const responseToCache = networkResponse.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseToCache);
        });
        return networkResponse;
      }).catch(() => {
        // Fallback inteligente para navegações offline
        if (event.request.mode === 'navigate') {
          if (event.request.url.includes('/backoffice')) {
            return caches.match('/backoffice');
          }
          return caches.match('/');
        }
      });
    })
  );
});
