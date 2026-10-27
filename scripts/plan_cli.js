#!/usr/bin/env node
/* Kjør ruteplanleggeren fra index.html på kommandolinjen, uten nettleser.

   node scripts/plan_cli.js 2026-10-22                 # standarddagene fra config/route.json (storfugl, lirype, orrfugl)
   node scripts/plan_cli.js 2026-10-22 --arter lirype,orrfugl --form normal --timer 7
   node scripts/plan_cli.js 2026-10-22 --tekst         # kort tekst i stedet for JSON

   Bruker samme funksjoner som nettsiden (hentet ut av index.html), samme grid, konfig, observasjonsdatabase
   og værvarsel (MET live, ellers data/forecast.json). Skriver per dag: opplegg og biler, valgt og forkastet retning
   med tall, drag med vind ved dragenes høyde, felt, og hvilke observasjoner som påvirker dagens felt.
   Brukes av /briefing. */
'use strict';
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8').replace(/\r\n/g, '\n');  // the working copy may be CRLF
const script = html.match(/<script>([\s\S]*?)<\/script>/g).pop().replace(/<\/?script>/g, '');

function grab(name) {
  const i = script.indexOf(`function ${name}(`); if (i < 0) throw new Error(`fant ikke ${name}`);
  const lineEnd = script.indexOf('\n', i); const first = script.slice(i, lineEnd);
  const opens = (first.match(/{/g) || []).length, closes = (first.match(/}/g) || []).length;
  if (first.trimEnd().endsWith('}') && opens === closes) return first + '\n';
  const j = script.indexOf('\n}\n', i); return script.slice(i, j + 3);
}
const NAMES = ['toXY', 'toLL', 'pip', 'kjerneFaktor', 'brukKjerner', 'byggGraf', 'dijkstra', 'stiTil', 'naermesteNode', 'nodesWithin', 'scoreAv', 'rotasjon', 'finnFelter', 'kmeans', 'lagFelt', 'rettLinje', 'sveipLinjer',
  'overlappProsent', 'chaikin', 'offsetLinje', 'retningGrader', 'vinkelDiff', 'planleggDag', 'kompass', 'iHoydesone', 'obsItems', 'obsVekt', 'distTilRing', 'obsBonusXY',
  'motvindAndel', 'retningScore', 'reverserRute', 'lokal', 'timerForDag', 'vaerStat', 'isoDate'];
const consts = [/const PROJ = [^\n]*\n/, /const OSLO = [^\n]*\n/].map(re => { const m = script.match(re); if (!m) throw new Error(`fant ikke konstant ${re}`); return m[0]; }).join('');

const args = process.argv.slice(2); const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const dato0 = args.find(a => /^\d{4}-\d{2}-\d{2}$/.test(a)) || new Date().toISOString().slice(0, 10);
const route = JSON.parse(fs.readFileSync(path.join(ROOT, 'config/route.json'), 'utf8'));
const habitat = JSON.parse(fs.readFileSync(path.join(ROOT, 'config/habitat.json'), 'utf8'));
const steder = JSON.parse(fs.readFileSync(path.join(ROOT, 'config/steder.json'), 'utf8')).steder;
const startpunkter = JSON.parse(fs.readFileSync(path.join(ROOT, 'config/start.json'), 'utf8')).startpunkter;
const obs = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/observasjoner.geojson'), 'utf8'));
const kjerner = JSON.parse(fs.readFileSync(path.join(ROOT, 'config/kjerner.geojson'), 'utf8'));
const grid = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/grid.geojson'), 'utf8'));
const arter = (flag('--arter', null) || (route.standard_dager && route.standard_dager.arter.join(',')) || 'storfugl,lirype,orrfugl').split(',');
const o = { dato: dato0, dager: arter.length, form: flag('--form', 'normal'), start_tid: flag('--tid', '08:00'), timer: +flag('--timer', 7), arter, egen: null, sloyfe: false };

const ctx = `const ARTER = ['lirype','orrfugl','storfugl']; const ART_NAVN = { lirype: 'Rype', orrfugl: 'Orrfugl', storfugl: 'Storfugl', blandet: 'Blandet' };
const fmt = { int: n => String(Math.round(n)), dec: n => new Intl.NumberFormat('nb-NO', { maximumFractionDigits: 1 }).format(n) }; const scoreKey = a => 'sk_' + a;
let HABITAT = __habitat; let PLAN_DATO = null; let OBS_CACHE = null; let LOGG = []; const CFG = { route: __route, obs: __obs, habitat: __habitat, kjerner: __kjerner }; const VAER = { punkter: {} };
${consts}${NAMES.map(grab).join('\n')}
return { byggGraf, brukKjerner, kjerneFaktor, planleggDag, obsItems, obsBonusXY, obsVekt, motvindAndel, retningScore, reverserRute, timerForDag, vaerStat, kompass, isoDate, toXY, VAER, setPlanDato: (d, c) => { PLAN_DATO = d; OBS_CACHE = c; } };`;
const M = new Function('__habitat', '__route', '__obs', '__kjerner', ctx)(habitat, route, obs, kjerner);

async function hentVaer() {
  const pts = route.vaer.punkter; let kilde = 'MET live';
  for (const p of pts) {
    try {
      const r = await fetch(`https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=${p.lat.toFixed(4)}&lon=${p.lon.toFixed(4)}&altitude=${p.hoyde_moh}`, { headers: { 'User-Agent': 'jakt-bygland/0.1 (+https://github.com/kskjevrak/jakt)' } });
      if (!r.ok) throw new Error(r.status); M.VAER.punkter[p.id] = { data: await r.json() };
    } catch (e) { kilde = 'data/forecast.json'; }
  }
  if (kilde !== 'MET live') { const fb = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/forecast.json'), 'utf8')); for (const p of pts) if (!M.VAER.punkter[p.id] && fb.punkter[p.id]) M.VAER.punkter[p.id] = { data: fb.punkter[p.id].data }; }
  return kilde;
}
const punkt = id => { const s = steder.find(x => x.id === id); if (s) return { id, navn: s.navn, lat: s.lat, lon: s.lon }; const p = startpunkter.find(x => x.id === id); return p ? { id, navn: p.navn, lat: p.lat, lon: p.lon } : null; };
const vindFn = (dato, h0) => { const pts = route.vaer.punkter; const cache = {}; return h => { let best = pts[0]; for (const p of pts) if (Math.abs(p.hoyde_moh - h) < Math.abs(best.hoyde_moh - h)) best = p; if (!(best.id in cache)) { const st = M.vaerStat(M.timerForDag(best.id, dato, h0, h0 + 3)); cache[best.id] = st ? { fra: st.fra, ms: st.typisk, hoyde: best.hoyde_moh, navn: best.navn } : null; } return cache[best.id]; }; };
const addDays = (iso, n) => { const d = new Date(iso + 'T12:00:00'); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };

(async () => {
  const kilde = await hentVaer();
  M.brukKjerner(grid);  // kjerner from local knowledge: kb_<art> on the cells, positive lifts and negative pulls, as in the web page
  const graf = M.byggGraf(grid, route);
  const middel = {}; for (const a of ['lirype', 'orrfugl', 'storfugl']) { let s = 0, n = 0; for (const nd of graf.nodes) { const v = nd.p['sc_' + a]; if (v != null && v >= 0) { s += v; n++; } } middel[a] = s / n; }
  const items = M.obsItems(); const dager = {}; const ut = { dato: dato0, vaerkilde: kilde, form: o.form, timer: o.timer, kjerner: (kjerner.features || []).map(f => ({ navn: f.properties.navn, faktor: M.kjerneFaktor(f.properties, habitat.kjerner), arter: f.properties.arter && f.properties.arter.length ? f.properties.arter : 'alle', notat: f.properties.notat })), dager: [] };
  const toBiler = route.standard_per_art.to_biler_over_m || 2000;
  for (let d = 1; d <= arter.length; d++) {
    const art = arter[d - 1]; const std = route.standard_per_art[art] || route.standard_per_art.blandet; const dato = addDays(dato0, d - 1); const h0 = +o.start_tid.slice(0, 2);
    const start = std.start, slutt = std.slutt === 'samme' ? std.start : std.slutt; const gjennomgang = slutt !== start; const vind = vindFn(dato, h0);
    M.setPlanDato(dato, items);
    const kjor = (s, e) => { const r = M.planleggDag(d, { ...o, sloyfe: !!std.sloyfe && !gjennomgang }, graf, dager, route, steder, punkt(s), gjennomgang ? punkt(e) : null, vind, middel); r.plan = { start: s, slutt: e, gjennomgang }; return r; };
    const A = kjor(start, slutt); let B = null;
    if (gjennomgang) B = kjor(slutt, start); else if (!A.feil) { B = M.reverserRute(A, vind, route); B.plan = A.plan; }
    const kand = [A, B].filter(x => x && !x.feil).map(x => ({ x, s: M.retningScore(x, route) })).sort((p, q) => q.s - p.s);
    const r = kand.length ? kand[0].x : A; dager[d] = r;
    const sammendrag = x => x && !x.feil ? { start: x.plan.start, slutt: x.plan.slutt, km: +(x.stats.m / 1000).toFixed(1), hm: Math.round(x.stats.up), timer: +(x.stats.t / 3600).toFixed(1), over60_pst: Math.round(x.stats.andelOver60 * 100), overlapp_pst: +x.stats.overlapp.toFixed(1), motvind_pst: Math.round((x.stats.motvind || 0) * 100), vind: x.stats.vind, score: +(M.retningScore(x, route)).toFixed(3) } : { feil: x && x.feil };
    // observations near today's fields (within 500 m of a field entry) with today's weight
    const relevante = obs.features.filter(f => f.properties.art === art || (f.properties.art === 'ukjent_honsefugl' && route.observasjoner.ukjent_gjelder.includes(art))).map(f => {
      const vekt = M.obsVekt(f.properties.dato, dato, route.observasjoner.vekt);
      let avstand = null; if (r.maal) { for (const m of r.maal) { const [mx, my] = M.toXY(m.lon, m.lat); let dd; if (f.geometry.type === 'Point') { const [x, y] = M.toXY(f.geometry.coordinates[0], f.geometry.coordinates[1]); dd = Math.hypot(x - mx, y - my); } else { const ring = f.geometry.coordinates[0].map(c => M.toXY(c[0], c[1])); dd = ring.reduce((b, p) => Math.min(b, Math.hypot(p[0] - mx, p[1] - my)), Infinity); } avstand = avstand == null ? dd : Math.min(avstand, dd); } }
      return { id: f.properties.id, art: f.properties.art, type: f.properties.type, dato: f.properties.dato, antall: f.properties.antall, kilde: f.properties.kilde, notat: f.properties.notat, vekt_i_dag: vekt, avstand_til_naermeste_felt_m: avstand == null ? null : Math.round(avstand) };
    });
    let bonusCeller = 0; if (r.path) for (const p of r.path) { const [x, y] = M.toXY(p[0], p[1]); if (M.obsBonusXY(x, y, art, dato, items) > 0) bonusCeller++; }
    const a0 = punkt(start), b0 = punkt(slutt); let avst = 0; if (a0 && b0) { const [x1, y1] = M.toXY(a0.lon, a0.lat), [x2, y2] = M.toXY(b0.lon, b0.lat); avst = Math.hypot(x1 - x2, y1 - y2); }
    const dragVind = {}; for (const dr of (r.drag || [])) { const v = vind((dr.ah + dr.bh) / 2); const k = v ? `${v.navn} ${v.hoyde} moh` : 'ukjent'; dragVind[k] = dragVind[k] || { m: 0, fra: v && M.kompass(v.fra), ms: v && Math.round(v.ms), mot: 0 }; dragVind[k].m += dr.m; }
    ut.dager.push({ dag: d, dato, art, opplegg: { start: r.plan.start, slutt: r.plan.slutt, gjennomgang, to_biler: gjennomgang && avst > toBiler, biltekst: gjennomgang ? (avst > toBiler ? `to biler, én ved ${punkt(r.plan.start).navn} og én ved ${punkt(r.plan.slutt).navn}` : `bilen står ved ${punkt(r.plan.slutt).navn}`) : `bilen står ved ${punkt(r.plan.start).navn}` },
      valgt: sammendrag(r), forkastet: kand[1] ? sammendrag(kand[1].x) : null, feil: r.feil || null, retning_tekst: r.retning,
      felt: (r.maal || []).map(m => ({ nr: m.nr, lon: +m.lon.toFixed(5), lat: +m.lat.toFixed(5), hoyde_moh: m.h, ha: m.ha, middelscore: m.verdi, drag: m.drag })), drag_vind: dragVind, rute_celler_med_obsbonus: bonusCeller, observasjoner: relevante, logg: (r.logg || []).slice(-3) });
  }
  if (args.includes('--tekst')) {
    for (const d of ut.dager) { const v = d.valgt; console.log(`Dag ${d.dag} ${d.dato} ${d.art}: ${d.feil || `${d.opplegg.start} → ${d.opplegg.slutt} (${d.opplegg.biltekst}); ${v.km} km, ${v.hm} hm, ${v.timer} t, ${v.over60_pst} % over 60, overlapp ${v.overlapp_pst} %, ${v.motvind_pst} % av dragene mot vinden`}`); if (d.forkastet && !d.forkastet.feil) console.log(`   forkastet: ${d.forkastet.start} → ${d.forkastet.slutt}: ${d.forkastet.km} km, overlapp ${d.forkastet.overlapp_pst} %, ${d.forkastet.motvind_pst} % mot vinden`); console.log(`   ${d.retning_tekst}`); console.log(`   felt: ${d.felt.map(f => `${f.nr}: ${f.hoyde_moh} m, ${f.ha} ha, ${f.middelscore}`).join(' | ')}`); console.log(`   obs: ${d.observasjoner.map(x => `${x.id} ${x.type} vekt ${x.vekt_i_dag} ${x.avstand_til_naermeste_felt_m != null ? x.avstand_til_naermeste_felt_m + ' m fra nærmeste felt' : ''}`).join('; ') || 'ingen'}`); }
  } else console.log(JSON.stringify(ut, null, 1));
})().catch(e => { console.error(e); process.exit(1); });
