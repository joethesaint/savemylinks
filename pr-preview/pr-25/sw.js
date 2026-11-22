// SaveMyLinks service worker: makes the app installable and opens it without a connection.
// Served from the app's root (./sw.js) so its scope covers every page.
// Network first for everything: you always get fresh pages and data when online. Pages and
// static files are cached as they load, so the app still opens offline. API answers are
// never cached: your library is only ever what the server says it is.
const CACHE = 'sml-v1';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin || url.pathname.includes('/api/')) return;
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() => caches.match(req, { ignoreSearch: req.mode === 'navigate' })),
  );
});
