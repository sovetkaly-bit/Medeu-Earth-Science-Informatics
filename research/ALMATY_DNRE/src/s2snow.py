"""Sentinel-2 L2A NDSI snow frequency by elevation band around Kok-Zhailau (Nov-Apr, 2019-2025)."""
import json, sys, warnings, numpy as np, pandas as pd
import planetary_computer as pc
from pystac_client import Client
import odc.stac
from rasterio.warp import Resampling
warnings.filterwarnings("ignore")
sys.path.insert(0, "../../ALMATY_SNOW/src")
from dem import dem_on_grid

BBOX = [76.90, 43.08, 77.12, 43.22]
BANDS = [(900, 1300), (1300, 1700), (1700, 2000), (2000, 2300), (2300, 2600), (2600, 3000), (3000, 3600)]
cat = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=pc.sign_inplace)


def main(out):
    rows, dem = [], None
    for y in range(2019, 2026):
        for (m0, m1) in [((y, 11), (y, 12)), ((y + 1, 1), (y + 1, 4))]:
            t0 = f"{m0[0]}-{m0[1]:02d}-01"; t1 = f"{m1[0]}-{m1[1]:02d}-28"
            items = list(cat.search(collections=["sentinel-2-l2a"], bbox=BBOX, datetime=f"{t0}/{t1}",
                                    query={"eo:cloud_cover": {"lt": 50}}).items())
            for it in items:
                try:
                    ds = odc.stac.load([it], bands=["B03", "B11", "SCL"], bbox=BBOX, resolution=60, crs="EPSG:32643",
                                       resampling="bilinear", groupby="solar_day").isel(time=0).compute()
                    off = 1000.0 if it.properties.get("s2:processing_baseline", "04.00") >= "04.00" else 0.0
                    g = (ds.B03.astype("float32") - off) / 10000.0; s = (ds.B11.astype("float32") - off) / 10000.0
                    ndsi = ((g - s) / (g + s + 1e-6)).values
                    scl = ds.SCL.values
                    valid = np.isin(scl, [4, 5, 6, 11])  # veg, bare, water, snow -> not cloud/shadow
                    snow = (ndsi > 0.4) & (g.values > 0.11) & valid
                    if dem is None:
                        tr = ds.odc.geobox.affine
                        dem, _ = dem_on_grid(dict(west=BBOX[0], south=BBOX[1], east=BBOX[2], north=BBOX[3]),
                                             "EPSG:32643", tr, snow.shape, "cop-dem-glo-30", Resampling.bilinear)
                    for lo, hi in BANDS:
                        mk = (dem >= lo) & (dem < hi) & valid
                        if mk.sum() < 50:
                            continue
                        rows.append(dict(date=str(it.datetime.date()), season=y + 1,
                                         month=it.datetime.month, band=f"{lo}-{hi}", frac_snow=float(snow[mk].mean()),
                                         n=int(mk.sum())))
                except Exception as e:
                    print("ERR", it.id, repr(e)[:150], flush=True)
            print(y, m0, len(items), flush=True)
    df = pd.DataFrame(rows)
    assert len(df) > 20, "empty S2 result"
    df.to_csv(f"{out}/s2_snow_scenes_by_band.csv", index=False)
    piv = df.groupby(["band", "month"]).frac_snow.agg(["mean", "count"]).round(3).reset_index()
    piv.to_csv(f"{out}/s2_snow_band_month.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1])
