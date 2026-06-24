const CACHE = 'motogram-v2';
const ASSETS = [
    '/',
    '/passageiro/',
    '/passageiro/login/',
    '/motorista/login/',
    '/motorista/conta/',
];

self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE).then((cache) => cache.addAll(ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (e) => {
    if (e.request.url.includes('/api/')) {
        e.respondWith(
            fetch(e.request).catch(() => caches.match(e.request))
        );
    } else {
        e.respondWith(
            caches.match(e.request).then((r) => r || fetch(e.request)).catch(() => {
                if (e.request.mode === 'navigate') {
                    return caches.match('/') || new Response('Offline', { status: 503 });
                }
                return new Response(null, { status: 503 });
            })
        );
    }
});
