"""Sentinel-2 L2A multi-year snow / vegetation time series for the Almaty study area (Planetary Computer, free).

Reads every scene at coarse resolution (default 120 m, nearest) for B04, B08 and SCL, aggregates per pixel:
snow frequency, valid-observation count, snow-free summer NDVI. Context layers only: they describe where snow and
vegetation can bias DEM-derived slope; they are NOT terrain-slope validation.
"""
from __future__ import annotations
import argparse, datetime as dt
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.transform import from_origin
from pyproj import Transformer
from . import common as C
from . import sources as S

BBOX = (76.85, 43.05, 77.20, 43.25)
CRS = "EPSG:32643"
SNOW, WATER, VEG, BARE = 11, 6, 4, 5
GOOD = (4, 5, 6, 7, 11)  # SCL classes treated as valid surface (cloud/shadow/cirrus/defective excluded)


def grid(res):
    t = Transformer.from_crs(4326, CRS, always_xy=True)
    x0, y0 = t.transform(BBOX[0], BBOX[1])
    x1, y1 = t.transform(BBOX[2], BBOX[3])
    x0, y0 = np.floor(x0 / res) * res, np.floor(y0 / res) * res
    x1, y1 = np.ceil(x1 / res) * res, np.ceil(y1 / res) * res
    return (x0, y0, x1, y1), int(round((x1 - x0) / res)), int(round((y1 - y0) / res))


class Acc:
    def __init__(self, shape):
        z = lambda dtp: np.zeros(shape, dtp)  # noqa: E731
        self.valid, self.snow = z(np.int32), z(np.int32)
        self.nd_sum, self.nd_n = z(np.float64), z(np.int32)
        self.valid_w, self.snow_w = z(np.int32), z(np.int32)  # winter DJF

    def add(self, scl, red, nir, month):
        good = np.isin(scl, GOOD)
        snow = scl == SNOW
        self.valid += good
        self.snow += good & snow
        if month in (12, 1, 2):
            self.valid_w += good
            self.snow_w += good & snow
        if month in (6, 7, 8):
            m = good & ~snow & (scl != WATER)
            with np.errstate(divide="ignore", invalid="ignore"):
                nd = (nir - red) / (nir + red)
            m &= np.isfinite(nd)
            self.nd_sum += np.where(m, nd, 0)
            self.nd_n += m


def scene_stats(item, bounds, shape):
    """Return (scl, red, nir) arrays on the common grid or None."""
    h, w = shape
    out = {}
    for key, rs in (("SCL", 0), ("B04", 0), ("B08", 0)):
        href = item.assets[key].href
        with rasterio.open(href) as src:
            if str(src.crs).upper() != CRS:
                return None
            win = from_bounds(*bounds, transform=src.transform)
            out[key] = src.read(1, window=win, out_shape=(h, w), boundless=True, fill_value=0, resampling=rasterio.enums.Resampling.nearest)
    return out["SCL"].astype(np.uint8), out["B04"].astype(np.float32) / 1e4 - 0.1, out["B08"].astype(np.float32) / 1e4 - 0.1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2017-04-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--res", type=float, default=120.0)
    ap.add_argument("--max-cloud", type=float, default=80.0)
    ap.add_argument("--max-scenes", type=int, default=1500)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    out = C.OUT
    out.mkdir(parents=True, exist_ok=True)
    bounds, w, h = grid(a.res)
    client = S.pc_client()
    items = S.pc_search(client, "sentinel-2-l2a", BBOX, max_items=a.max_scenes * 2,
                        datetime=f"{a.start}/{a.end}", query={"eo:cloud_cover": {"lt": a.max_cloud}})
    items = [i for i in items if i.properties.get("proj:code", "") in ("EPSG:32643", "") or "32643" in str(i.properties.get("proj:epsg", ""))] or items
    items.sort(key=lambda i: i.datetime)
    items = items[: a.max_scenes]
    print(f"scenes={len(items)} grid={w}x{h} res={a.res}", flush=True)
    acc, rows = Acc((h, w)), []
    t0 = dt.datetime.now()

    def work(it):
        try:
            return it, scene_stats(__import__("planetary_computer").sign(it), bounds, (h, w)), None
        except Exception as e:  # noqa: BLE001
            return it, None, repr(e)[:200]

    with ThreadPoolExecutor(a.workers) as ex:
        for it, res, err in ex.map(work, items):
            d = it.datetime
            row = {"id": it.id, "date": d.date().isoformat(), "cloud": it.properties.get("eo:cloud_cover")}
            if res is None:
                row.update(status="FAILED" if err else "SKIPPED_CRS", error=err or "")
            else:
                scl, red, nir = res
                good = np.isin(scl, GOOD)
                row.update(status="OK", valid_frac=float(good.mean()), snow_frac_of_valid=float((scl == SNOW)[good].mean()) if good.any() else None)
                if good.mean() > 0.2:
                    acc.add(scl, red, nir, d.month)
            rows.append(row)
    C.write_csv(out / "s2_scenes.csv", rows)
    with np.errstate(divide="ignore", invalid="ignore"):
        snowf = np.where(acc.valid > 0, acc.snow / acc.valid, np.nan).astype(np.float32)
        snowf_w = np.where(acc.valid_w > 0, acc.snow_w / acc.valid_w, np.nan).astype(np.float32)
        ndvi = np.where(acc.nd_n > 0, acc.nd_sum / acc.nd_n, np.nan).astype(np.float32)
    tr = from_origin(bounds[0], bounds[3], a.res, a.res)
    for name, arr in (("snow_frequency_all", snowf), ("snow_frequency_DJF", snowf_w), ("ndvi_summer_mean", ndvi),
                      ("valid_obs", acc.valid.astype(np.float32)), ("ndvi_n", acc.nd_n.astype(np.float32))):
        with rasterio.open(out / f"{name}.tif", "w", driver="GTiff", height=h, width=w, count=1, dtype="float32", crs=CRS, transform=tr, nodata=np.nan, compress="deflate") as dst:
            dst.write(arr, 1)
    ok = [r for r in rows if r["status"] == "OK"]
    # monthly snow fraction summary
    by = {}
    for r in ok:
        if r["snow_frac_of_valid"] is not None and r["valid_frac"] > 0.2:
            by.setdefault(r["date"][5:7], []).append(r["snow_frac_of_valid"])
    C.write_json(out / "s2_summary.json", {
        "time": C.now(), "n_scenes_listed": len(items), "n_ok": len(ok), "n_failed": sum(r["status"] == "FAILED" for r in rows),
        "n_skipped_crs": sum(r["status"] == "SKIPPED_CRS" for r in rows),
        "valid_obs_median_per_pixel": float(np.median(acc.valid)), "median_ndvi_summer": float(np.nanmedian(ndvi)),
        "snow_fraction_by_month_median": {m: float(np.median(v)) for m, v in sorted(by.items())},
        "minutes": (dt.datetime.now() - t0).total_seconds() / 60,
        "note": "SCL snow class; context layer only, not slope validation"})
    print("done", flush=True)


if __name__ == "__main__":
    main()
