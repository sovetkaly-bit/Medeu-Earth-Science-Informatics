import io, math, os, sys
import numpy as np, pandas as pd, requests
from scipy.stats import theilslopes, kendalltau
OUT = sys.argv[1] if len(sys.argv) > 1 else "out"; os.makedirs(OUT, exist_ok=True)
LAT0, LON0, RADIUS = 43.25, 76.95, 450
BASE = "https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/"
def hav(a, b, c, d):
    p = math.pi / 180; x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))
txt = requests.get("https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt", timeout=120).text
st = []
for l in txt.splitlines():
    if l[:2] in ("KZ", "KG", "UZ", "CH") or l[:2] == "KZ":
        try: lat, lon, el = float(l[12:20]), float(l[21:30]), float(l[31:37])
        except: continue
        dist = hav(LAT0, LON0, lat, lon)
        if dist <= RADIUS: st.append((l[:11], l[41:71].strip(), lat, lon, el, round(dist)))
print("candidates:", len(st), flush=True)
def tr(s, w):
    s = s.dropna(); s = s[s.index >= w]
    if len(s) < 15: return None
    x = s.index.values.astype(float); sl = theilslopes(s.values, x)[0] * 10; t, p = kendalltau(x, s.values)
    return round(sl, 3), round(p, 4), len(s)
rows, meta = [], []
for sid, name, lat, lon, el, dist in st:
    try:
        r = requests.get(BASE + sid + ".csv", timeout=120)
        if r.status_code != 200: continue
        d = pd.read_csv(io.StringIO(r.text), low_memory=False, parse_dates=["DATE"]).set_index("DATE").sort_index()
    except Exception as e:
        print(sid, e); continue
    for c in ("TMAX", "TMIN", "TAVG", "PRCP"):
        if c in d: d[c] = pd.to_numeric(d[c], errors="coerce") / 10
    meta.append(dict(id=sid, name=name, lat=lat, lon=lon, elev=el, dist_km=dist, first=str(d.index.min().date()), last=str(d.index.max().date()), days=len(d)))
    for c, nm in (("TMAX", "Tmax"), ("TMIN", "Tmin"), ("PRCP", "Precip")):
        if c not in d: continue
        for lab, ms, shift in (("year", range(1, 13), False), ("DJF", [12, 1, 2], True), ("MAM", [3, 4, 5], False)):
            m = d[d.index.month.isin(list(ms))][c].dropna()
            if m.empty: continue
            yr = np.where(m.index.month >= 9, m.index.year + 1, m.index.year) if shift else m.index.year
            g = m.groupby(yr)
            need = {"year": 330, "DJF": 80, "MAM": 80}[lab]
            ok = g.count() >= need
            val = (g.mean() if c != "PRCP" else g.sum())[ok]
            for w in (1961, 1991):
                t = tr(val, w)
                if t: rows.append(dict(id=sid, name=name, elev=el, var=nm, season=lab, window=w, slope_per_10y=t[0], p=t[1], n=t[2]))
pd.DataFrame(meta).to_csv(os.path.join(OUT, "stations.csv"), index=False)
pd.DataFrame(rows).to_csv(os.path.join(OUT, "trends_neighbors.csv"), index=False)
print("stations used:", len(meta), "rows:", len(rows))
