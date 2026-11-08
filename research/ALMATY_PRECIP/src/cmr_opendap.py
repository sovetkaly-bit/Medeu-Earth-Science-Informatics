"""Monthly precipitation-phase series for Almaty from NASA Earthdata (MERRA-2 monthly flux, GPM IMERG monthly).
Access: CMR granule search -> OPeNDAP subset with the Earthdata bearer token (secret EARTHDATA_TOKEN)."""
import argparse, os, sys, time, json
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np, pandas as pd, requests, xarray as xr

CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
BOX = dict(lat=(42.5, 43.5), lon=(76.25, 77.5))  # around Almaty, covers 2x2 MERRA-2 cells
PRODUCTS = {
    "MERRA2": dict(short_name="M2TMNXFLX", vars=["PRECTOT", "PRECSNO", "PRECCON", "PRECLSC"]),
    "IMERG": dict(short_name="GPM_3IMERGM", vars=["precipitation"]),
}

def session():
    s = requests.Session()
    tok = os.environ.get("EARTHDATA_TOKEN", "")
    if not tok:
        sys.exit("EARTHDATA_TOKEN is empty")
    s.headers["Authorization"] = "Bearer " + tok
    return s

def granules(short_name, y0, y1):
    out, page = [], 1
    while True:
        r = requests.get(CMR, params=dict(short_name=short_name, temporal="%d-01-01T00:00:00Z,%d-12-31T23:59:59Z" % (y0, y1),
                                          page_size=2000, page_num=page, sort_key="start_date"), timeout=120)
        r.raise_for_status()
        items = r.json()["feed"]["entry"]
        if not items:
            break
        out += items
        page += 1
    return out

def opendap_url(g):
    for l in g.get("links", []):
        href = l.get("href", "")
        if "opendap" in href.lower() and not href.endswith(".html") and l.get("rel", "").endswith("/service#"):
            return href
    for l in g.get("links", []):
        if "opendap" in l.get("href", "").lower():
            return l["href"].replace(".html", "")
    return None

def subset(url, vars_, s):
    ds = xr.open_dataset(url, engine="pydap", session=s)
    latn = "lat" if "lat" in ds.coords else "latitude"
    lonn = "lon" if "lon" in ds.coords else "longitude"
    sub = ds[vars_].sel({latn: slice(*BOX["lat"]), lonn: slice(*BOX["lon"])})
    sub = sub.load()
    return sub.mean(dim=[latn, lonn])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", required=True, choices=list(PRODUCTS))
    ap.add_argument("--year-from", type=int, default=2000)
    ap.add_argument("--year-to", type=int, default=2025)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cfg = PRODUCTS[a.product]
    gs = granules(cfg["short_name"], a.year_from, a.year_to)
    print("granules:", len(gs), flush=True)
    if gs:
        print("example links:", json.dumps(gs[0].get("links", [])[:12], ensure_ascii=False)[:1500], flush=True)
    if a.limit:
        gs = gs[:a.limit]
    s = session()
    rows, failed = [], []

    def work(g):
        url = opendap_url(g)
        if not url:
            return g, None, "no opendap link"
        err = ""
        for attempt in range(3):
            try:
                m = subset(url, cfg["vars"], s)
                t = pd.Timestamp(g["time_start"][:10])
                rec = {"month": t.strftime("%Y-%m"), "granule": g["title"]}
                for v in cfg["vars"]:
                    rec[v] = float(np.asarray(m[v]).squeeze())
                return g, rec, ""
            except Exception as e:
                err = repr(e)[:300]; time.sleep(3)
        return g, None, err

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(work, g) for g in gs]
        for n, f in enumerate(as_completed(futs), 1):
            g, rec, err = f.result()
            if rec: rows.append(rec)
            else: failed.append((g["title"], err))
            if n % 24 == 0 or n <= 3:
                print("done %d/%d failed=%d last_err=%s" % (n, len(gs), len(failed), err), flush=True)
    rows.sort(key=lambda r: r["month"])
    pd.DataFrame(rows).to_csv(os.path.join(a.out, "%s_monthly_almaty.csv" % a.product.lower()), index=False)
    pd.DataFrame(failed, columns=["granule", "error"]).to_csv(os.path.join(a.out, "%s_failed.csv" % a.product.lower()), index=False)
    print("rows:", len(rows), "failed:", len(failed), flush=True)
    if not rows:
        sys.exit("no rows retrieved")

if __name__ == "__main__":
    main()
