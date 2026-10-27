/* Service worker for Fugledashboard Bygland.
   - app shell, config og ferdige datafiler: cache først, oppdateres i bakgrunnen (stale-while-revalidate)
   - MET-varsel: nett først, cache som reserve
   - Kartverket-fliser: cache først med tak på antall
   - WMS-sannhetslag: bare nett
*/
const VERSJON = 'jakt-v4';
const APP = `${VERSJON}-app`;
const FLISER = `${VERSJON}-fliser`;
const MET = `${VERSJON}-met`;
const MAKS_FLISER = 1500;
const SKALL = [
  './', 'index.html', 'manifest.webmanifest', 'icons/icon.svg', 'icons/icon-192.png', 'icons/icon-512.png',
  'fonts/schibsted-grotesk.css', 'fonts/schibsted-grotesk-latin.woff2', 'fonts/schibsted-grotesk-latin-ext.woff2',
  'config/habitat.json', 'config/route.json', 'config/start.json', 'config/steder.json', 'config/kjerner.geojson',
  'data/jaktfelt.geojson', 'data/teiger.geojson', 'data/naboteiger.geojson', 'data/aoi.geojson', 'data/vann.geojson', 'data/bekker.geojson',
  'data/stier.geojson', 'data/myr_n50.geojson', 'data/artskart.geojson', 'data/grid.geojson',
  'data/score_lirype.png', 'data/score_lirype.json', 'data/score_orrfugl.png', 'data/score_orrfugl.json', 'data/score_storfugl.png', 'data/score_storfugl.json',
  'data/dominant.png', 'data/dominant.json', 'data/forecast.json', 'data/sun.json', 'data/turer.geojson', 'data/observasjoner.geojson',
  'https://cdn.jsdelivr.net/npm/maplibre-gl@5.6.0/dist/maplibre-gl.js', 'https://cdn.jsdelivr.net/npm/maplibre-gl@5.6.0/dist/maplibre-gl.css',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(APP).then(c => Promise.allSettled(SKALL.map(u => c.add(u).catch(() => null)))).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => !k.startsWith(VERSJON)).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

async function trimFliser() {
  const c = await caches.open(FLISER); const keys = await c.keys();
  if (keys.length > MAKS_FLISER) for (const k of keys.slice(0, keys.length - MAKS_FLISER)) await c.delete(k);
}
async function staleWhileRevalidate(req) {
  const c = await caches.open(APP); const cached = await c.match(req, { ignoreSearch: false });
  const nett = fetch(req).then(r => { if (r && r.ok) c.put(req, r.clone()); return r; }).catch(() => null);
  return cached || (await nett) || new Response('Frakoblet og ikke i cache', { status: 503 });
}
async function nettForst(req, cacheNavn) {
  const c = await caches.open(cacheNavn);
  try { const r = await fetch(req); if (r && r.ok) c.put(req, r.clone()); return r; }
  catch (e) { const cached = await c.match(req); return cached || new Response(JSON.stringify({ feil: 'frakoblet' }), { status: 503, headers: { 'Content-Type': 'application/json' } }); }
}
async function cacheForst(req, cacheNavn) {
  const c = await caches.open(cacheNavn); const cached = await c.match(req); if (cached) return cached;
  try { const r = await fetch(req); if (r && r.ok) { c.put(req, r.clone()); trimFliser(); } return r; } catch (e) { return new Response('', { status: 504 }); }
}

self.addEventListener('fetch', e => {
  const req = e.request; if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.hostname === 'api.met.no') { e.respondWith(nettForst(req, MET)); return; }
  if (url.hostname === 'cache.kartverket.no') { e.respondWith(cacheForst(req, FLISER)); return; }
  if (url.hostname.endsWith('nibio.no') || url.hostname === 'wms.geonorge.no') return;  // WMS: alltid nett
  if (url.origin === location.origin || url.hostname === 'cdn.jsdelivr.net') { e.respondWith(staleWhileRevalidate(req)); }
});
