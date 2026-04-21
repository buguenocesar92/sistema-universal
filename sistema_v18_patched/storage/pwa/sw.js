// sw.js — Service Worker de KraftDo PWA
// Estrategia: network-first con fallback a cache para assets estáticos

const CACHE_NAME = 'kraftdo-v1';
const ASSETS = [
  '/',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
];

// Instalación: cachear assets básicos
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

// Activación: limpiar caches viejos
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// Fetch: network-first, cache fallback
self.addEventListener('fetch', (e) => {
  // No cachear POST, PUT, DELETE
  if (e.request.method !== 'GET') return;

  // No cachear /subir, /api/, /health — siempre frescos
  const url = new URL(e.request.url);
  if (url.pathname.startsWith('/subir') ||
      url.pathname.startsWith('/api/') ||
      url.pathname.startsWith('/health')) {
    return;
  }

  e.respondWith(
    fetch(e.request)
      .then((res) => {
        // Guardar en cache
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(e.request, clone));
        }
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});
