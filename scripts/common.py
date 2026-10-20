"""Shared helpers for all fetch scripts: HTTP session, caching, paths, reporting.

Every network call goes through `download_file` / `http_get_*` so that:
  * the User-Agent identifies the project,
  * responses are cached under raw/ and re-used when the server says 304 or the
    cache entry is younger than `max_age`,
  * large files can resume with HTTP Range,
  * every fetch is logged into raw/_cache.json and surfaces in data/SOURCES.md.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
DATA = ROOT / "data"
CONFIG = ROOT / "config"
CACHE_INDEX = RAW / "_cache.json"

USER_AGENT = "jakt-bygland/0.1 (+https://github.com/kskjevrak/jakt)"
KOMMUNE = "4220"
KOMMUNENAVN = "Bygland"
MATRIKKEL = [(49, 1), (49, 2), (49, 3), (49, 4), (50, 1)]
CRS_UTM33 = "EPSG:25833"

DAY = 24 * 3600


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def ensure_dirs() -> None:
    RAW.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)


def session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    s.headers["Accept"] = "*/*"
    return s


SESSION = session()


def _load_index() -> dict[str, Any]:
    if CACHE_INDEX.exists():
        try:
            return json.loads(CACHE_INDEX.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _save_index(idx: dict[str, Any]) -> None:
    ensure_dirs()
    CACHE_INDEX.write_text(json.dumps(idx, indent=1, ensure_ascii=False), encoding="utf-8")


def url_key(url: str, params: dict | None = None) -> str:
    full = url if not params else url + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return hashlib.sha1(full.encode("utf-8")).hexdigest()[:16]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def human(n: int | float | None) -> str:
    if n is None:
        return "?"
    n = float(n)
    for unit in ("B", "kB", "MB", "GB"):
        if n < 1024:
            return f"{int(n)} B" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def download_file(
    url: str,
    dest: Path,
    *,
    params: dict | None = None,
    max_age: float | None = 7 * DAY,
    force: bool = False,
    resume: bool = True,
    timeout: int = 600,
    note: str = "",
    method: str = "GET",
    json_body: Any = None,
) -> Path:
    """Download `url` to `dest` with conditional requests, resume and index logging.

    Returns the path. Raises for HTTP errors. POST requests are cached by
    URL + body hash and are never resumed.
    """
    ensure_dirs()
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    idx = _load_index()
    if method == "GET":
        key = url_key(url, params)
    else:
        key = url_key(url, {"body": json.dumps(json_body, sort_keys=True)})
    entry = idx.get(key, {})

    if dest.exists() and not force and entry.get("complete"):
        age = time.time() - entry.get("fetched_epoch", 0)
        if max_age is None or age < max_age:
            log(f"cache hit  {dest.relative_to(ROOT)} ({human(dest.stat().st_size)}, {age / DAY:.1f} d old)")
            return dest
        headers = {}
        if entry.get("etag"):
            headers["If-None-Match"] = entry["etag"]
        if entry.get("last_modified"):
            headers["If-Modified-Since"] = entry["last_modified"]
        if headers and method == "GET":
            r = SESSION.get(url, params=params, headers=headers, timeout=timeout, stream=True)
            if r.status_code == 304:
                r.close()
                entry["fetched_epoch"] = time.time()
                entry["fetched_at"] = now_iso()
                idx[key] = entry
                _save_index(idx)
                log(f"not modified {dest.relative_to(ROOT)}")
                return dest
            r.close()

    headers = {}
    mode = "wb"
    partial = dest.with_suffix(dest.suffix + ".part")
    if method == "GET" and resume and partial.exists() and entry.get("url") == url and not force:
        headers["Range"] = f"bytes={partial.stat().st_size}-"
        mode = "ab"

    shown = url if not params else url + " " + json.dumps(params, ensure_ascii=False)[:160]
    log(f"fetch      {shown}")
    if method == "GET":
        r = SESSION.get(url, params=params, headers=headers, timeout=timeout, stream=True)
    else:
        r = SESSION.post(url, params=params, json=json_body, headers=headers, timeout=timeout, stream=True)
    if r.status_code == 416:  # range not satisfiable -> partial is already complete
        r.close()
        partial.replace(dest)
    else:
        if r.status_code == 200 and mode == "ab":
            mode = "wb"  # server ignored Range, start over
        r.raise_for_status()
        total = r.headers.get("Content-Length")
        already = partial.stat().st_size if mode == "ab" else 0
        done = already
        expected = (int(total) + already) if total else None
        t0 = time.time()
        next_report = 50 << 20
        with open(partial, mode) as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if not chunk:
                    continue
                f.write(chunk)
                done += len(chunk)
                if done >= next_report:
                    next_report += 50 << 20
                    pct = f"{100 * done / expected:.0f}%" if expected else "?"
                    rate = (done - already) / max(time.time() - t0, 1e-6)
                    log(f"  ... {human(done)} ({pct}, {human(rate)}/s)")
        partial.replace(dest)
        entry = {
            "url": url,
            "params": params,
            "method": method,
            "path": str(dest.relative_to(ROOT)),
            "etag": r.headers.get("ETag"),
            "last_modified": r.headers.get("Last-Modified"),
            "content_type": r.headers.get("Content-Type"),
            "size": dest.stat().st_size,
            "fetched_at": now_iso(),
            "fetched_epoch": time.time(),
            "complete": True,
            "note": note,
        }
        idx[key] = entry
        _save_index(idx)
    log(f"saved      {dest.relative_to(ROOT)} ({human(dest.stat().st_size)})")
    return dest


def http_get_json(url: str, params: dict | None = None, timeout: int = 120, **kw) -> Any:
    r = SESSION.get(url, params=params, timeout=timeout, **kw)
    r.raise_for_status()
    return r.json()


def http_get_text(url: str, params: dict | None = None, timeout: int = 120, **kw) -> str:
    r = SESSION.get(url, params=params, timeout=timeout, **kw)
    r.raise_for_status()
    return r.text


def cache_entry_for(path: Path) -> dict[str, Any]:
    rel = str(Path(path).resolve().relative_to(ROOT))
    for e in _load_index().values():
        if e.get("path") == rel:
            return e
    return {}


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------
@dataclass
class Attempt:
    route: str  # "WFS" | "WCS" | "REST" | "Atom" | "Nedlastings-API" | "WMS" | "manuell"
    url: str
    ok: bool
    detail: str = ""


@dataclass
class SourceReport:
    name: str
    dataset: str
    license: str
    attempts: list[Attempt] = field(default_factory=list)
    route_used: str = ""
    files: list[dict[str, Any]] = field(default_factory=list)  # {path,size,last_modified,url}
    version: str = ""
    notes: list[str] = field(default_factory=list)
    ok: bool = False

    def attempt(self, route: str, url: str, ok: bool, detail: str = "") -> None:
        self.attempts.append(Attempt(route, url, ok, detail))
        log(f"  {'OK ' if ok else 'FAIL'} {route}: {detail or url}")

    def add_file(self, path: Path, url: str = "", last_modified: str | None = None) -> None:
        p = Path(path)
        e = cache_entry_for(p)
        self.files.append(
            {
                "path": str(p.relative_to(ROOT)),
                "size": p.stat().st_size if p.exists() else None,
                "last_modified": last_modified or e.get("last_modified") or "",
                "fetched_at": e.get("fetched_at", now_iso()),
                "url": url or e.get("url", ""),
            }
        )

    def total_size(self) -> int:
        return sum(f["size"] or 0 for f in self.files)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_reports(reports: Iterable[SourceReport]) -> None:
    """Write data/sources.json (machine readable) and data/SOURCES.md (human)."""
    ensure_dirs()
    reports = list(reports)
    (DATA / "sources.json").write_text(
        json.dumps([r.to_dict() for r in reports], indent=1, ensure_ascii=False), encoding="utf-8"
    )
    lines = [
        "# Datakilder",
        "",
        f"Generert av `scripts/download.py` {now_iso()}. Alle kilder er åpne data (NLOD / CC BY 4.0) med mindre annet er nevnt.",
        "Rekkefølge som ble forsøkt per kilde: (1) WFS/WCS/REST, (2) Atom feed, (3) Geonorge/NIBIO nedlastings-API, (4) manuelt.",
        "",
        "| Kilde | Vei som fungerte | Størrelse | Datert (server) | Hentet |",
        "|---|---|---|---|---|",
    ]
    for r in reports:
        dated = ", ".join(sorted({f["last_modified"] for f in r.files if f["last_modified"]})) or r.version or "–"
        fetched = max((f["fetched_at"] for f in r.files), default="–")[:10]
        lines.append(f"| {r.name} | {r.route_used or 'INGEN'} | {human(r.total_size())} | {dated} | {fetched} |")
    lines.append("")
    for r in reports:
        lines += [
            f"## {r.name}",
            "",
            f"Datasett: {r.dataset}  ",
            f"Lisens: {r.license}  ",
            f"Status: {'OK' if r.ok else 'FEILET'} via **{r.route_used or 'ingen'}**",
            "",
        ]
        if r.version:
            lines += [f"Versjon/dato: {r.version}", ""]
        lines.append("Forsøk:")
        for a in r.attempts:
            tail = f" – {a.detail}" if a.detail else ""
            lines.append(f"- {'OK' if a.ok else 'FEIL'} {a.route}: `{a.url}`{tail}")
        if r.files:
            lines += ["", "Filer:"]
            for f in r.files:
                lines.append(
                    f"- `{f['path']}` ({human(f['size'])}, Last-Modified: {f['last_modified'] or '?'}, hentet {f['fetched_at']})  "
                )
                if f["url"]:
                    lines.append(f"  `{f['url']}`")
        if r.notes:
            lines += ["", "Merknader:"]
            lines += [f"- {n}" for n in r.notes]
        lines.append("")
    (DATA / "SOURCES.md").write_text("\n".join(lines), encoding="utf-8")


def load_aoi() -> dict[str, Any]:
    """AOI bbox in EPSG:25833 written by build_jaktfelt.py: {minx,miny,maxx,maxy,...}."""
    p = RAW / "aoi.json"
    if not p.exists():
        raise SystemExit("raw/aoi.json mangler – kjør fetch_teig.py / build_jaktfelt.py først")
    return json.loads(p.read_text(encoding="utf-8"))


def parse_args(argv: list[str] | None = None) -> dict[str, bool]:
    argv = sys.argv[1:] if argv is None else argv
    return {"force": "--force" in argv, "verbose": "-v" in argv}
