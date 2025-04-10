// static/sw.js
self.addEventListener("install", (e) => {
  e.waitUntil(
    caches
      .open("prioritymaster-v1")
      .then((cache) =>
        cache.addAll(["/", "/static/style.css", "/static/script.js"])
      )
  );
});

self.addEventListener("fetch", (e) => {
  e.respondWith(
    caches.match(e.request).then((response) => response || fetch(e.request))
  );
});

self.addEventListener("push", (e) => {
  const data = e.data.json();
  self.registration.showNotification(data.title, {
    body: data.body,
    icon: "/static/icon.png",
  });
});
