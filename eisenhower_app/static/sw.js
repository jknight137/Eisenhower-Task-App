// static/sw.js
self.addEventListener("install", (e) => {
  e.waitUntil(
    caches
      .open("prioritymaster-v1")
      .then((cache) =>
        cache.addAll(["/static/css/bootstrap.min.css", "/static/js/main.js"])
      )
  );
});
self.addEventListener("fetch", (e) => {
  e.respondWith(
    caches.match(e.request).then((response) => response || fetch(e.request))
  );
});
