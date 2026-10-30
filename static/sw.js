/**
 * Service Worker - Fecho (fecho.pt)
 * Fornece suporte a cache estático e funcionamento 100% offline
 * para motores client-side (Calculadora IMT/Selo e Teleprompter).
 *
 * Estratégias (v24 - performance):
 *  - HTML/navegação: network-first com fallback offline para a casca em cache;
 *  - JS/CSS: cache-first (ficheiros versionados com ?v=);
 *  - Imagens: stale-while-revalidate em cache próprio limitado (fecho-img-v1);
 *  - /api/ e métodos != GET: nunca passam pela cache.
 */

const CACHE_NAME = 'fecho-static-v30';
const IMG_CACHE = 'fecho-img-v1';
const IMG_CACHE_MAX = 40;

// Pré-cache apenas da casca essencial (imagens hero deixam de ser pré-carregadas: ~4,4 MB poupados)
const ASSETS_TO_CACHE = [
  '/',
  '/app',
  '/backoffice',
  '/static/manifest.json',
  '/static/css/design-tokens.css?v=17',
  '/static/css/style.css?v=17',
  '/static/css/team-meetings.css?v=17',
  '/static/js/app.js?v=17',
  '/static/js/api.js?v=17',
  '/static/js/team_meetings.js?v=17',
  '/static/js/calculator.js?v=17',
  '/static/js/teleprompter.js?v=17',
  '/static/js/audio_recorder.js?v=17',
  '/static/js/market_study.js?v=17',
  '/static/js/subscription.js?v=17',
  '/static/img/screen.png',
  '/static/img/logo.png'
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
          if (key !== CACHE_NAME && key !== IMG_CACHE) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

function trimCache(cacheName, max) {
  caches.open(cacheName).then((cache) => {
    cache.keys().then((keys) => {
      if (keys.length > max) {
        cache.delete(keys[0]).then(() => trimCache(cacheName, max));
      }
    });
  });
}

function isCacheable(response) {
  return response && response.status === 200 && response.type === 'basic';
}

self.addEventListener('fetch', (event) => {
  const request = event.request;
  // Ignora requisições de API para validações online ou métodos que não sejam GET
  if (request.method !== 'GET' || request.url.includes('/api/')) {
    return;
  }

  // 1. Navegações / HTML: network-first para a Landing Page ('/') e stale-while-revalidate para '/app' e '/backoffice'
  if (request.mode === 'navigate') {
    const reqUrl = new URL(request.url);
    if (reqUrl.pathname === '/') {
      event.respondWith(
        fetch(request).then((networkResponse) => {
          if (isCacheable(networkResponse)) {
            const copy = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          }
          return networkResponse;
        }).catch(() => caches.match(request))
      );
      return;
    }
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) => {
        return cache.match(request).then((cached) => {
          const networkFetch = fetch(request).then((networkResponse) => {
            if (isCacheable(networkResponse)) {
              cache.put(request, networkResponse.clone());
            }
            return networkResponse;
          }).catch(() => {
            if (cached) return cached;
            return cache.match(request.url.includes('/backoffice') ? '/backoffice' : '/app');
          });
          return cached || networkFetch;
        });
      })
    );
    return;
  }

  // 2. Imagens: stale-while-revalidate
  if (request.destination === 'image') {
    event.respondWith(
      caches.open(IMG_CACHE).then((cache) => {
        return cache.match(request).then((cached) => {
          const network = fetch(request).then((networkResponse) => {
            if (isCacheable(networkResponse)) {
              cache.put(request, networkResponse.clone());
              trimCache(IMG_CACHE, IMG_CACHE_MAX);
            }
            return networkResponse;
          }).catch(() => cached);
          return cached || network;
        });
      })
    );
    return;
  }

  // 3. JS/CSS e restantes estáticos: cache-first
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(request).then((networkResponse) => {
        if (!isCacheable(networkResponse)) {
          return networkResponse;
        }
        const responseToCache = networkResponse.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(request, responseToCache);
        });
        return networkResponse;
      });
    })
  );
});
