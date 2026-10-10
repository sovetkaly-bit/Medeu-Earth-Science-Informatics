"""Shared helpers: audit log, JSON/CSV writers, hashing, HTTP with retries, UTM selection."""
from __future__ import annotations
import csv, datetime as dt, hashlib, json, math, os, sys, time, traceback
from pathlib import Path

OUT = Path(os.environ.get("R40_OUT", "output"))
AUDIT: list[dict] = []
ERRORS: list[dict] = []
UA = "R40-KZ-research/1.0 (+https://github.com/sovetkaly-bit/Medeu-Earth-Science-Informatics)"


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def log(site, source, status, detail="", n=None):
    row = dict(time=now(), site=site, source=source, status=status, details=str(detail)[:1800], count=n)
    AUDIT.append(row)
    print(f"[{site}] {source}: {status} {str(detail)[:300]}", flush=True)


def log_exc(site, source, exc, status="FAILED"):
    tb = traceback.format_exc()
    ERRORS.append(dict(time=now(), site=site, source=source, error=repr(exc), traceback=tb))
    log(site, source, status, repr(exc))


def write_json(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def write_csv(p, rows, fieldnames=None):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if not rows:
        return
    if fieldnames is None:
        fieldnames = []
        for r in rows:
            for k in r:
                if k not in fieldnames:
                    fieldnames.append(k)
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def utm_epsg(lon, lat):
    zone = int((lon + 180) // 6) + 1
    return (32600 if lat >= 0 else 32700) + zone


def http_json(url, params=None, data=None, headers=None, timeout=90, retries=3, method=None):
    import requests
    h = {"User-Agent": UA}
    h.update(headers or {})
    last = None
    for i in range(retries):
        try:
            if data is not None or method == "POST":
                r = requests.post(url, params=params, data=data, headers=h, timeout=timeout)
            else:
                r = requests.get(url, params=params, headers=h, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise last
