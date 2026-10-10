"""Satellite catalogue discovery (Sentinel-1/2, Landsat C2) and QA-masked NDVI previews. KazEOSat is manual/licensed."""
from __future__ import annotations
import numpy as np
from rasterio.warp import Resampling
from . import common as C
from . import sources as S

CDSE = "https://stac.dataspace.copernicus.eu/v1"


def _scale_offset(asset, default_scale, default_offset):
    rb = (asset.extra_fields or {}).get("raster:bands")
    if rb and isinstance(rb, list) and rb:
        return float(rb[0].get("scale", default_scale)), float(rb[0].get("offset", default_offset))
    return default_scale, default_offset


def discover(client, site, bbox, dates, outdir, max_items=40):
    """Catalogue Sentinel-2 L2A, Landsat C2 L2, Sentinel-1 GRD/RTC on Planetary Computer. Returns {collection: items}."""
    found = {}
    for coll in ("sentinel-2-l2a", "landsat-c2-l2", "sentinel-1-grd", "sentinel-1-rtc"):
        try:
            items = S.pc_search(client, coll, bbox, max_items=max_items, datetime=dates)
            if coll in ("sentinel-2-l2a", "landsat-c2-l2"):
                items.sort(key=lambda v: v.properties.get("eo:cloud_cover") if isinstance(v.properties.get("eo:cloud_cover"), (int, float)) else 1e3)
            rows = [{"id": x.id, "datetime": str(x.datetime), "cloud_cover": x.properties.get("eo:cloud_cover"),
                     "platform": x.properties.get("platform"), "bbox": x.bbox, "assets": list(x.assets)[:40]} for x in items]
            C.write_json(outdir / "catalog" / f"{coll}.json", rows)
            C.log(site, coll, "FOUND" if items else "NO_ITEMS", f"{dates}", len(items))
            found[coll] = items
        except Exception as e:  # noqa: BLE001
            C.log_exc(site, coll, e, "SEARCH_FAILED")
            found[coll] = []
    # independent cross-check of Sentinel-2 availability in Copernicus Data Space
    try:
        j = C.http_json(f"{CDSE}/collections/sentinel-2-l2a/items", params={"bbox": ",".join(f"{v:.5f}" for v in bbox), "limit": 5,
                                                                              "datetime": dates.replace("/", "/") if "/" in dates else None})
        feats = j.get("features", [])
        C.write_json(outdir / "catalog" / "cdse_sentinel_2_crosscheck.json",
                     [{"id": z.get("id"), "datetime": z.get("properties", {}).get("datetime"),
                       "cloud": z.get("properties", {}).get("eo:cloud_cover")} for z in feats])
        C.log(site, "CDSE-S2", "FOUND" if feats else "NO_ITEMS", "independent catalogue cross-check", len(feats))
    except Exception as e:  # noqa: BLE001
        C.log_exc(site, "CDSE-S2", e, "SEARCH_FAILED")
    return found


def ndvi_previews(site, found, grid, outdir, snow_ok=False):
    """QA-masked NDVI from the least-cloudy S2 and Landsat scene; diagnostic only."""
    res = []
    for coll in ("sentinel-2-l2a", "landsat-c2-l2"):
        its = found.get(coll, [])
        for it in its[:3]:
            try:
                if coll == "sentinel-2-l2a":
                    rk, nk, qk = "B04", "B08", "SCL"
                    d_scale = (1e-4, 0.0)
                else:
                    rk, nk, qk = "red", "nir08", "qa_pixel"
                    d_scale = (2.75e-5, -0.2)
                if any(k not in it.assets for k in (rk, nk, qk)):
                    continue
                red, _, f1 = S.mosaic([it.assets[rk].href], grid, Resampling.bilinear)
                nir, _, f2 = S.mosaic([it.assets[nk].href], grid, Resampling.bilinear)
                qa, _, f3 = S.mosaic([it.assets[qk].href], grid, Resampling.nearest)
                if f1 or f2 or f3:
                    raise RuntimeError((f1 + f2 + f3)[0])
                sr, so = _scale_offset(it.assets[rk], *d_scale)
                nr, no = _scale_offset(it.assets[nk], *d_scale)
                r = red * sr + so
                n = nir * nr + no
                with np.errstate(all="ignore"):
                    ndvi = (n - r) / (n + r)
                if coll == "sentinel-2-l2a":
                    bad = np.isin(qa, [0, 1, 3, 8, 9, 10] + ([] if snow_ok else [11]))
                else:
                    q = np.nan_to_num(qa, nan=0).astype("int64")
                    bad = ((q >> 1) & 1) | ((q >> 2) & 1) | ((q >> 3) & 1) | ((q >> 4) & 1) | (0 if snow_ok else ((q >> 5) & 1))
                    bad = bad.astype(bool)
                ndvi = np.where(~bad & np.isfinite(ndvi) & (np.abs(n + r) > 1e-4) & (ndvi >= -1) & (ndvi <= 1), ndvi, np.nan)
                nv = int(np.isfinite(ndvi).sum())
                if nv < 100:
                    C.log(site, coll, "NDVI_TOO_FEW_CLEAR_PIXELS", f"{it.id}: {nv}")
                    continue
                S.save_tif(outdir / "rasters" / f"{coll}_{it.id}_ndvi_masked.tif", ndvi, grid, descr="NDVI, cloud/shadow/snow-masked via SCL/QA_PIXEL; diagnostic")
                C.log(site, coll, "NDVI_READY", f"{it.id}: {nv} clear px, cloud(scene)={it.properties.get('eo:cloud_cover')}")
                res.append({"collection": coll, "id": it.id, "datetime": str(it.datetime), "clear_pixels": nv,
                            "ndvi_median": float(np.nanmedian(ndvi)), "ndvi_p10": float(np.nanpercentile(ndvi, 10)),
                            "ndvi_p90": float(np.nanpercentile(ndvi, 90))})
                break
            except Exception as e:  # noqa: BLE001
                C.log_exc(site, coll, e, "NDVI_FAILED")
    return res


def kazeosat_probe(client):
    """KazEOSat-1/2 imagery is licensed through Kazakhstan Gharysh Sapary / Kazakhstan Garysh Sapary (manual request)."""
    rows = []
    try:
        for c in client.get_collections():
            blob = f"{c.id} {c.title} {c.description}".lower()
            if any(k in blob for k in ("kazeo", "kazakh", "kazsat")):
                rows.append({"catalogue": "planetary-computer", "id": c.id, "title": c.title})
    except Exception as e:  # noqa: BLE001
        rows.append({"catalogue": "planetary-computer", "error": repr(e)})
    try:
        j = C.http_json(f"{CDSE}/collections", params={"limit": 200})
        for c in j.get("collections", []):
            blob = f"{c.get('id')} {c.get('title')} {c.get('description')}".lower()
            if any(k in blob for k in ("kazeo", "kazakh", "kazsat")):
                rows.append({"catalogue": "cdse", "id": c.get("id"), "title": c.get("title")})
    except Exception as e:  # noqa: BLE001
        rows.append({"catalogue": "cdse", "error": repr(e)})
    hits = [r for r in rows if "error" not in r]
    C.log("all", "KazEOSat-1/2", "MANUAL_LICENSE_REQUIRED" if not hits else "CATALOGUE_HIT",
          "no public anonymous catalogue of KazEOSat scenes found; official request draft in KAZEOSAT_REQUEST_RU.md" if not hits else str(hits)[:400])
    return rows
