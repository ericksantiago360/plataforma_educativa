// Service worker de la app instalable.
// - Nunca guarda la API ni el chat (/api/, /ws/): son datos personales y deben estar siempre al día.
// - Páginas y archivos: primero la red (así cada actualización llega de inmediato) y, sin conexión,
//   la copia guardada; si no hay copia de una página, la pantalla "Sin conexión".
const VERSION = 'campus-v1';
const BASICOS = [
    '/offline.html',
    '/manifest.webmanifest',
    '/icons/icon-192.png',
    '/icons/icon-512.png',
    '/icons/apple-touch-icon.png',
    '/icons/favicon-32.png',
];

self.addEventListener('install', evento => {
    evento.waitUntil(caches.open(VERSION).then(cache => cache.addAll(BASICOS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', evento => {
    // Borra las cachés de versiones anteriores
    evento.waitUntil(
        caches.keys()
            .then(nombres => Promise.all(nombres.filter(n => n !== VERSION).map(n => caches.delete(n))))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', evento => {
    const peticion = evento.request;
    const url = new URL(peticion.url);
    if (peticion.method !== 'GET' || url.origin !== self.location.origin) return;
    if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws/')) return;

    if (peticion.mode === 'navigate') {
        // Sin conexión, el campus no puede funcionar (todo sale de la API): se avisa en lugar de mostrar una página a medias
        evento.respondWith(fetch(peticion).catch(() => caches.match('/offline.html')));
        return;
    }

    evento.respondWith(
        fetch(peticion)
            .then(respuesta => {
                if (respuesta.ok && respuesta.type === 'basic') {
                    const copia = respuesta.clone();
                    caches.open(VERSION).then(cache => cache.put(peticion, copia));
                }
                return respuesta;
            })
            .catch(() => caches.match(peticion))
    );
});
