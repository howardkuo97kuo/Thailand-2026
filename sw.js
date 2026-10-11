// Offline support: the page, its libraries and the last-seen data (itinerary, hearts, comments, photos, map tiles)
// are kept on the device, so the site still opens where Chiang Mai reception is poor. Fresh data always wins online.
const V = "cnx-v1";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icon-192.png", "icon-512.png", "icon-180.png"];
const LIMITS = { "cnx-photos": 400, "cnx-tiles": 600 };

self.addEventListener("install", e => {
  e.waitUntil(caches.open(V).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  const keep = new Set([V, "cnx-data", "cnx-lib", "cnx-photos", "cnx-tiles"]);
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => !keep.has(k)).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

async function trim(name) {
  const max = LIMITS[name]; if (!max) return;
  const c = await caches.open(name), ks = await c.keys();
  for (let i = 0; i < ks.length - max; i++) await c.delete(ks[i]);
}
// Network first (so edits by others show up), the saved copy when offline.
async function networkFirst(req, name) {
  const c = await caches.open(name);
  try {
    const r = await fetch(req);
    if (r.ok) c.put(req, r.clone());
    return r;
  } catch (err) {
    const hit = await c.match(req, { ignoreSearch: name === V });
    if (hit) return hit;
    throw err;
  }
}
// Cache first for things that never change at the same URL (library versions, photos, map tiles).
// Images are fetched again with CORS so the cached copy isn't an opaque response (those count as ~7 MB each
// against storage); if a host refuses CORS, the image is just shown and not kept.
async function cacheFirst(req, name) {
  const c = await caches.open(name), hit = await c.match(req.url);
  if (hit) return hit;
  try {
    const r = await fetch(req.url, { mode: "cors", credentials: "omit" });
    if (r.ok) { c.put(req.url, r.clone()); trim(name); return r; }
  } catch (err) { /* fall through */ }
  return fetch(req);
}

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  if ((req.headers.get("accept") || "").includes("text/event-stream")) return;   // live streams stay live
  const u = new URL(req.url);
  if (u.origin === location.origin) { e.respondWith(networkFirst(req, V)); return; }
  if (u.hostname.endsWith("firebasedatabase.app")) { e.respondWith(networkFirst(req, "cnx-data")); return; }
  if (u.hostname === "places.googleapis.com") {
    e.respondWith(u.pathname.endsWith("/media") ? cacheFirst(req, "cnx-photos") : networkFirst(req, "cnx-data"));
    return;
  }
  if (u.hostname.endsWith("tile.openstreetmap.org")) { e.respondWith(cacheFirst(req, "cnx-tiles")); return; }
  if (u.hostname === "cdnjs.cloudflare.com" || u.hostname.endsWith("googleapis.com") || u.hostname.endsWith("gstatic.com")) {
    e.respondWith(cacheFirst(req, "cnx-lib"));
  }
});
