import io, os, sys, zipfile, requests
import numpy as np, pandas as pd
OUT = sys.argv[1] if len(sys.argv) > 1 else "out"; os.makedirs(OUT, exist_ok=True)
URLS = ["https://www.glims.org/RGI/rgi60_files/13_rgi60_CentralAsia.zip",
        "https://www.glims.org/RGI/rgi60_files/13_rgi60_CentralAsia.zip".replace("www.glims.org", "glims.org")]
data = None
for u in URLS:
    try:
        r = requests.get(u, timeout=600); print(u, r.status_code, len(r.content), flush=True)
        if r.status_code == 200 and len(r.content) > 1e6: data = r.content; break
    except Exception as e: print(u, e, flush=True)
if data is None: sys.exit("download failed")
z = zipfile.ZipFile(io.BytesIO(data)); print(z.namelist()[:10], flush=True)
dbf = [n for n in z.namelist() if n.lower().endswith(".csv")]
print("csv files:", dbf, flush=True)
if dbf:
    df = pd.read_csv(z.open(dbf[0]))
else:
    z.extractall("rgi"); 
    sys.path.append(".")
    from dbfread import DBF
    f = [n for n in z.namelist() if n.endswith(".dbf")][0]
    df = pd.DataFrame(iter(DBF(os.path.join("rgi", f), encoding="latin1")))
print(df.columns.tolist(), len(df), flush=True)
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
