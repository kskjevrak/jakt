"""Valider og legg observasjoner inn i data/observasjoner.geojson. Brukes av /obs og for å promotere en jaktlogg.

  python scripts/obs_add.py nye.geojson            # legger til features (GeoJSON FeatureCollection eller liste av features)
  python scripts/obs_add.py nye.geojson --tabell   # viser bare tabellen, skriver ikke
  python scripts/obs_add.py logg.geojson --fra-logg # konverterer eksportert jaktlogg (type stokk/felt, tid) til schemaet først

Schema per feature: id, dato (ISO), dato_usikker (bool), art (lirype|orrfugl|storfugl|ukjent_honsefugl),
kjonn (tiur|roy|hann|hunn|ukjent), antall (tall eller null), type (sett|stokket|felt|spor|omrade), kilde (navn),
presisjon_m (tall eller null), notat. Geometri Point eller Polygon i WGS84.
Manglende id lages. Dubletter på id hoppes over. Rapporterer om punktet ligger innenfor jaktfeltet.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "observasjoner.geojson"
ARTER = {"lirype", "orrfugl", "storfugl", "ukjent_honsefugl"}
KJONN = {"tiur", "roy", "hann", "hunn", "ukjent"}  # tiur/roy for storfugl, hann/hunn for orrfugl and lirype
TYPER = {"sett", "stokket", "felt", "spor", "omrade"}


def fra_logg(f: dict) -> dict:
    p = f.get("properties", {})
    return {"type": "Feature", "geometry": f["geometry"],
            "properties": {"id": None, "dato": (p.get("tid") or "")[:10], "dato_usikker": False, "art": p.get("art") if p.get("art") in ARTER else "ukjent_honsefugl",
                           "kjonn": "ukjent", "antall": p.get("antall"), "type": "felt" if p.get("type") == "felt" else "stokket",
                           "kilde": "jaktlogg", "presisjon_m": p.get("noyaktighet_m"), "notat": p.get("notat") or ""}}


def valider(f: dict, inne) -> tuple[dict, list[str]]:
    feil = []
    p = dict(f.get("properties") or {}); g = f.get("geometry") or {}
    if g.get("type") not in ("Point", "Polygon"):
        feil.append("geometri må være Point eller Polygon")
    try:
        date.fromisoformat(str(p.get("dato"))[:10])
    except Exception:  # noqa: BLE001
        feil.append(f"ugyldig dato {p.get('dato')!r}")
    if p.get("art") not in ARTER: feil.append(f"ukjent art {p.get('art')!r}")
    if p.get("kjonn", "ukjent") not in KJONN: feil.append(f"ukjent kjonn {p.get('kjonn')!r}")
    if p.get("type") not in TYPER: feil.append(f"ukjent type {p.get('type')!r}")
    if not p.get("kilde"): feil.append("kilde mangler")
    p.setdefault("kjonn", "ukjent"); p.setdefault("dato_usikker", False); p.setdefault("antall", None); p.setdefault("presisjon_m", None); p.setdefault("notat", "")
    if p.get("antall") is not None:
        try: p["antall"] = int(p["antall"])
        except Exception: feil.append("antall må være tall eller null")  # noqa: BLE001
    p["innenfor_jaktfelt"] = inne(g) if g.get("type") else None
    return {"type": "Feature", "properties": p, "geometry": g}, feil


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__); return 2
    bare_tabell = "--tabell" in sys.argv; konverter = "--fra-logg" in sys.argv
    ny = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    feats = ny.get("features", ny) if isinstance(ny, dict) else ny
    if konverter: feats = [fra_logg(f) for f in feats]
    db = json.loads(DB.read_text(encoding="utf-8"))
    ider = {f["properties"]["id"] for f in db["features"]}
    # inside-check against the hunting ground
    try:
        import geopandas as gpd
        from shapely.geometry import shape
        jf = gpd.read_file(ROOT / "data" / "jaktfelt.geojson").geometry.iloc[0]
        def inne(g):
            s = shape(g); return bool(jf.intersects(s)) if s.geom_type == "Polygon" else bool(jf.contains(s))
    except Exception:  # noqa: BLE001
        def inne(g): return None
    sys.stdout.reconfigure(encoding="utf-8")
    print("| id | dato | art | kjonn | antall | type | kilde | presisjon | innenfor | notat |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    godkjente = []; alle_feil = 0
    for i, f in enumerate(feats):
        f, feil = valider(f, inne)
        p = f["properties"]
        if not p.get("id"):
            base = f"o-{str(p.get('dato', '00000000'))[:10].replace('-', '')}"
            n = 1
            while f"{base}-{n:02d}" in ider: n += 1
            p["id"] = f"{base}-{n:02d}"
        if p["id"] in ider: feil.append("id finnes fra før, hoppes over")
        ider.add(p["id"])
        inn = p.pop("innenfor_jaktfelt")
        print(f"| {p['id']} | {p['dato']}{' (usikker)' if p['dato_usikker'] else ''} | {p['art']} | {p['kjonn']} | {p['antall'] if p['antall'] is not None else '–'} | {p['type']} | {p['kilde']} | {p['presisjon_m'] or '–'} | {'ja' if inn else 'nei' if inn is False else '?'} | {(p['notat'] or '')[:60]}{' **FEIL: ' + '; '.join(feil) + '**' if feil else ''} |")
        if feil: alle_feil += 1
        else: godkjente.append(f)
    if bare_tabell:
        print(f"\n{len(godkjente)} gyldige, {alle_feil} med feil. Ingenting skrevet (--tabell)."); return 0
    if alle_feil:
        print(f"\n{alle_feil} med feil. Rett dem før innlegging; ingenting skrevet."); return 1
    db["features"].extend(godkjente)
    DB.write_text(json.dumps(db, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\n{len(godkjente)} observasjoner lagt til i {DB.relative_to(ROOT)} (totalt {len(db['features'])}). Commit filen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
