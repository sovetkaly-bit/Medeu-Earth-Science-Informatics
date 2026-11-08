"""TerraClimate monthly precipitation, SWE, Tmax, Tmin (model-based, ~4 km) from Planetary Computer, by DEM band.

Output: out/terraclimate_monthly_by_band.csv. This is a gridded model product, not station measurements.
"""
import json
import os

import numpy as np
import pandas as pd
import planetary_computer
import pystac_client
import xarray as xr
from rasterio.transform import from_origin

from src.common import assign_bands
from src.dem import dem_on_grid, STAC

CFG = json.load(open(os.path.join(os.path.dirname(__file__), "..", "config.json")))


def main(out=None):
    out = out or os.environ.get("ALMATY_OUT", "out")
    os.makedirs(out, exist_ok=True)
    aoi = CFG["aoi"]
    cat = pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)
    col = cat.get_collection(CFG["terraclimate_collection"])
    asset = planetary_computer.sign(col.assets["zarr-abfs"])
    print("asset href:", asset.href, "extra keys:", list(asset.extra_fields), flush=True)
    kw = dict(asset.extra_fields.get("xarray:open_kwargs") or {})
    kw.setdefault("consolidated", True)
    so = asset.extra_fields.get("xarray:storage_options")
    if so and "storage_options" not in kw:
        kw["storage_options"] = so
    print("open kwargs keys:", list(kw), flush=True)
    kw.pop("consolidated", None)
    ds = xr.open_dataset(asset.href, consolidated=True, **kw)
    lat, lon = ds["lat"].values, ds["lon"].values
    ii = np.where((lat >= aoi["south"] - 0.03) & (lat <= aoi["north"] + 0.03))[0]
    jj = np.where((lon >= aoi["west"] - 0.03) & (lon <= aoi["east"] + 0.03))[0]
    sub = ds[["ppt", "swe", "tmax", "tmin"]].isel(lat=slice(ii.min(), ii.max() + 1), lon=slice(jj.min(), jj.max() + 1)).load()
    sl, so = sub["lat"].values, sub["lon"].values
    dlat = abs(float(sl[1] - sl[0])) if len(sl) > 1 else 1 / 24
    dlon = abs(float(so[1] - so[0])) if len(so) > 1 else 1 / 24
    # DEM mean per TerraClimate cell on the cell grid (north-up)
    top = float(sl.max()) + dlat / 2
    left = float(so.min()) - dlon / 2
    tr = from_origin(left, top, dlon, dlat)
    elev_grid, _ = dem_on_grid(aoi, "EPSG:4326", tr, (len(sl), len(so)), CFG["dem_collection"])
    if sl[0] < sl[-1]:  # data are south-up: flip DEM to match array order
        elev_grid = elev_grid[::-1, :]
    bands = assign_bands(elev_grid, CFG["bands_m"])
    rows = []
    times = pd.to_datetime(sub["time"].values)
    for b in range(1, len(CFG["bands_m"]) + 1):
        m = bands == b
        if not m.any():
            continue
        for v in ("ppt", "swe", "tmax", "tmin"):
            arr = sub[v].values  # time, lat, lon
            vals = np.nanmean(np.where(m[None, :, :], arr, np.nan), axis=(1, 2))
            for t, x in zip(times, vals):
                rows.append((t.year, t.month, b, v, float(x), int(m.sum())))
    df = pd.DataFrame(rows, columns=["year", "month", "band", "var", "value", "cells"])
    df = df.pivot_table(index=["year", "month", "band", "cells"], columns="var", values="value").reset_index()
    df.rename(columns={"ppt": "precip_mm", "swe": "swe_mm", "tmax": "tmax_c", "tmin": "tmin_c"}, inplace=True)
    df.to_csv(os.path.join(out, "terraclimate_monthly_by_band.csv"), index=False)
    print("terraclimate rows:", len(df), "years:", df["year"].min(), df["year"].max(), flush=True)


if __name__ == "__main__":
    main()
