"""MODIS Terra MOD10A1 v061 daily snow cover, windowed COG reads from Planetary Computer (anonymous).

Output: out/modis_daily_by_band.csv (date, band, band_px, clear_px, snow_px) + out/modis_items.csv (provenance).
Observations are satellite retrievals; cloud, missing and non-land codes are excluded from the clear count.
"""
import argparse
import collections
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import planetary_computer
import pystac_client
import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

from src.common import assign_bands
from src.dem import dem_on_grid, STAC

CFG = json.load(open(os.path.join(os.path.dirname(__file__), "..", "config.json")))


def parse_id(item):
    """MOD10A1.A2020045.h23v04.061.... -> (sensor, date, tile)."""
    parts = item.id.split(".")
    sensor = parts[0][:3]
    date = (pd.Timestamp(year=int(parts[1][1:5]), month=1, day=1) + pd.Timedelta(days=int(parts[1][5:8]) - 1)).date()
    return sensor, date, parts[2]


def pick_asset_key(item):
    keys = list(item.assets)
    for k in keys:
        if "NDSI_Snow_Cover" in k and not any(t in k for t in ("QA", "Class", "Flags")):
            return k
    raise RuntimeError("NDSI_Snow_Cover asset not found; keys=%s" % keys)


def read_window(item, key, window, retries=3):
    for a in range(retries):
        try:
            signed = planetary_computer.sign(item)
            with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF",
                              GDAL_HTTP_MAX_RETRY="3", GDAL_HTTP_RETRY_DELAY="2"):
                with rasterio.open(signed.assets[key].href) as ds:
                    return ds.read(1, window=window, boundless=False)
        except Exception as e:  # noqa
            err = e
            time.sleep(2 * (a + 1))
    return err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year-from", type=int, default=2000)
    ap.add_argument("--year-to", type=int, default=2026)
    ap.add_argument("--out", default=os.environ.get("ALMATY_OUT", "out"))
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0, help="debug: only the first N items")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    aoi = CFG["aoi"]
    cx, cy = (aoi["west"] + aoi["east"]) / 2, (aoi["south"] + aoi["north"]) / 2

    cat = pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)
    search = cat.search(collections=[CFG["modis"]["collection"]],
                        intersects={"type": "Point", "coordinates": [cx, cy]},
                        datetime="%d-01-01/%d-12-31" % (a.year_from, a.year_to))
    items = list(search.items())
    if not items:
        sys.exit("ERROR: no MOD10A1 items found")
    tiles = collections.Counter(parse_id(i)[2] for i in items)
    sensors = collections.Counter(parse_id(i)[0] for i in items)
    print("items:", len(items), "tiles:", dict(tiles), "sensors:", dict(sensors), flush=True)
    tile = tiles.most_common(1)[0][0]
    items = [i for i in items if parse_id(i)[2] == tile]
    items.sort(key=lambda i: (parse_id(i)[1], parse_id(i)[0]))
    if a.limit:
        items = items[: a.limit]
    key = pick_asset_key(items[0])
    print("asset key:", key, "assets:", list(items[0].assets)[:20], flush=True)

    signed0 = planetary_computer.sign(items[0])
    with rasterio.open(signed0.assets[key].href) as ds:
        crs, tr = ds.crs, ds.transform
        b = transform_bounds("EPSG:4326", crs, aoi["west"], aoi["south"], aoi["east"], aoi["north"])
        win = from_bounds(*b, transform=tr).round_offsets().round_lengths()
        win_tr = ds.window_transform(win)
        shape = (int(win.height), int(win.width))
        print("tile", tile, "crs", crs, "window", win, "shape", shape, "pixel size", tr.a, flush=True)

    elev, dem_ids = dem_on_grid(aoi, crs, win_tr, shape, CFG["dem_collection"])
    bands = assign_bands(elev, CFG["bands_m"])
    nb = len(CFG["bands_m"])
    band_px = {i: int((bands == i).sum()) for i in range(1, nb + 1)}
    print("band pixels:", band_px, "dem tiles:", dem_ids, flush=True)
    pd.DataFrame([{"band": i, "lo_m": CFG["bands_m"][i - 1][0], "hi_m": CFG["bands_m"][i - 1][1], "pixels": band_px[i],
                   "mean_elev_m": float(np.nanmean(elev[bands == i])) if band_px[i] else None} for i in band_px]
                 ).to_csv(os.path.join(a.out, "bands_summary.csv"), index=False)

    thr = CFG["modis"]["snow_ndsi_threshold"]
    prov, failed = [], []
    per_day = collections.defaultdict(dict)  # date -> sensor -> (clear, snow) boolean arrays
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(read_window, it, key, win): it for it in items}
        for n, f in enumerate(as_completed(futs), 1):
            it = futs[f]
            arr = f.result()
            sensor, date, _ = parse_id(it)
            if isinstance(arr, Exception) or arr is None or arr.shape != shape:
                failed.append((it.id, str(arr)[:200]))
                continue
            clear = arr <= 100
            per_day[date][sensor] = (clear, clear & (arr >= thr))
            prov.append((it.id, sensor, date.isoformat()))
            if n % 1000 == 0:
                print("read %d/%d  %.0fs  failed=%d" % (n, len(items), time.time() - t0, len(failed)), flush=True)

    rows = []
    for date, sd in per_day.items():
        variants = dict(sd)
        if len(sd) > 1:  # combined Terra+Aqua: pixel is clear if clear in any overpass, snow if snow in any clear overpass
            variants["COMB"] = (np.logical_or.reduce([v[0] for v in sd.values()]), np.logical_or.reduce([v[1] for v in sd.values()]))
        else:
            variants["COMB"] = list(sd.values())[0]
        for sensor, (clear, snow) in variants.items():
            for i in range(1, nb + 1):
                m = bands == i
                if band_px[i]:
                    rows.append((date.isoformat(), sensor, i, band_px[i], int((clear & m).sum()), int((snow & m).sum())))
    df = pd.DataFrame(rows, columns=["date", "sensor", "band", "band_px", "clear_px", "snow_px"]).sort_values(["date", "sensor", "band"])
    df.to_csv(os.path.join(a.out, "modis_daily_by_band.csv"), index=False)
    pd.DataFrame(prov, columns=["item_id", "sensor", "date"]).sort_values("date").to_csv(os.path.join(a.out, "modis_items.csv"), index=False)
    pd.DataFrame(failed, columns=["item_id", "error"]).to_csv(os.path.join(a.out, "modis_failed.csv"), index=False)
    print("done: days=%d failed=%d" % (df["date"].nunique() if len(df) else 0, len(failed)), flush=True)
    if len(failed) > 0.2 * len(items):
        sys.exit("ERROR: more than 20 percent of reads failed")


if __name__ == "__main__":
    main()
