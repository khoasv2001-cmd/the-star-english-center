// Service worker cho PWA - THE STAR ENGLISH CENTER
// Chien luoc: network-first. App can du lieu/dang nhap tu server nen KHONG
// cache cac trang dong de tranh hien thi noi dung cu hoac loi dang xuat.
const CACHE = 'thestar-v1';
const PRECACHE = [
  '/static/style.css',
  '/static/logo.png',
  '/static/icon-192.png',
  '/static/icon-512.png',
  '/static/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  // Chi xu ly tai nguyen tinh trong /static (network-first, fallback cache).
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }
  // Cac request khac (trang dong): de trinh duyet xu ly binh thuong.
});
