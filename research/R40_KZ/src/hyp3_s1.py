"""R40 stage E3 - Sentinel-1 InSAR/RTC through ASF HyP3 with an explicit credit budget.

modes:
  plan    : pick 12-day same-track IW SLC pairs fully covering the AOI (summer, snow-free months), print cost, submit nothing
  submit  : submit at most --max-jobs INSAR_GAMMA (20x4 looks) jobs within --budget credits; job ids are written to output
  collect : list jobs by name, download finished products (coherence, LOS angles, unwrapped phase) and summarise coherence

Token only from env EARTHDATA_TOKEN. Job ids are not secret and are stored in the repository.
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, collections
from pathlib import Path
import numpy as np
from . import common as C

BBOX = (76.85, 43.05, 77.20, 43.25)
PREFIX = "r40kz"
COST_INSAR_20x4 = 10  # confirmed from the HyP3 /costs endpoint in the estimate run (credits per job)


def pick_pairs(years=(2025,), months=("06", "07", "08", "09"), tracks=None, max_per_track=12):
    import asf_search as asf
    from shapely.geometry import box, shape
    aoi = box(*BBOX)
    res = asf.geo_search(intersectsWith=aoi.wkt, platform=[asf.PLATFORM.SENTINEL1], processingLevel=["SLC"], beamMode="IW",
                         start=f"{min(years)}-01-01T00:00:00Z", end=f"{max(years)}-12-31T23:59:59Z", maxResults=2000)
    by = collections.defaultdict(list)
    for r in res:
        p = r.properties
        d = p["startTime"][:10]
        if d[:4] not in map(str, years) or d[5:7] not in months:
            continue
        cover = shape(r.geometry).intersection(aoi).area / aoi.area
        by[(p["pathNumber"], p["flightDirection"])].append({"name": p["sceneName"], "date": d, "cover": cover})
    plan = []
    for key, sc in sorted(by.items()):
        if tracks and key[0] not in tracks:
            continue
        sc = sorted(sc, key=lambda x: x["date"])
        sc = [s for s in sc if s["cover"] >= 0.95]
        for a, b in zip(sc[:-1], sc[1:]):
            gap = (dt.date.fromisoformat(b["date"]) - dt.date.fromisoformat(a["date"])).days
            if gap == 12:
                plan.append({"track": key[0], "direction": key[1], "ref": a["name"], "sec": b["name"], "ref_date": a["date"], "sec_date": b["date"]})
    per = collections.Counter()
    out = []
    for p in plan:
        if per[p["track"]] < max_per_track:
            out.append(p); per[p["track"]] += 1
    return out, len(res)


def hyp3():
    import hyp3_sdk as sdk
    return sdk.HyP3(token=os.environ["EARTHDATA_TOKEN"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["plan", "submit", "collect"], default="plan")
    ap.add_argument("--years", default="2025")
    ap.add_argument("--tracks", default="")
    ap.add_argument("--max-per-track", type=int, default=12)
    ap.add_argument("--max-jobs", type=int, default=12)
    ap.add_argument("--budget", type=int, default=150, help="credits this run may spend")
    a = ap.parse_args()
    out = C.OUT
    out.mkdir(parents=True, exist_ok=True)
    years = tuple(int(y) for y in a.years.split(",") if y)
    tracks = [int(t) for t in a.tracks.split(",") if t] or None
    rep = {"mode": a.mode, "time": C.now(), "bbox_WSEN": BBOX}
    if a.mode in ("plan", "submit"):
        pairs, n_scenes = pick_pairs(years, tracks=tracks, max_per_track=a.max_per_track)
        rep["scenes_seen"] = n_scenes
        rep["pairs_selected"] = len(pairs)
        rep["cost_credits_if_all_submitted"] = len(pairs) * COST_INSAR_20x4
        rep["pairs"] = pairs
        C.write_json(out / "hyp3_plan.json", rep)
        print(f"pairs={len(pairs)} cost={len(pairs) * COST_INSAR_20x4} credits", flush=True)
    if a.mode == "submit":
        h = hyp3()
        before = h.check_credits()
        n = min(len(pairs), a.max_jobs, a.budget // COST_INSAR_20x4)
        jobs = []
        for p in pairs[:n]:
            name = f"{PREFIX}-t{p['track']}-{p['ref_date']}-{p['sec_date']}"
            j = h.submit_insar_job(p["ref"], p["sec"], name=name, looks="20x4", include_look_vectors=True, include_displacement_maps=False)
            jobs.append({"job_id": j.job_id, "name": name, **p})
        rep.update({"credits_before": before, "credits_after": h.check_credits(), "submitted": jobs})
        C.write_json(out / "hyp3_submitted.json", rep)
        print(f"submitted {len(jobs)} jobs; credits {before} -> {rep['credits_after']}", flush=True)
    if a.mode == "collect":
        h = hyp3()
        batch = h.find_jobs(name=None)
        mine = [j for j in batch if (j.name or "").startswith(PREFIX)]
        rows, d = [], out / "hyp3_products"
        d.mkdir(parents=True, exist_ok=True)
        for j in mine:
            row = {"job_id": j.job_id, "name": j.name, "status": j.status_code, "expires": str(j.expiration_time)}
            if j.succeeded():
                try:
                    paths = j.download_files(d, create=True)
                    row["files"] = [Path(p).name for p in paths]
                except Exception as e:  # noqa: BLE001
                    row["download_error"] = repr(e)[:200]
            rows.append(row)
        rep["jobs"] = rows
        C.write_json(out / "hyp3_collect.json", rep)
        print(f"jobs={len(rows)} succeeded={sum(r['status'] == 'SUCCEEDED' for r in rows)}", flush=True)


if __name__ == "__main__":
    main()
