"""Raster/DEM acquisition on a common metric grid (Planetary Computer STAC, swisstopo STAC, FABDEM attempt)."""
from __future__ import annotations
import math
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling
from pyproj import Transformer
from . import common as C

PC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
SWISS_STAC = "https://data.geo.admin.ch/api/stac/v0.9"
GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2",
                CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF,.tiff,.zip", VSI_CACHE="TRUE", GDAL_HTTP_TIMEOUT="60")


class Grid:
    def __init__(self, epsg, x0, y1, w, h, res):
        self.epsg, self.crs = epsg, f"EPSG:{epsg}"
        self.x0, self.y1, self.w, self.h, self.res = x0, y1, w, h, res
        self.transform = from_origin(x0, y1, res, res)
        self.shape = (h, w)

    def fine(self, rf):
        k = int(round(self.res / rf))
        return Grid(self.epsg, self.x0, self.y1, self.w * k, self.h * k, rf)

    def bounds(self):
        return (self.x0, self.y1 - self.h * self.res, self.x0 + self.w * self.res, self.y1)

    def to_dict(self):
        return dict(crs=self.crs, x0=self.x0, y1=self.y1, width=self.w, height=self.h, res_m=self.res)


def make_grid(bbox_wgs84, epsg, res=30.0, multiple=6, max_side_km=14.0):
    tr = Transformer.from_crs(4326, epsg, always_xy=True)
    w, s, e, n = bbox_wgs84
    xs, ys = zip(*[tr.transform(x, y) for x in (w, e) for y in (s, n)])
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    half = max_side_km * 500
    x0, x1 = max(x0, cx - half), min(x1, cx + half)
    y0, y1 = max(y0, cy - half), min(y1, cy + half)
    x0 = math.floor(x0 / res) * res
    y1 = math.ceil(y1 / res) * res
    W = math.ceil((x1 - x0) / res)
    H = math.ceil((y1 - y0 + 0.0) / res)
    W = int(math.ceil(W / multiple) * multiple)
    H = int(math.ceil(H / multiple) * multiple)
    return Grid(epsg, x0, y1, W, H, res)


def bbox_wgs84_of(geom_wgs84, buffer_deg=0.0):
    w, s, e, n = geom_wgs84.bounds
    return (w - buffer_deg, s - buffer_deg, e + buffer_deg, n + buffer_deg)


def pc_client():
    from pystac_client import Client
    import planetary_computer as pc
    return Client.open(PC_URL, modifier=pc.sign_inplace)


def clean_href(h):
    return h.split("?")[0]


def pc_search(client, collection, bbox, max_items=40, **kw):
    s = client.search(collections=[collection], bbox=list(bbox), max_items=max_items, **kw)
    return list(s.items())


def collection_info(client, name):
    try:
        c = client.get_collection(name)
        return {"id": c.id, "title": c.title, "license": c.license, "description": (c.description or "")[:1200],
                "extra": {k: (v if not isinstance(v, (dict, list)) else str(v)[:400]) for k, v in c.extra_fields.items()
                          if k in ("msft:short_description", "sci:citation", "sci:doi", "deprecated")},
                "providers": [p.name for p in (c.providers or [])]}
    except Exception as e:  # noqa: BLE001
        return {"error": repr(e)}


def mosaic(hrefs, grid: Grid, resampling=Resampling.bilinear, site="", source="", nodata_override=None):
    """Reproject several (tile) rasters onto `grid`; first valid pixel wins. Returns (array, n_ok, failures)."""
    dst = np.full(grid.shape, np.nan, dtype="float32")
    ok, fails = 0, []
    with rasterio.Env(**GDAL_ENV):
        for h in hrefs:
            try:
                with rasterio.open(h) as src:
                    reproject(source=rasterio.band(src, 1), destination=dst, src_crs=src.crs, src_transform=src.transform,
                              src_nodata=nodata_override if nodata_override is not None else src.nodata,
                              dst_transform=grid.transform, dst_crs=grid.crs, dst_nodata=np.nan,
                              resampling=resampling, init_dest_nodata=False)
                ok += 1
            except Exception as e:  # noqa: BLE001
                fails.append(f"{clean_href(h)[-90:]}: {e!r}"[:300])
    return dst, ok, fails


def save_tif(path, arr, grid: Grid, nodata=np.nan, dtype="float32", descr=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1, dtype=dtype,
                       crs=grid.crs, transform=grid.transform, nodata=nodata, compress="deflate", predictor=3 if dtype == "float32" else 1) as o:
        o.write(arr.astype(dtype), 1)
        if descr:
            o.set_band_description(1, descr)


# ------------------------------------------------------------------------ global DEMs (Planetary Computer)
PC_DEMS = {
    "cop-dem-glo-30": {"asset": "data", "label": "Copernicus GLO-30 (DSM, EGM2008)", "datum": "EGM2008 orthometric", "license": "Copernicus (free, attribution)", "publish_raster": True},
    "nasadem": {"asset": "elevation", "label": "NASADEM (SRTM reprocessed, DSM)", "datum": "EGM96 orthometric", "license": "NASA public domain", "publish_raster": True},
    "alos-dem": {"asset": "data", "label": "ALOS World 3D 30 m (PC 'alos-dem', see metadata)", "datum": "EGM96 orthometric", "license": "JAXA AW3D30 terms (citation required)", "publish_raster": False},
}


def fetch_pc_dems(client, site, bbox, grid, which=None):
    """Return {name: array}, provenance dict."""
    out, prov = {}, {}
    for coll, meta in PC_DEMS.items():
        if which and coll not in which:
            continue
        try:
            items = pc_search(client, coll, bbox, max_items=12)
            if not items:
                C.log(site, coll, "NO_ITEMS", "")
                prov[coll] = {"status": "NO_ITEMS"}
                continue
            hrefs = [it.assets[meta["asset"]].href for it in items if meta["asset"] in it.assets]
            arr, ok, fails = mosaic(hrefs, grid, Resampling.bilinear, site, coll)
            n = int(np.isfinite(arr).sum())
            prov[coll] = {"status": "OK" if n > 100 else "INSUFFICIENT_COVERAGE", "items": [it.id for it in items],
                          "hrefs": [clean_href(h) for h in hrefs], "tiles_read": ok, "failures": fails, "valid_pixels": n,
                          "datetimes": [str(it.datetime) for it in items], "meta": meta, "collection": collection_info(client, coll),
                          "resampling": "bilinear to 30 m UTM grid (cell centres)"}
            if n > 100:
                out[coll] = arr
                C.log(site, coll, "RASTER_READY", f"{n} valid px from {ok}/{len(hrefs)} tiles")
            else:
                C.log(site, coll, "RASTER_FAILED", f"valid={n}; {fails[:1]}")
        except Exception as e:  # noqa: BLE001
            C.log_exc(site, coll, e, "RASTER_FAILED")
            prov[coll] = {"status": "FAILED", "error": repr(e)}
    return out, prov


# ------------------------------------------------------------------------ reference DTMs
def fetch_3dep(client, site, bbox, grid_fine):
    """USGS 3DEP 1/3 arc-second (~10 m) seamless bare-earth DEM via Planetary Computer."""
    try:
        items = pc_search(client, "3dep-seamless", bbox, max_items=60)
        it10 = [i for i in items if float(i.properties.get("gsd", 0)) == 10.0]
        info = {"collection": collection_info(client, "3dep-seamless"), "n_items_all": len(items), "n_items_10m": len(it10)}
        if not it10:
            info["status"] = "NO_10M_ITEMS"
            C.log(site, "3dep-seamless", "NO_ITEMS", f"{len(items)} items, none gsd=10")
            return None, info
        hrefs = [i.assets["data"].href for i in it10 if "data" in i.assets]
        arr, ok, fails = mosaic(hrefs, grid_fine, Resampling.bilinear, site, "3dep")
        n = int(np.isfinite(arr).sum())
        info.update({"status": "OK" if n > 100 else "INSUFFICIENT", "items": [i.id for i in it10], "hrefs": [clean_href(h) for h in hrefs],
                     "failures": fails, "valid_pixels": n, "datum": "NAVD88 (heights), source lidar-derived bare earth where available",
                     "license": "USGS public domain", "resampling": "bilinear to fine UTM grid"})
        C.log(site, "3dep-seamless", "REFERENCE_READY" if n > 100 else "RASTER_FAILED", f"{n} px")
        return (arr if n > 100 else None), info
    except Exception as e:  # noqa: BLE001
        C.log_exc(site, "3dep-seamless", e, "RASTER_FAILED")
        return None, {"status": "FAILED", "error": repr(e)}


def swiss_items(bbox):
    w, s, e, n = bbox
    items, url = [], f"{SWISS_STAC}/collections/ch.swisstopo.swissalti3d/items"
    params = {"bbox": f"{w},{s},{e},{n}", "limit": 100}
    for _ in range(20):
        j = C.http_json(url, params=params, timeout=90)
        items += j.get("features", [])
        nxt = next((l["href"] for l in j.get("links", []) if l.get("rel") == "next"), None)
        if not nxt or not j.get("features"):
            break
        url, params = nxt, None
    return items


def fetch_swissalti3d(site, bbox, grid_fine):
    """swissALTI3D 2 m DTM (bare earth, LV95 / LN02), one tile per km, newest release per tile."""
    try:
        feats = swiss_items(bbox)
        best = {}
        for f in feats:
            tile = f["id"].rsplit("_", 1)[-1]
            year = int(f["id"].split("_")[1]) if f["id"].split("_")[1].isdigit() else 0
            if tile not in best or year > best[tile][0]:
                best[tile] = (year, f)
        hrefs, ids = [], []
        for tile, (year, f) in best.items():
            for k, a in f.get("assets", {}).items():
                if "_2_2056_" in k and a.get("href"):
                    hrefs.append(a["href"]); ids.append(f["id"]); break
        info = {"n_items": len(feats), "n_tiles": len(best), "n_2m_assets": len(hrefs), "datum": "LN02 (Swiss levelling), CRS EPSG:2056",
                "license": "swisstopo OGD (free, attribution: Swiss Federal Office of Topography swisstopo)",
                "catalog": SWISS_STAC + "/collections/ch.swisstopo.swissalti3d", "items": ids[:400], "hrefs": hrefs[:400]}
        if not hrefs:
            info["status"] = "NO_2M_ASSETS"
            C.log(site, "swissALTI3D", "NO_ITEMS", f"{len(feats)} features")
            return None, info
        arr, ok, fails = mosaic(hrefs, grid_fine, Resampling.bilinear, site, "swissalti3d")
        n = int(np.isfinite(arr).sum())
        info.update({"status": "OK" if n > 100 else "INSUFFICIENT", "tiles_read": ok, "failures": fails[:20], "valid_pixels": n,
                     "resampling": "bilinear to fine UTM grid (2 m)"})
        C.log(site, "swissALTI3D", "REFERENCE_READY" if n > 100 else "RASTER_FAILED", f"{n} px, {ok}/{len(hrefs)} tiles")
        return (arr if n > 100 else None), info
    except Exception as e:  # noqa: BLE001
        C.log_exc(site, "swissALTI3D", e, "RASTER_FAILED")
        return None, {"status": "FAILED", "error": repr(e)}


def fetch_fabdem(site, lon, lat, grid):
    """FABDEM V1-2 (forest/building-corrected Copernicus DEM; CC BY-NC-SA 4.0) via GDAL /vsizip/ range reads. Optional."""
    try:
        y0, x0 = int(math.floor(lat)), int(math.floor(lon))
        gy, gx = int(math.floor(y0 / 10.0) * 10), int(math.floor(x0 / 10.0) * 10)

        def tag(y, x):
            return f"{'N' if y >= 0 else 'S'}{abs(y):02d}{'E' if x >= 0 else 'W'}{abs(x):03d}"
        pack = f"{tag(gy, gx)}-{tag(gy + 10, gx + 10)}_FABDEM_V1-2.zip"
        base = f"https://data.bris.ac.uk/datasets/s5hqmjcdj8yo2ibzi9b4ew3sn/{pack}"
        member = f"{tag(y0, x0)}_FABDEM_V1-2.tif"
        vsi = f"/vsizip//vsicurl/{base}/{member}"
        arr, ok, fails = mosaic([vsi], grid, Resampling.bilinear, site, "fabdem")
        n = int(np.isfinite(arr).sum())
        info = {"status": "OK" if n > 100 else "FAILED", "url": base, "member": member, "failures": fails, "valid_pixels": n,
                "license": "CC BY-NC-SA 4.0 (Hawker et al. 2022) - raster NOT redistributed here", "datum": "EGM2008"}
        C.log(site, "FABDEM", "RASTER_READY" if n > 100 else "RASTER_FAILED", f"{n} px {fails[:1]}")
        return (arr if n > 100 else None), info
    except Exception as e:  # noqa: BLE001
        C.log_exc(site, "FABDEM", e, "RASTER_FAILED")
        return None, {"status": "FAILED", "error": repr(e)}
