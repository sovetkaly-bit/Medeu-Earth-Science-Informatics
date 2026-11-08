import io, os, sys, zipfile, requests
import numpy as np, pandas as pd
OUT = sys.argv[1] if len(sys.argv) > 1 else "out"; os.makedirs(OUT, exist_ok=True)
URL = "https://cluster.klima.uni-bremen.de/~oggm/rgi/rgi62_stats.csv"
r = requests.get(URL, timeout=600); print(URL, r.status_code, len(r.content), flush=True)
r.raise_for_status()
df = pd.read_csv(io.StringIO(r.text), index_col=0, low_memory=False)
print(df.columns.tolist(), len(df), flush=True)
df = df.reset_index().rename(columns={df.index.name or "index": "RGIId"}) if "RGIId" not in df.columns else df
for c in ("CenLat", "CenLon"):
    df[c] = pd.to_numeric(df[c])
for c in ("BgnDate", "EndDate", "Slope", "Aspect", "Name", "GLIMSId"):
    if c not in df.columns: df[c] = np.nan
lat = "CenLat"; lon = "CenLon"
box = df[(df[lat].between(43.0, 43.5)) & (df[lon].between(76.4, 78.0))].copy()
box["Zmed"] = pd.to_numeric(box["Zmed"]); box["Area"] = pd.to_numeric(box["Area"])
print("glaciers in box:", len(box), "area km2:", box.Area.sum().round(1), flush=True)
bins = [0, 3000, 3250, 3500, 3750, 4000, 4250, 5000]
box["zbin"] = pd.cut(box.Zmed, bins)
agg = box.groupby("zbin").agg(n=("Area", "size"), area_km2=("Area", "sum"), mean_zmin=("Zmin", "mean"), mean_zmax=("Zmax", "mean")).round(2)
agg.to_csv(os.path.join(OUT, "glaciers_by_median_elevation.csv"))
box[["RGIId", "GLIMSId", "BgnDate", "EndDate", "CenLon", "CenLat", "Area", "Zmin", "Zmax", "Zmed", "Slope", "Aspect", "Name"]].to_csv(os.path.join(OUT, "glaciers_ile_alatau.csv"), index=False)
sm = pd.DataFrame({"glaciers": [len(box)], "area_km2": [round(box.Area.sum(), 1)], "median_Zmed_m": [box.Zmed.median()], "min_Zmin_m": [box.Zmin.min()], "bgn_date_range": [f"{box.BgnDate.min()}-{box.BgnDate.max()}"]})
sm.to_csv(os.path.join(OUT, "summary.csv"), index=False); print(sm.to_string(), flush=True); print(agg.to_string(), flush=True)
