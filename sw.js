// SaveMyLinks service worker: makes the app installable and opens it without a connection.
// Served from the app's root (./sw.js) so its scope covers every page.
//
// Pages: the network, but never more than 1.5 s; then the saved copy. (Plain network-first made a
// share from the phone wait ~10 s on a slow or blocking network before it fell back to the copy it
// already had. Plain cache-first showed the old page once after every update.)
// Styles, scripts and pictures: the saved copy at once, refreshed in the background. sml.css and
// sml.js carry ?v=N, so a changed file is a new address and is fetched fresh.
// API answers are never cached: your library is only ever what the server says it is.
const CACHE = 'sml-v4'; // v4 (27 Nov): drops phones' saved copies from before Import and Export
const PAGE_WAIT_MS = 1500;

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

function keep(req, res) {
  if (res.ok) {
    const copy = res.clone();
    caches.open(CACHE).then((c) => c.put(req, copy));
  }
  return res;
}

function page(req) {
  return new Promise((resolve) => {
    let done = false;
    const finish = (res) => { if (!done && res) { done = true; resolve(res); } };
    const saved = () => caches.match(req, { ignoreSearch: true });
    const timer = setTimeout(() => saved().then(finish), PAGE_WAIT_MS);
    fetch(req)
      .then((res) => { clearTimeout(timer); finish(keep(req, res)); })
      .catch(() => { clearTimeout(timer); saved().then((res) => finish(res || Response.error())); });
  });
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin || url.pathname.includes('/api/')) return;
  if (req.mode === 'navigate') { event.respondWith(page(req)); return; }
  const fresh = fetch(req).then((res) => keep(req, res));
  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) {
        event.waitUntil(fresh.catch(() => {}));
        return cached;
      }
      return fresh;
    }),
  );
});
