"""R40 Kazakhstan - single-run orchestration: boundaries -> DEMs/reference -> validation -> application -> report.

Run from research/R40_KZ:  python -m src.run [--site all|medeu|shymbulak|kok_zhailau] [--no-validation] [--no-optical]
Every stage is failure-tolerant: problems are written to run_status.csv / errors.json, never hidden.
"""
from __future__ import annotations
import argparse, json, shutil, sys, time
from pathlib import Path
import numpy as np
from pyproj import Transformer
from shapely.ops import transform as shp_transform
from rasterio.features import rasterize

from . import common as C
from . import terrain as T
from . import decision as D
from . import sources as S
from . import boundaries as B
from . import optical as O
from . import experiment as E
from . import report as R

ROOT = Path(__file__).resolve().parents[1]
DEC_LABELS = {0: "BELOW", 1: "ABOVE", 2: "ABSTAIN"}


def utm_geom(g, epsg):
    return shp_transform(Transformer.from_crs(4326, epsg, always_xy=True).transform, g) if g is not None else None


def mask_of(geom_utm, grid):
    if geom_utm is None or geom_utm.is_empty:
        return None
    m = rasterize([(geom_utm, 1)], out_shape=grid.shape, transform=grid.transform, fill=0, dtype="uint8").astype(bool)
    return m if m.sum() > 0 else None


def window_bbox(s, polys):
    lon, lat = s["center"]
    r = s["window_radius_km"]
    dy = r / 111.19
    dx = r / (111.19 * np.cos(np.radians(lat)))
    w, so, e, n = lon - dx, lat - dy, lon + dx, lat + dy
    for g in polys:
        if g is not None and not g.is_empty:
            gw, gs, ge, gn = g.bounds
            pad = 1.5 / 111.19
            w, so, e, n = min(w, gw - pad), min(so, gs - pad), max(e, ge + pad), max(n, gn + pad)
    return (w, so, e, n)


def grid_bbox_wgs(grid):
    tr = Transformer.from_crs(grid.epsg, 4326, always_xy=True)
    x0, y0, x1, y1 = grid.bounds()
    pts = [tr.transform(x, y) for x in (x0, x1) for y in (y0, y1)]
    xs, ys = zip(*pts)
    return (min(xs) - 0.002, min(ys) - 0.002, max(xs) + 0.002, max(ys) + 0.002)


PUBLISH_RASTER = {"cop-dem-glo-30", "nasadem"}


def acquire(group, key, s, cfg, client, out, args):
    lon, lat = s["center"]
    epsg = C.utm_epsg(lon, lat)
    rec = {"group": group, "key": key, "cfg": s, "epsg": epsg, "z": {}, "boundary_status": "NOT_ATTEMPTED", "territory": None, "footprint": None}
    sdir = out / "sites" / key
    # ---- boundary geometry
    try:
        b = B.fetch_site(key, s)
        rec["territory"], rec["footprint"], rec["boundary_status"] = b["territory"], b["footprint"], b["status"]
        prov = b["prov"]
        if b["territory"] is None and group == "kazakhstan":
            prov["nominatim_fallback"] = B.nominatim_fallback(key, s)
        C.write_json(out / "boundaries" / f"{key}_provenance.json", prov)
        C.write_json(out / "boundaries" / f"{key}_candidates.json", {"candidates": b["candidates"], "named_nodes": b.get("named_nodes", [])})
        items = [{"geom": b["territory"], "props": {"site": key, "kind": "territory_polygon_osm", "status": b["status"], "provenance": "OpenStreetMap (ODbL) via Overpass; see provenance json"}},
                 {"geom": b["footprint"], "props": {"site": key, "kind": "functional_footprint_derived", "note": "derived from mapped aerialway/piste/tourism/leisure features; NOT an official boundary"}}]
        C.write_json(out / "boundaries" / f"{key}.geojson", B.to_geojson(items))
        C.log(key, "boundary", b["status"], f"candidates={b['prov'].get('n_candidates')}, footprint_km2={b['prov'].get('footprint_area_km2')}")
        time.sleep(2)
    except Exception as e:  # noqa: BLE001
        C.log_exc(key, "boundary", e)
    # ---- window and grid
    polys = [rec["territory"], rec["footprint"]] if group == "kazakhstan" else []
    bbox = window_bbox(s, polys)
    grid = S.make_grid(bbox, epsg, cfg["grid_res_m"])
    rec["grid"] = grid
    bb = grid_bbox_wgs(grid)
    C.write_json(sdir / "window.json", {"grid": grid.to_dict(), "bbox_wgs84": bb, "note": "processing window only; NOT a territory boundary"})
    # ---- global DEMs
    prov = {}
    if client is not None:
        z, prov = S.fetch_pc_dems(client, key, bb, grid)
        rec["z"].update(z)
    else:
        C.log(key, "planetary-computer", "CATALOG_UNAVAILABLE", "no client")
    if cfg.get("enable_fabdem") and not args.no_fabdem:
        fz, finfo = S.fetch_fabdem(key, lon, lat, grid)
        prov["fabdem"] = finfo
        if fz is not None:
            rec["z"]["fabdem"] = fz
    # ---- independent reference (validation sites)
    rec["ref_fine"], rec["rf"] = None, None
    if group == "validation":
        rf = float(s["ref_res_m"])
        gf = grid.fine(rf)
        if s["reference"] == "swissalti3d":
            ref, info = S.fetch_swissalti3d(key, bb, gf)
        else:
            ref, info = S.fetch_3dep(client, key, bb, gf) if client is not None else (None, {"status": "NO_CLIENT"})
        prov["reference_dtm"] = info
        if ref is not None:
            rec["ref_fine"], rec["rf"] = ref.astype("float32"), rf
    C.write_json(sdir / "sources_provenance.json", prov)
    # ---- satellite catalogues (Kazakhstan only)
    if group == "kazakhstan" and client is not None and not args.no_optical:
        try:
            found = O.discover(client, key, bb, cfg["optical_dates"], sdir)
            rec["ndvi"] = O.ndvi_previews(key, found, grid, sdir)
            C.write_json(sdir / "ndvi_previews.json", rec["ndvi"])
        except Exception as e:  # noqa: BLE001
            C.log_exc(key, "optical", e)
    return rec


def slope_stats(slope, mask, extra=None):
    m = mask & np.isfinite(slope)
    n = int(m.sum())
    if n == 0:
        return None
    v = slope[m]
    row = {"n_px": n, "area_km2": n * 900 / 1e6, "mean_slope": float(v.mean()), "p95_slope": float(np.percentile(v, 95)),
           "share_lt_7.5": float(100 * np.mean(v < 7.5)), "share_7.5_15": float(100 * np.mean((v >= 7.5) & (v < 15))),
           "share_15_25": float(100 * np.mean((v >= 15) & (v < 25))), "share_ge_25": float(100 * np.mean(v >= 25))}
    row.update(extra or {})
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="all")
    ap.add_argument("--no-validation", action="store_true")
    ap.add_argument("--no-optical", action="store_true")
    ap.add_argument("--no-fabdem", action="store_true")
    args = ap.parse_args()
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    out = C.OUT
    out.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    th = cfg["thresholds_deg"]
    predictors, primary = cfg["predictor_dems"], cfg["primary_dem"]
    head = cfg["decision"]["headline_target_risk"]

    client = None
    try:
        client = S.pc_client()
        C.log("all", "planetary-computer", "CATALOG_OK", S.PC_URL)
    except Exception as e:  # noqa: BLE001
        C.log_exc("all", "planetary-computer", e, "CATALOG_UNAVAILABLE")
    kaz_rows = []
    if client is not None:
        try:
            kaz_rows = O.kazeosat_probe(client)
        except Exception as e:  # noqa: BLE001
            C.log_exc("all", "KazEOSat-probe", e)
    C.write_json(out / "kazeosat_probe.json", kaz_rows)

    data = {}
    plan = [("kazakhstan", k, v) for k, v in cfg["kazakhstan"].items() if args.site in ("all", k)]
    if not args.no_validation:
        plan += [("validation", k, v) for k, v in cfg["validation"].items()]
    for group, key, s in plan:
        t0 = time.time()
        try:
            data[key] = acquire(group, key, s, cfg, client, out, args)
        except Exception as e:  # noqa: BLE001
            C.log_exc(key, "acquire", e)
        C.log(key, "timing", "ACQUIRE_DONE", f"{time.time() - t0:.0f} s")

    # ------------------------------------------------------------- per-site descriptive products
    qc, shares, pair_rows = [], [], []
    for key, d in data.items():
        grid, z = d["grid"], d["z"]
        sdir = out / "sites" / key
        terr_utm, foot_utm = utm_geom(d["territory"], d["epsg"]), utm_geom(d["footprint"], d["epsg"])
        d["terr_utm"], d["foot_utm"] = terr_utm, foot_utm
        masks = {"context": np.ones(grid.shape, bool)}
        if d["group"] == "kazakhstan":
            tm = mask_of(terr_utm, grid)
            fm = mask_of(foot_utm, grid)
            if tm is not None:
                masks["territory_osm_polygon"] = tm
            elif fm is not None:
                masks["functional_footprint_derived"] = fm
        d["masks"] = masks
        slopes = {}
        for name, arr in z.items():
            meta = S.PC_DEMS.get(name, {})
            v = arr[np.isfinite(arr)]
            qc.append({"site": key, "dem": name, "grid_crs": grid.crs, "grid_res_m": grid.res, "shape": f"{grid.h}x{grid.w}",
                       "valid_px": int(v.size), "nodata_pct": float(100 * (1 - v.size / arr.size)), "min_m": float(v.min()) if v.size else None,
                       "max_m": float(v.max()) if v.size else None, "mean_m": float(v.mean()) if v.size else None,
                       "vertical_datum": meta.get("datum", "EGM2008" if name == "fabdem" else "n/a"), "license": meta.get("license", "see provenance"),
                       "native_resolution": "~1 arc-second (≈30 m)", "type": "DSM (surface), not bare-earth DTM" if name != "fabdem" else "DEM with forest/building correction (still modelled, not LiDAR DTM)"})
            s = T.slope_deg(arr, grid.res)
            slopes[name] = s
            for mname, m in masks.items():
                row = slope_stats(s, m, {"site": key, "group": d["group"], "dem": name, "mask": mname})
                if row:
                    shares.append(row)
            if name in PUBLISH_RASTER:
                S.save_tif(sdir / "rasters" / f"{name}_elevation_m.tif", arr, grid, descr=f"{name} elevation, bilinear to 30 m UTM")
                S.save_tif(sdir / "rasters" / f"{name}_slope_deg_horn.tif", s, grid, descr="slope degrees, Horn, 30 m")
        d["slopes"] = slopes
        ks = sorted(slopes)
        for i, a in enumerate(ks):
            for b in ks[i + 1:]:
                for t in th:
                    m = np.isfinite(slopes[a]) & np.isfinite(slopes[b])
                    if m.sum() < 50:
                        continue
                    ca, cb = slopes[a][m] >= t, slopes[b][m] >= t
                    po = float(np.mean(ca == cb))
                    pe = float(ca.mean() * cb.mean() + (1 - ca.mean()) * (1 - cb.mean()))
                    pair_rows.append({"site": key, "dem_a": a, "dem_b": b, "threshold_deg": t, "common_px": int(m.sum()),
                                      "class_disagreement_pct": 100 * (1 - po), "cohen_kappa": (po - pe) / (1 - pe) if pe < 1 else None,
                                      "interpretation": "MODEL_DISAGREEMENT_NOT_ACCURACY"})
        if d.get("ref_fine") is not None:
            k = int(round(30 / d["rf"]))
            zr = T.block_mean(d["ref_fine"], k)
            S.save_tif(sdir / "rasters" / "reference_dtm_30m_blockmean_m.tif", zr, grid, descr="independent reference DTM block-mean to 30 m")
            S.save_tif(sdir / "rasters" / "reference_slope_30m_deg.tif", T.slope_deg(zr, 30.0), grid, descr="reference slope from block-mean DTM (support-matched)")
    C.write_csv(out / "tables" / "dem_qc.csv", qc)
    C.write_csv(out / "tables" / "slope_class_shares.csv", shares)
    C.write_csv(out / "tables" / "pairwise_dem_threshold_disagreement.csv", pair_rows)

    # ------------------------------------------------------------- validation
    val = {k: {"z": {p: d["z"][p] for p in predictors if p in d["z"]}, "ref_fine": d["ref_fine"], "rf": d["rf"]}
           for k, d in data.items() if d["group"] == "validation" and d.get("ref_fine") is not None and all(p in d["z"] for p in predictors)}
    results, models, taus = {}, {}, {}
    manifest_val = {"validation_sites_used": sorted(val), "validation_sites_requested": [k for k, d in data.items() if d["group"] == "validation"]}
    if not args.no_validation:
        if len(val) >= 2:
            try:
                results, models, taus = E.run_validation(val, cfg, out)
                C.write_csv(out / "tables" / "validation_aurc.csv", results["aurc"])
                C.write_csv(out / "tables" / "validation_aurc_bootstrap_ci.csv", results["ci"])
                C.write_csv(out / "tables" / "validation_calibration_bins.csv", results["calib"])
                C.write_csv(out / "tables" / "validation_calibration_metrics.csv", results["calib_metrics"])
                C.write_csv(out / "tables" / "validation_risk_coverage_curves.csv", results["rc"])
                C.write_csv(out / "tables" / "validation_operating_points_heldout.csv", results["oper"])
                C.write_csv(out / "tables" / "validation_stress_tests.csv", results["stress"])
                C.write_csv(out / "tables" / "validation_dem_error_vs_reference.csv", E.dem_error_table(val, predictors))
                C.write_csv(out / "tables" / "validation_shared_error_consensus.csv", E.shared_error_table(val, th, predictors))
                R.rc_figure(out / "figures" / "risk_coverage_loso.png", results["rc"], th)
                R.calib_figure(out / "figures" / "calibration_loso.png", results["calib"], th)
                C.log("validation", "R40-experiment", "VALIDATION_DONE", f"sites={sorted(val)}")
            except Exception as e:  # noqa: BLE001
                C.log_exc("validation", "R40-experiment", e)
        else:
            C.log("validation", "R40-experiment", "VALIDATION_IMPOSSIBLE", f"need >=2 validation sites with reference DTM and all predictor DEMs; have {sorted(val)}")
    # ------------------------------------------------------------- application to all sites (no reference needed)
    dec_rows, flip_rows, intl = [], [], []
    for key, d in data.items():
        z = d["z"]
        grid = d["grid"]
        if not all(p in z for p in predictors):
            C.log(key, "application", "SKIPPED", f"missing predictor DEMs: {[p for p in predictors if p not in z]}")
            continue
        sdir = out / "sites" / key
        decisions_c, decisions_d = {}, {}
        s_primary = d["slopes"][primary]
        for t in th:
            if t not in models:
                continue
            try:
                r = E.apply_to_site(z, grid.res, t, predictors, primary, models[t], taus[(t, head, "combined")], taus[(t, head, "distance")])
                decisions_c[t], decisions_d[t] = r["dec_combined"], r["dec_distance"]
                if d["group"] == "kazakhstan":
                    S.save_tif(sdir / "rasters" / f"decision_combined_t{t}_risk{int(head*100)}.tif", r["dec_combined"], grid, nodata=255, dtype="uint8", descr="0=BELOW 1=ABOVE 2=ABSTAIN 255=nodata")
                    S.save_tif(sdir / "rasters" / f"p_error_combined_t{t}.tif", r["perr"], grid, descr="predicted probability of threshold-class error (model transferred from validation sites)")
                    to_wgs = Transformer.from_crs(grid.epsg, 4326, always_xy=True).transform
                    C.write_json(sdir / f"decision_combined_t{t}.geojson", R.vector_geojson(r["dec_combined"], grid, to_wgs, DEC_LABELS))
                for mname, m in d["masks"].items():
                    for meth, arr in (("combined", r["dec_combined"]), ("distance_only", r["dec_distance"])):
                        mm = m & (arr != 255)
                        n = int(mm.sum())
                        if n == 0:
                            continue
                        dec_rows.append({"site": key, "group": d["group"], "mask": mname, "threshold_deg": t, "target_risk_train": head, "method": meth,
                                         "n_px": n, "BELOW_pct": float(100 * np.mean(arr[mm] == 0)), "ABOVE_pct": float(100 * np.mean(arr[mm] == 1)),
                                         "ABSTAIN_pct": float(100 * np.mean(arr[mm] == 2)),
                                         "note": "in-sample (site contributed to model training)" if key in val else "model transferred; error NOT measured at this site"})
            except Exception as e:  # noqa: BLE001
                C.log_exc(key, f"application:t={t}", e)
        if d["group"] == "kazakhstan":
            try:
                if decisions_c:
                    R.site_figure(out / "figures" / f"{key}_decisions.png", key, cfg["kazakhstan"][key]["name_ru"], grid, s_primary, decisions_c, [t for t in th if t in decisions_c],
                                  d["terr_utm"], d["foot_utm"] if d["territory"] is None else None, head)
                for mname, m in d["masks"].items():
                    for r_ in E.sensitivity_flips(z, predictors, primary, th, m):
                        r_.update(site=key, mask=mname)
                        flip_rows.append(r_)
            except Exception as e:  # noqa: BLE001
                C.log_exc(key, "figures/sensitivity", e)
        # comparison row
        zp = z[primary]
        vz = zp[np.isfinite(zp)]
        row = {"site": key, "group": d["group"], "country": d["cfg"]["country"], "boundary_status": d["boundary_status"],
               "reference_dtm": bool(d.get("ref_fine") is not None), "elev_min_m": float(vz.min()), "elev_p5_m": float(np.percentile(vz, 5)),
               "elev_p95_m": float(np.percentile(vz, 95)), "elev_max_m": float(vz.max()), "relief_p95_p5_m": float(np.percentile(vz, 95) - np.percentile(vz, 5))}
        st = slope_stats(s_primary, d["masks"]["context"])
        if st:
            row.update({k: v for k, v in st.items() if k.startswith("share") or k in ("mean_slope", "area_km2")})
        stack = np.stack([d["slopes"][p] for p in predictors])
        row["mean_dem_slope_std_deg"] = float(np.nanmean(np.nanstd(stack, axis=0)))
        for t in th:
            rr = [x for x in dec_rows if x["site"] == key and x["threshold_deg"] == t and x["method"] == "combined" and x["mask"] == "context"]
            if rr:
                row[f"abstain_pct_t{t}"] = rr[0]["ABSTAIN_pct"]
        intl.append(row)
    C.write_csv(out / "tables" / "decisions_by_site.csv", dec_rows)
    C.write_csv(out / "tables" / "kazakhstan_sensitivity_class_change.csv", flip_rows)
    C.write_csv(out / "tables" / "international_comparison.csv", intl)
    # similarity of terrain statistics (not equivalence of resorts)
    try:
        feats = ["relief_p95_p5_m", "mean_slope", "share_15_25", "share_ge_25"]
        arr = np.array([[r[f] for f in feats] for r in intl], dtype=float)
        z_ = (arr - arr.mean(0)) / (arr.std(0) + 1e-9)
        pairs = []
        for i, a in enumerate(intl):
            if a["group"] != "kazakhstan":
                continue
            for j, b in enumerate(intl):
                if b["group"] == "validation":
                    pairs.append({"kazakhstan_site": a["site"], "comparison_site": b["site"], "country": b["country"],
                                  "terrain_stat_distance": float(np.linalg.norm(z_[i] - z_[j])), "features": ",".join(feats),
                                  "caveat": "similarity of window terrain statistics only; not a geographic or functional identification of any resort with an experimental tile"})
        pairs.sort(key=lambda r: (r["kazakhstan_site"], r["terrain_stat_distance"]))
        C.write_csv(out / "tables" / "international_terrain_similarity.csv", pairs)
        sh_rows = [dict(r) for r in shares if r["dem"] == primary]
        R.comparison_figure(out / "figures" / "slope_class_shares_all_sites.png", sh_rows)
    except Exception as e:  # noqa: BLE001
        C.log_exc("all", "international-comparison", e)

    # ------------------------------------------------------------- packaging
    finish(out, cfg, data, results, manifest_val, t_start, args)


def finish(out, cfg, data, results, manifest_val, t_start, args):
    for sub in ("src", "tests"):
        shutil.copytree(ROOT / sub, out / "code" / sub, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    for f in ("config.json", "requirements.txt", "KAZEOSAT_REQUEST_RU.md"):
        if (ROOT / f).exists():
            shutil.copy(ROOT / f, out / "code" / f)
    C.write_csv(out / "run_status.csv", C.AUDIT, ["time", "site", "source", "status", "details", "count"])
    C.write_json(out / "errors.json", C.ERRORS)
    ok = [r for r in C.AUDIT if r["status"] in ("RASTER_READY", "REFERENCE_READY", "FOUND", "NDVI_READY", "OSM_POLYGON_NAMED_MATCH", "FUNCTIONAL_FOOTPRINT_ONLY", "CATALOG_OK")]
    bad = [r for r in C.AUDIT if r["status"] not in ("RASTER_READY", "REFERENCE_READY", "FOUND", "NDVI_READY", "OSM_POLYGON_NAMED_MATCH", "FUNCTIONAL_FOOTPRINT_ONLY", "CATALOG_OK", "VALIDATION_DONE", "ACQUIRE_DONE")]
    C.write_json(out / "manifest.json", {
        "project": cfg["run_label"], "finished_utc": C.now(), "runtime_s": round(time.time() - t_start), "thresholds_deg": cfg["thresholds_deg"],
        "primary_dem": cfg["primary_dem"], "predictor_dems": cfg["predictor_dems"], "sites": {k: {"group": d["group"], "boundary_status": d["boundary_status"],
                                                                                            "dems": sorted(d["z"]), "reference_dtm": d.get("ref_fine") is not None} for k, d in data.items()},
        "validation": manifest_val, "reference_dtm_available_for_kazakhstan": False, "kazakhstan_error_is_measured": False,
        "n_ok_events": len(ok), "n_problem_events": len(bad), "policy": "No restricted imagery fetched or distributed; ALOS/FABDEM rasters not redistributed (statistics only).",
        "python": sys.version.split()[0]})
    from .make_readme import write_readme
    try:
        write_readme(out, cfg, data, results, manifest_val)
    except Exception as e:  # noqa: BLE001
        C.log_exc("all", "readme", e)
    with (out / "sha256.txt").open("w", encoding="utf-8") as f:
        for p in sorted(out.rglob("*")):
            if p.is_file() and p.name != "sha256.txt":
                f.write(f"{C.sha256(p)}  {p.relative_to(out)}\n")
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
