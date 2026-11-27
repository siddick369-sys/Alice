/**
 * A.L.I.C.E — Service Worker PWA Résilient (Feature 26).
 * Met en cache UNIQUEMENT les ressources statiques publiques de l'interface.
 * Aucun secret, jeton ou réponse /api/* sensible n'est jamais mis en cache ici.
 */

const CACHE_NAME = "alice-pwa-static-v1";
const STATIC_ASSETS = [
  "/",
  "/index.html",
  "/style.css",
  "/app.js",
  "/orb.js",
  "/manifest.json"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  // Ne JAMAIS intercepter ou mettre en cache les appels API / WebSocket / authentification
  if (url.pathname.startsWith("/api/") || event.request.method !== "GET") {
    return;
  }
  event.respondWith(
    fetch(event.request)
      .then((resp) => {
        if (resp && resp.status === 200 && url.origin === self.location.origin) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then((c) => c.put(event.request, clone)).catch(() => {});
        }
        return resp;
      })
      .catch(() => caches.match(event.request))
  );
});
