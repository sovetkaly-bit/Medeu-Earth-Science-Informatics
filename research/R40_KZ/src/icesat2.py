"""R40 stage E1/E2 - ICESat-2 ATL08 as a partial independent reference for slope-threshold decisions.

extract : stream ATL08 v007 granules (HTTP range reads, no bulk download) for each study area -> CSV of terrain segments
analyze : sample global DEMs (and, where available, the lidar reference DTM) at the segments; elevation error,
          along-track slope error, directional class agreement, risk-coverage of the distance rule.

Method notes (see docs/ICESAT2_METHOD.md):
* ATL08 heights are ellipsoidal -> only de-biased (median-removed) elevation statistics are reported; slope uses height differences.
* ATL08 segments are ~100 m long: slope is the ALONG-TRACK component between adjacent segments (80-120 m apart). DEM and
  reference are sampled on the same 100 m support (3x3 cell mean) and the same direction. It is a lower bound of full slope.
* The procedure is first run on Switzerland/USA where the lidar DTM is known, to measure ICESat-2's own error as a reference.
Token: environment EARTHDATA_TOKEN only; never printed or written.
"""
from __future__ import annotations
import argparse, json, math, os, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from . import common as C

ROOT = Path(__file__).resolve().parents[1]
FILL = 1e30
T_START, T_END = "2018-10-01", "2026-10-10"
FIELDS = {  # column -> (relative path within beam group)
    "h_te": "land_segments/terrain/h_te_best_fit", "h_te_unc": "land_segments/terrain/h_te_uncertainty",
    "n_te_ph": "land_segments/terrain/n_te_photons", "terrain_slope": "land_segments/terrain/terrain_slope",
    "h_canopy": "land_segments/canopy/h_canopy", "night": "land_segments/night_flag", "cloud": "land_segments/cloud_flag_atm",
    "landcover": "land_segments/segment_landcover", "snow": "land_segments/segment_snowcover", "msw": "land_segments/msw_flag",
    "solar_elev": "land_segments/solar_elevation", "dt": "land_segments/delta_time"}


def study_areas(cfg):
    a = {"kz_all": (76.85, 43.05, 77.20, 43.25)}
    for k, s in cfg["validation"].items():
        lon, lat = s["center"]
        r = s["window_radius_km"] + 1.0
        dy, dx = r / 111.19, r / (111.19 * math.cos(math.radians(lat)))
        a[k] = (lon - dx, lat - dy, lon + dx, lat + dy)
    return a


def _read_granule(g, site, bbox, retries=3):
    import earthaccess, h5py
    last = None
    for attempt in range(retries):
        try:
            f = earthaccess.open([g])[0]
            h = h5py.File(f, "r")
            name = g["umm"]["GranuleUR"]
            rows = []
            for beam in [k for k in h if k.startswith("gt")]:
                lat = h[f"{beam}/land_segments/latitude"][:]
                lon = h[f"{beam}/land_segments/longitude"][:]
                m = (lon >= bbox[0]) & (lon <= bbox[2]) & (lat >= bbox[1]) & (lat <= bbox[3])
                if not m.any():
                    continue
                idx = np.nonzero(m)[0]
                i0, i1 = int(idx.min()), int(idx.max()) + 1
                data = {"lat": lat[i0:i1], "lon": lon[i0:i1]}
                sel = m[i0:i1]
                for col, rel in FIELDS.items():
                    p = f"{beam}/{rel}"
                    data[col] = h[p][i0:i1] if p in h else np.full(i1 - i0, np.nan)
                for j in np.nonzero(sel)[0]:
                    rows.append({"site": site, "granule": name, "beam": beam, "lat": float(data["lat"][j]), "lon": float(data["lon"][j]),
                                 **{c: float(data[c][j]) for c in FIELDS}})
            h.close()
            return rows
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (attempt + 1))
    C.log(site, "ATL08-granule", "GRANULE_FAILED", f"{g['umm'].get('GranuleUR')}: {last!r}"[:300])
    return []


def extract(cfg, out, workers=6, only=None):
    import earthaccess
    earthaccess.login(strategy="environment")
    d = out / "icesat2"
    d.mkdir(parents=True, exist_ok=True)
    summary = []
    for site, bbox in study_areas(cfg).items():
        if only and site not in only:
            continue
        t0 = time.time()
        res = earthaccess.search_data(short_name="ATL08", version="007", bounding_box=bbox, temporal=(T_START, T_END))
        mb = sum(float((r.get("size") or 0)) for r in res)
        C.log(site, "ATL08-search", "FOUND", f"{len(res)} granules, {mb / 1024:.1f} GB if downloaded in full", len(res))
        rows = []
        with ThreadPoolExecutor(workers) as ex:
            for part in ex.map(lambda g: _read_granule(g, site, bbox), res):
                rows += part
        if rows:
            C.write_csv(d / f"atl08_{site}.csv", rows)
        summary.append({"site": site, "bbox_WSEN": bbox, "granules": len(res), "segments_in_bbox": len(rows), "seconds": round(time.time() - t0)})
        C.log(site, "ATL08-extract", "EXTRACTED" if rows else "NO_SEGMENTS", f"{len(rows)} segments in {time.time() - t0:.0f}s", len(rows))
    C.write_json(d / "extract_summary.json", summary)


# ------------------------------------------------------------------------------------------- analysis
def load_points(path):
    import csv
    with open(path, encoding="utf-8") as f:
        r = list(csv.DictReader(f))
    cols = {k: np.array([float(x["" + k]) if x[k] not in ("", "nan") else np.nan for x in r]) for k in r[0] if k not in ("site", "granule", "beam")}
    cols["granule"] = np.array([x["granule"] for x in r])
    cols["beam"] = np.array([x["beam"] for x in r])
    return cols


def quality_mask(p, night_only=False):
    ok = (p["h_te"] < FILL) & (p["h_te_unc"] < FILL) & np.isfinite(p["h_te"]) & (p["n_te_ph"] >= 30) & (p["h_te_unc"] < 5.0)
    ok &= (~np.isfinite(p["cloud"])) | (p["cloud"] <= 2)
    if night_only:
        ok &= p["night"] == 1
    return ok


def smooth100(z):
    """3x3 NaN-aware mean (~90 m support, comparable to the 100 m ATL08 segment)."""
    from scipy import ndimage as ndi
    v = np.isfinite(z)
    s = ndi.uniform_filter(np.where(v, z, 0.0), 3, mode="constant")
    n = ndi.uniform_filter(v.astype("float64"), 3, mode="constant")
    return np.where(n > 0.999, s / np.maximum(n, 1e-12), np.nan)


def sample(z, grid, x, y):
    from scipy import ndimage as ndi
    col = (x - grid.x0) / grid.res - 0.5
    row = (grid.y1 - y) / grid.res - 0.5
    inside = (col >= 0) & (row >= 0) & (col <= grid.w - 1) & (row <= grid.h - 1)
    out = np.full(len(x), np.nan)
    if inside.any():
        out[inside] = ndi.map_coordinates(z, [row[inside], col[inside]], order=1, mode="nearest", cval=np.nan)
    return out


def track_pairs(p, x, y):
    """Indices (i, i+1) of consecutive segments of the same beam/granule 80-120 m apart."""
    order = np.lexsort((p["dt"], p["beam"], p["granule"]))
    a, b = order[:-1], order[1:]
    same = (p["granule"][a] == p["granule"][b]) & (p["beam"][a] == p["beam"][b])
    d = np.hypot(x[b] - x[a], y[b] - y[a])
    ok = same & (d >= 80) & (d <= 120)
    return a[ok], b[ok], d[ok]


def nmad(v):
    return float(1.4826 * np.median(np.abs(v - np.median(v)))) if len(v) else np.nan


def aurc_from(u, err, rng):
    o = np.lexsort((rng.random(len(u)), u))
    return float((np.cumsum(err[o]) / np.arange(1, len(o) + 1)).mean())


def analyze(cfg, out, sites=None):
    from pyproj import Transformer
    from . import sources as S
    from . import terrain as T
    client = S.pc_client()
    d = out / "icesat2"
    areas = study_areas(cfg)
    ths = cfg["thresholds_deg"]
    elev_rows, slope_rows, rc_rows, cnt_rows, pts_out = [], [], [], [], []
    rng = np.random.default_rng(0)
    for site, bbox in areas.items():
        if sites and site not in sites:
            continue
        f = d / f"atl08_{site}.csv"
        if not f.exists():
            C.log(site, "ICESat2-analyze", "NO_POINTS_FILE")
            continue
        try:
            p = load_points(f)
            n_all = len(p["lat"])
            qm = quality_mask(p)
            cnt_rows.append({"site": site, "segments": n_all, "after_quality_filter": int(qm.sum()),
                             "night_only": int(quality_mask(p, True).sum())})
            q = {k: v[qm] for k, v in p.items()}
            lon0, lat0 = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
            epsg = C.utm_epsg(lon0, lat0)
            grid = S.make_grid(bbox, epsg, 30.0, max_side_km=45.0)
            dems, prov = S.fetch_pc_dems(client, site, bbox, grid)
            if site == "kz_all" and cfg.get("enable_fabdem"):
                fz, _ = S.fetch_fabdem(site, lon0, lat0, grid)
                if fz is not None:
                    dems["fabdem"] = fz
            ref = None
            vcfg = cfg["validation"].get(site)
            if vcfg:
                rf = float(vcfg["ref_res_m"])
                gf = grid.fine(rf)
                rz, _ = S.fetch_swissalti3d(site, bbox, gf) if vcfg["reference"] == "swissalti3d" else S.fetch_3dep(client, site, bbox, gf)
                if rz is not None:
                    ref = T.block_mean(rz.astype("float32"), int(round(30 / rf)))
            if ref is not None:
                dems["lidar_reference_dtm"] = ref
            tr = Transformer.from_crs(4326, epsg, always_xy=True)
            x, y = tr.transform(q["lon"], q["lat"])
            ia, ib, dist = track_pairs(q, x, y)
            zs = {k: sample(smooth100(v.astype("float64")), grid, x, y) for k, v in dems.items()}
            h = q["h_te"]
            for k, z in zs.items():
                m = np.isfinite(z) & np.isfinite(h)
                if m.sum() < 30:
                    continue
                dz = (z - h)[m]
                elev_rows.append({"site": site, "dem": k, "n": int(m.sum()), "offset_median_m_incl_datum": float(np.median(dz)),
                                  "NMAD_m": nmad(dz), "RMSE_debiased_m": float(np.sqrt(np.mean((dz - np.median(dz)) ** 2))),
                                  "p95_abs_debiased_m": float(np.percentile(np.abs(dz - np.median(dz)), 95))})
            s_atl = np.degrees(np.arctan((h[ib] - h[ia]) / dist))
            for k, z in zs.items():
                s_d = np.degrees(np.arctan((z[ib] - z[ia]) / dist))
                m = np.isfinite(s_d) & np.isfinite(s_atl)
                if m.sum() < 30:
                    continue
                e = np.abs(s_d[m]) - np.abs(s_atl[m])
                row = {"site": site, "dem": k, "n_pairs": int(m.sum()), "abs_slope_bias_deg": float(e.mean()), "abs_slope_MAE_deg": float(np.abs(e).mean()),
                       "abs_slope_RMSE_deg": float(np.sqrt((e ** 2).mean())), "abs_slope_NMAD_deg": nmad(e)}
                for t in ths:
                    cd, ca = np.abs(s_d[m]) >= t, np.abs(s_atl[m]) >= t
                    row[f"class_disagreement_pct_t{t}"] = float(100 * np.mean(cd != ca))
                    err = (cd != ca).astype(float)
                    u = -np.abs(np.abs(s_d[m]) - t)
                    blocks = (np.arange(m.sum()) // 10)
                    row[f"AURC_distance_rule_t{t}"] = aurc_from(u, err, rng)
                    row[f"error_full_cov_t{t}"] = float(err.mean())
                    o = np.lexsort((rng.random(len(u)), u))
                    risk = np.cumsum(err[o]) / np.arange(1, len(o) + 1)
                    for c in (0.9, 0.7):
                        row[f"risk@{c}_t{t}"] = float(risk[int(np.ceil(c * len(risk))) - 1])
                slope_rows.append(row)
            pts_out.append({"site": site, "n_pairs": int(len(ia)), "median_spacing_m": float(np.median(dist)) if len(dist) else None})
            C.log(site, "ICESat2-analyze", "ANALYZED", f"{len(h)} pts, {len(ia)} track pairs, DEMs={sorted(zs)}")
        except Exception as e:  # noqa: BLE001
            C.log_exc(site, "ICESat2-analyze", e)
    o = out / "tables"
    C.write_csv(o / "icesat2_counts.csv", cnt_rows)
    C.write_csv(o / "icesat2_elevation_vs_dem.csv", elev_rows)
    C.write_csv(o / "icesat2_alongtrack_slope_vs_dem.csv", slope_rows)
    C.write_json(o / "icesat2_pairs_summary.json", pts_out)
    return elev_rows, slope_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["extract", "analyze", "all"], default="all")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    only = [s for s in a.only.split(",") if s] or None
    out = C.OUT
    out.mkdir(parents=True, exist_ok=True)
    if a.stage in ("extract", "all"):
        extract(cfg, out, only=only)
    if a.stage in ("analyze", "all"):
        analyze(cfg, out, sites=only)
    C.write_csv(out / "icesat2_run_status.csv", C.AUDIT, ["time", "site", "source", "status", "details", "count"])
    C.write_json(out / "icesat2_errors.json", C.ERRORS)
    print("DONE-ICESAT2")


if __name__ == "__main__":
    main()
