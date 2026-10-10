"""Risk-coverage of the transferred abstention model against ICESat-2 along-track slope classes (Kazakhstan and test sites).

Model: trained on the lidar-DTM validation sites exactly as in the main run (E.run_validation), then applied to every
ICESat-2 study area. Reference = class of the ICESat-2 ATL08 along-track slope between adjacent 100 m segments.
Error = class of the DEM along-track slope (same 100 m geometry) disagrees with the ICESat-2 class.
ICESat-2 noise inflates every method's error alike; the comparison is of RANKING quality (AURC), not absolute error.
"""
from __future__ import annotations
import json
import numpy as np
from pyproj import Transformer
from . import common as C
from . import sources as S
from . import terrain as T
from . import experiment as E
from . import icesat2 as I
from . import decision as D
from .run import window_bbox


def acquire_validation(cfg, client):
    val = {}
    for key, s in cfg["validation"].items():
        try:
            lon, lat = s["center"]
            epsg = C.utm_epsg(lon, lat)
            bbox = window_bbox(s, [])
            grid = S.make_grid(bbox, epsg, cfg["grid_res_m"])
            bb = (bbox[0], bbox[1], bbox[2], bbox[3])
            z, _ = S.fetch_pc_dems(client, key, bb, grid)
            rf = float(s["ref_res_m"])
            gf = grid.fine(rf)
            ref, _ = S.fetch_swissalti3d(key, bb, gf) if s["reference"] == "swissalti3d" else S.fetch_3dep(client, key, bb, gf)
            if ref is not None and all(p in z for p in cfg["predictor_dems"]):
                val[key] = {"z": {p: z[p] for p in cfg["predictor_dems"]}, "ref_fine": ref.astype("float32"), "rf": rf}
                C.log(key, "riskcov-acquire", "REFERENCE_READY")
        except Exception as e:  # noqa: BLE001
            C.log_exc(key, "riskcov-acquire", e)
    return val


def block_boot(u_by, err, blocks, n_boot=300, seed=1):
    rng = np.random.default_rng(seed)
    ub = np.unique(blocks)
    idx_by = {b: np.nonzero(blocks == b)[0] for b in ub}
    res = {m: [] for m in u_by}
    for _ in range(n_boot):
        pick = rng.choice(ub, len(ub), replace=True)
        ii = np.concatenate([idx_by[b] for b in pick])
        for m, u in u_by.items():
            res[m].append(I.aurc_from(u[ii], err[ii], rng))
    out = {}
    for m, v in res.items():
        v = np.array(v)
        out[m] = (float(np.mean(v)), float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)), v)
    return out


def main():
    cfg = json.loads((I.ROOT / "config.json").read_text(encoding="utf-8"))
    out = C.OUT
    out.mkdir(parents=True, exist_ok=True)
    th, predictors, primary = cfg["thresholds_deg"], cfg["predictor_dems"], cfg["primary_dem"]
    head = cfg["decision"]["headline_target_risk"]
    client = S.pc_client()
    val = acquire_validation(cfg, client)
    if len(val) < 2:
        C.write_json(out / "riskcov_error.json", {"error": "fewer than 2 validation sites", "sites": sorted(val)})
        return
    results, models, taus = E.run_validation(val, cfg, out)
    C.write_csv(out / "tables" / "riskcov_model_validation_aurc.csv", results["aurc"])
    # support-matched model: trained and applied on 90 m block means (comparable to the 100 m ATL08 along-track geometry)
    models90, taus90 = {}, {}
    rng90 = np.random.default_rng(17)
    for t in th:
        base = E._tables(val, t, predictors, primary=primary, support_m=90)
        Xa = np.concatenate([D._X(base[k]) for k in base]); ya = np.concatenate([base[k]["err"] for k in base])
        ii = D._subsample({"err": ya}, 150000, rng90)
        models90[t] = D.fit_logit(Xa[ii], ya[ii])
        pa = D.predict_logit(models90[t], Xa)
        da = np.concatenate([-base[k]["dist"] for k in base])
        for target in cfg["decision"]["target_risks"]:
            taus90[(t, target, "combined")] = D.choose_tau(pa, ya, target, rng90)
            taus90[(t, target, "distance")] = D.choose_tau(da, ya, target, rng90)
    from types import SimpleNamespace
    areas = I.study_areas(cfg)
    rows, oper, curves = [], [], []
    rng = np.random.default_rng(0)
    for site, bbox in areas.items():
        f = out / "icesat2" / f"atl08_{site}.csv"
        if not f.exists():
            C.log(site, "riskcov", "NO_POINTS_FILE")
            continue
        try:
            p = I.load_points(f)
            lon0, lat0 = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
            epsg = C.utm_epsg(lon0, lat0)
            grid = S.make_grid(bbox, epsg, 30.0, max_side_km=45.0)
            dems, _ = S.fetch_pc_dems(client, site, bbox, grid)
            if not all(d in dems for d in predictors):
                C.log(site, "riskcov", "SKIPPED", "predictor DEMs missing")
                continue
            tr = Transformer.from_crs(4326, epsg, always_xy=True)
            for qlevel, umax in I.QUALITY_LEVELS.items():
                qm = I.quality_mask(p, unc_max=umax)
                q = {k: v[qm] for k, v in p.items()}
                x, y = tr.transform(q["lon"], q["lat"])
                ia, ib, dist = I.track_pairs(q, x, y)
                if len(ia) < 50:
                    continue
                h = q["h_te"]
                s_atl = np.degrees(np.arctan((h[ib] - h[ia]) / dist))
                z_s = I.sample(I.smooth100(dems[primary].astype("float64")), grid, x, y)
                s_d = np.degrees(np.arctan((z_s[ib] - z_s[ia]) / dist))
                blocks = (np.floor(x[ia] / 1000).astype(int) * 100000 + np.floor(y[ia] / 1000).astype(int))
                for t in th:
                    k3 = 3
                    d90 = {n: T.block_mean(dems[n].astype("float64"), k3) for n in predictors}
                    g90 = SimpleNamespace(x0=grid.x0, y1=grid.y1, res=90.0, w=d90[primary].shape[1], h=d90[primary].shape[0])
                    r90 = E.apply_to_site(d90, 90.0, t, predictors, primary, models90[t], taus90[(t, head, "combined")], taus90[(t, head, "distance")])
                    perr90 = r90["perr"]
                    fin9 = np.isfinite(perr90).astype("float64")
                    p9 = np.nan_to_num(perr90, nan=0.0).astype("float64")
                    pe90 = 0.5 * (I.sample(p9, g90, x[ia], y[ia]) + I.sample(p9, g90, x[ib], y[ib]))
                    v90 = (I.sample(fin9, g90, x[ia], y[ia]) > 0.999) & (I.sample(fin9, g90, x[ib], y[ib]) > 0.999)
                    r = E.apply_to_site(dems, 30.0, t, predictors, primary, models[t], taus[(t, head, "combined")], taus[(t, head, "distance")])
                    perr = r["perr"]
                    fin = np.isfinite(perr).astype("float64")
                    p0 = np.nan_to_num(perr, nan=0.0).astype("float64")
                    pe = 0.5 * (I.sample(p0, grid, x[ia], y[ia]) + I.sample(p0, grid, x[ib], y[ib]))
                    vfull = (I.sample(fin, grid, x[ia], y[ia]) > 0.999) & (I.sample(fin, grid, x[ib], y[ib]) > 0.999)
                    ok = np.isfinite(s_d) & np.isfinite(s_atl) & np.isfinite(pe) & vfull & np.isfinite(pe90) & v90
                    if ok.sum() < 50:
                        continue
                    sd, sa, pe_, bl, pe9 = np.abs(s_d[ok]), np.abs(s_atl[ok]), pe[ok], blocks[ok], pe90[ok]
                    err = ((sd >= t) != (sa >= t)).astype(float)
                    u = {"random": rng.random(len(err)), "distance": -np.abs(sd - t), "combined_30m_model": pe_, "combined_90m_model": pe9}
                    bs = block_boot(u, err, bl)
                    base = bs["distance"][3]
                    for m in u:
                        row = {"site": site, "quality": qlevel, "threshold_deg": t, "method": m, "n_pairs": int(ok.sum()),
                               "error_rate_full_coverage": float(err.mean()), "AURC": I.aurc_from(u[m], err, rng),
                               "AURC_boot_mean": bs[m][0], "AURC_lo95": bs[m][1], "AURC_hi95": bs[m][2],
                               "dAURC_vs_distance_lo95": float(np.percentile(bs[m][3] - base, 2.5)), "dAURC_vs_distance_hi95": float(np.percentile(bs[m][3] - base, 97.5)),
                               "model_in_training_set": site in val}
                        rows.append(row)
                    for target in cfg["decision"]["target_risks"]:
                        for m, tau, sc in (("combined_30m_model", taus[(t, target, "combined")], pe_), ("combined_90m_model", taus90[(t, target, "combined")], pe9), ("distance", taus[(t, target, "distance")], -np.abs(sd - t))):
                            acc = sc <= tau
                            oper.append({"site": site, "quality": qlevel, "threshold_deg": t, "method": m, "target_risk_train": target, "tau_fixed_on_lidar_sites": float(tau),
                                         "coverage": float(acc.mean()), "selective_risk_vs_icesat2": float(err[acc].mean()) if acc.any() else None,
                                         "full_coverage_error_vs_icesat2": float(err.mean()), "n_pairs": int(ok.sum())})
                C.log(site, "riskcov", "DONE", f"{qlevel}: pairs={len(ia)}")
        except Exception as e:  # noqa: BLE001
            C.log_exc(site, "riskcov", e)
    C.write_csv(out / "tables" / "icesat2_riskcov_aurc.csv", rows)
    C.write_csv(out / "tables" / "icesat2_riskcov_operating_points.csv", oper)
    C.write_csv(out / "icesat2_riskcov_run_status.csv", C.AUDIT, ["time", "site", "source", "status", "details", "count"])
    C.write_json(out / "icesat2_riskcov_errors.json", C.ERRORS)
    print("DONE-RISKCOV")


if __name__ == "__main__":
    main()
