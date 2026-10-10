"""R40 stage E0 - availability + volume + cost ESTIMATE for ICESat-2, GEDI and Sentinel-1 (HyP3). Submits nothing.

Token policy: read ONLY from environment variable EARTHDATA_TOKEN (GitHub Actions secret). Never printed, never written.
Run from research/R40_KZ:  python -m src.estimate_earthdata
"""
from __future__ import annotations
import json, os, time, datetime as dt, collections
import requests
from shapely.geometry import box
from . import common as C

BBOX = (76.85, 43.05, 77.20, 43.25)  # W,S,E,N - Almaty foothills study area (as checked by the author in Earthdata Search)
CMR = "https://cmr.earthdata.nasa.gov/search"
START = "2018-10-01T00:00:00Z"
OUT = C.OUT


def token():
    return os.environ.get("EARTHDATA_TOKEN", "").strip() or None


def auth_headers():
    t = token()
    return {"Authorization": f"Bearer {t}"} if t else {}


def check_token():
    t = token()
    if not t:
        return {"status": "NO_TOKEN_IN_ENV"}
    try:
        r = requests.get("https://urs.earthdata.nasa.gov/api/users/user", headers=auth_headers(), timeout=60)
        j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        exp = None
        try:
            import base64
            body = t.split(".")[1]
            body += "=" * (-len(body) % 4)
            exp = dt.datetime.fromtimestamp(json.loads(base64.urlsafe_b64decode(body))["exp"], dt.timezone.utc).isoformat()
        except Exception:  # noqa: BLE001
            pass
        return {"status": "TOKEN_ACCEPTED" if r.status_code == 200 else f"HTTP_{r.status_code}", "username": j.get("uid"), "token_expires_utc": exp}
    except Exception as e:  # noqa: BLE001
        return {"status": "ERROR", "error": repr(e)}


def cmr_granules(short_name, version=None, bbox=BBOX, start=START, page_size=2000):
    params = {"short_name": short_name, "bounding_box": ",".join(map(str, bbox)),
              "temporal": f"{start},{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}", "page_size": page_size}
    if version:
        params["version"] = version
    r = requests.get(f"{CMR}/granules.json", params=params, timeout=120)
    r.raise_for_status()
    ents = r.json()["feed"]["entry"]
    total_hits = int(r.headers.get("CMR-Hits", len(ents)))
    mb = sum(float(e.get("granule_size", 0) or 0) for e in ents)
    years = collections.Counter(e["time_start"][:4] for e in ents)
    return {"short_name": short_name, "version": version, "hits": total_hits, "returned": len(ents), "total_size_GB": round(mb / 1024, 2),
            "mean_granule_MB": round(mb / max(len(ents), 1), 1), "by_year": dict(sorted(years.items())),
            "first": ents[0]["time_start"] if ents else None, "last": ents[-1]["time_start"] if ents else None,
            "example_ids": [e.get("producer_granule_id") for e in ents[:3]]}


def latest_version(short_name):
    r = requests.get(f"{CMR}/collections.json", params={"short_name": short_name, "page_size": 50}, timeout=60)
    vs = sorted({e["version_id"] for e in r.json()["feed"]["entry"]})
    return vs[-1] if vs else None


def icesat_gedi():
    rows = []
    for sn in ("ATL08", "ATL03", "GEDI02_A"):
        try:
            v = latest_version(sn)
            rows.append(cmr_granules(sn, v))
            C.log("E0", sn, "FOUND", f"v{v}: {rows[-1]['hits']} granules, {rows[-1]['total_size_GB']} GB (full granules)", rows[-1]["hits"])
        except Exception as e:  # noqa: BLE001
            C.log_exc("E0", sn, e, "SEARCH_FAILED")
            rows.append({"short_name": sn, "error": repr(e)})
    return rows


def streaming_test():
    """Open ONE ATL08 granule remotely (HTTP range reads) and read segment coordinates - measures feasibility without bulk download."""
    t = token()
    if not t:
        return {"status": "NO_TOKEN"}
    try:
        import earthaccess, h5py, numpy as np
        earthaccess.login(strategy="environment")
        res = earthaccess.search_data(short_name="ATL08", bounding_box=BBOX, count=1)
        if not res:
            return {"status": "NO_GRANULE"}
        t0 = time.time()
        f = earthaccess.open(res[:1])[0]
        h = h5py.File(f, "r")
        beams = [k for k in h if k.startswith("gt")]
        out = {"status": "OK", "granule": res[0]["umm"]["GranuleUR"], "beams": beams}
        n_in = 0
        for b in beams:
            lat = h[f"{b}/land_segments/latitude"][:]
            lon = h[f"{b}/land_segments/longitude"][:]
            m = (lon >= BBOX[0]) & (lon <= BBOX[2]) & (lat >= BBOX[1]) & (lat <= BBOX[3])
            n_in += int(m.sum())
        out.update({"segments_in_bbox_this_granule": n_in, "seconds": round(time.time() - t0, 1),
                    "datasets_example": list(h[f"{beams[0]}/land_segments/terrain"].keys())[:25] if beams else []})
        return out
    except Exception as e:  # noqa: BLE001
        C.log_exc("E0", "icesat2-stream-test", e)
        return {"status": "ERROR", "error": repr(e)[:500]}


def sentinel1():
    try:
        import asf_search as asf
        wkt = box(*BBOX).wkt
        res = asf.geo_search(intersectsWith=wkt, platform=[asf.PLATFORM.SENTINEL1], processingLevel=["SLC"], beamMode="IW",
                             start="2021-01-01T00:00:00Z", end=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), maxResults=2000)
        tracks = collections.defaultdict(list)
        for r in res:
            p = r.properties
            tracks[(p.get("pathNumber"), p.get("flightDirection"))].append(p.get("startTime")[:10])
        rows = []
        for (path, d), days in sorted(tracks.items()):
            days = sorted(days)
            summer = [x for x in days if x[5:7] in ("06", "07", "08", "09")]
            rows.append({"relative_orbit": path, "direction": d, "scenes": len(days), "summer_JJAS_scenes": len(summer), "first": days[0], "last": days[-1]})
        return {"status": "OK", "total_scenes": len(res), "tracks": rows}
    except Exception as e:  # noqa: BLE001
        C.log_exc("E0", "asf-sentinel1", e)
        return {"status": "ERROR", "error": repr(e)[:500]}


def hyp3_info():
    t = token()
    if not t:
        return {"status": "NO_TOKEN"}
    try:
        import hyp3_sdk as sdk
        h = sdk.HyP3(token=t)
        out = {"status": "OK", "remaining_credits": h.check_credits()}
        try:
            out["user"] = {k: v for k, v in h.my_info().items() if k in ("user_id", "remaining_credits", "job_names", "application_status")}
        except Exception as e:  # noqa: BLE001
            out["my_info_error"] = repr(e)[:200]
        try:
            import requests as rq
            r = rq.get(f"{h.url}/costs", headers={"Authorization": f"Bearer {t}"}, timeout=60)
            out["costs_http"] = r.status_code
            if r.ok:
                out["costs"] = r.json()
        except Exception as e:  # noqa: BLE001
            out["costs_error"] = repr(e)[:200]
        return out
    except Exception as e:  # noqa: BLE001
        C.log_exc("E0", "hyp3", e)
        return {"status": "ERROR", "error": repr(e)[:500]}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rep = {"generated_utc": C.now(), "bbox_WSEN": BBOX, "submits_jobs": False}
    rep["earthdata_token"] = check_token()
    C.log("E0", "earthdata-token", rep["earthdata_token"]["status"], rep["earthdata_token"].get("username", ""))
    rep["cmr_granules"] = icesat_gedi()
    rep["icesat2_streaming_test"] = streaming_test()
    rep["sentinel1_slc_asf"] = sentinel1()
    rep["hyp3"] = hyp3_info()
    C.write_json(OUT / "earthdata_estimate.json", rep)
    C.write_csv(OUT / "earthdata_estimate_status.csv", C.AUDIT, ["time", "site", "source", "status", "details", "count"])
    C.write_json(OUT / "earthdata_estimate_errors.json", C.ERRORS)
    print("DONE-ESTIMATE")


if __name__ == "__main__":
    main()
