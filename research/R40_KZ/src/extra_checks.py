"""R40 extra checks requested by the independent review (no change of the approved concept, no new data products).

A. Paired block-bootstrap of AURC differences on the FULL pooled sample (no 80,000-pixel thinning), two designs:
   plain (blocks resampled over all sites) and site-stratified (blocks resampled within each site); pooled and macro (site-mean) AURC.
   Comparisons: combined - norm_margin, combined - distance, norm_margin - distance.
B. Leave-one-country-out (train CH -> test US, train US -> test CH): AURC and operating points of combined / distance / norm_margin.
C. Per-site calibration of the LOSO combined score (ECE, Brier skill, mean predicted vs observed error).
D. Applicability of the training feature range to the Kazakhstan windows (share of pixels outside the training range).
"""
from __future__ import annotations
import json
import numpy as np
from . import common as C
from . import terrain as T
from . import experiment as E
from . import decision as D

PAIRS = (("combined", "norm_margin"), ("combined", "distance"), ("norm_margin", "distance"))


def aurc_fast(u, err):
    """AURC (mean selective risk over all coverage levels), most confident first; stable order for ties."""
    o = np.argsort(u, kind="stable")
    e = err[o]
    return float((np.cumsum(e) / np.arange(1, len(e) + 1)).mean())


def _site_index(site):
    return {s: np.nonzero(site == s)[0] for s in np.unique(site)}


def boot(u_by, err, block, site, n_boot=200, seed=1, stratified=True):
    """Resample 1-km blocks (jointly for all methods). stratified: within each site; else over all blocks.
    Returns {method: {"pooled": array, "macro": array}} (macro only when stratified)."""
    rng = np.random.default_rng(seed)
    sidx = _site_index(site)
    blk = {}
    for s, m in sidx.items():
        ub = np.unique(block[m])
        blk[s] = (ub, {b: m[block[m] == b] for b in ub})
    all_blocks = np.unique(block)
    by_block = {b: np.nonzero(block == b)[0] for b in all_blocks}
    res = {k: {"pooled": [], "macro": []} for k in u_by}
    for _ in range(n_boot):
        if stratified:
            per = []
            for s in sidx:
                ub, ix = blk[s]
                per.append(np.concatenate([ix[b] for b in rng.choice(ub, len(ub), replace=True)]))
            allidx = np.concatenate(per)
        else:
            allidx = np.concatenate([by_block[b] for b in rng.choice(all_blocks, len(all_blocks), replace=True)])
            per = None
        for k, u in u_by.items():
            res[k]["pooled"].append(aurc_fast(u[allidx], err[allidx]))
            if per is not None:
                res[k]["macro"].append(float(np.mean([aurc_fast(u[i], err[i]) for i in per])))
    return {k: {m: np.array(v) for m, v in d.items()} for k, d in res.items()}


def point_estimates(u_by, err, site):
    sidx = _site_index(site)
    out = {}
    for k, u in u_by.items():
        out[k] = {"pooled": aurc_fast(u, err), "macro": float(np.mean([aurc_fast(u[i], err[i]) for i in sidx.values()]))}
    return out


def _clean(p):
    return {s: (v if np.all(np.isfinite(v)) else np.where(np.isfinite(v), v, np.nanmean(v))) for s, v in p.items()}


def part_a_c(val, cfg, rows_boot, rows_cal, rows_site):
    predictors, primary = cfg["predictor_dems"], cfg["primary_dem"]
    nb = int(cfg.get("extra", {}).get("n_boot", 200))
    for t in cfg["thresholds_deg"]:
        base = E._tables(val, t, predictors, primary=primary)
        p = _clean(D.cv_scores(base, "loso"))
        names = list(base)
        pool = D.pool(base)
        pp = np.concatenate([p[s] for s in names])
        site = np.concatenate([[s] * len(base[s]["err"]) for s in names])
        u = D.scores_for(pool, pp, np.random.default_rng(2))
        u = {k: u[k] for k in ("distance", "norm_margin", "combined")}
        err, block = pool["err"], pool["block"]
        pe = point_estimates(u, err, site)
        for stratified in (False, True):
            bs = boot(u, err, block, site, n_boot=nb, seed=5, stratified=stratified)
            for a, b in PAIRS:
                for metric in (("pooled", "macro") if stratified else ("pooled",)):
                    d = bs[a][metric] - bs[b][metric]
                    rows_boot.append({"threshold_deg": t, "design": "site_stratified" if stratified else "plain_all_blocks",
                                      "comparison": f"{a} - {b}", "metric": metric, "point_estimate": pe[a][metric] - pe[b][metric],
                                      "boot_mean": float(d.mean()), "lo95": float(np.percentile(d, 2.5)), "hi95": float(np.percentile(d, 97.5)),
                                      "n_boot": nb, "n_pixels": int(len(err)), "n_blocks": int(len(np.unique(block)))})
        for m in u:
            rows_boot.append({"threshold_deg": t, "design": "point", "comparison": m, "metric": "pooled", "point_estimate": pe[m]["pooled"], "n_pixels": int(len(err))})
            rows_boot.append({"threshold_deg": t, "design": "point", "comparison": m, "metric": "macro", "point_estimate": pe[m]["macro"], "n_pixels": int(len(err))})
        sidx = _site_index(site)
        for s, ii in sidx.items():
            row = {"threshold_deg": t, "site": s, "n_pixels": int(len(ii)), "error_rate": float(err[ii].mean())}
            for m in u:
                row[f"AURC_{m}"] = aurc_fast(u[m][ii], err[ii])
            rows_site.append(row)
            _, met = D.calibration(p[s], base[s]["err"])
            rows_cal.append({"threshold_deg": t, "site": s, "ECE": met["ECE"], "Brier": met["Brier"], "Brier_const": met["Brier_const"],
                             "Brier_skill": met["Brier_skill"], "mean_pred_error": float(p[s].mean()), "observed_error": float(base[s]["err"].mean()),
                             "n": int(len(p[s]))})
        _, met = D.calibration(pp, err)
        rows_cal.append({"threshold_deg": t, "site": "POOLED", "ECE": met["ECE"], "Brier": met["Brier"], "Brier_const": met["Brier_const"],
                         "Brier_skill": met["Brier_skill"], "mean_pred_error": float(pp.mean()), "observed_error": float(err.mean()), "n": int(len(pp))})
        C.log("all", "extra", "PART_A_C_DONE", f"t={t}")


def part_b(val, cfg, rows_loco, rows_loco_op):
    predictors, primary = cfg["predictor_dems"], cfg["primary_dem"]
    country = {k: cfg["validation"][k]["country"] for k in val}
    rng = np.random.default_rng(31)
    for t in cfg["thresholds_deg"]:
        base = E._tables(val, t, predictors, primary=primary)
        for tgt in sorted(set(country.values())):
            tr = [s for s in base if country[s] != tgt]
            te = [s for s in base if country[s] == tgt]
            if not tr or not te:
                continue
            Xtr = np.concatenate([D._X(base[s]) for s in tr]); ytr = np.concatenate([base[s]["err"] for s in tr])
            ii = D._subsample({"err": ytr}, 120000, rng)
            mdl = D.fit_logit(Xtr[ii], ytr[ii])
            ptr = D.predict_logit(mdl, Xtr)
            ptr_pool = D.pool(base, tr)
            utr = D.scores_for(ptr_pool, ptr, np.random.default_rng(3))
            sc_te = {}
            for s in te:
                pe = D.predict_logit(mdl, D._X(base[s]))
                sc_te[s] = D.scores_for(base[s], pe, np.random.default_rng(4))
            pool_te = D.pool(base, te)
            sc_pool = D.scores_for(pool_te, np.concatenate([D.predict_logit(mdl, D._X(base[s])) for s in te]), np.random.default_rng(4))
            for label, sc, err in [("POOLED_" + tgt, sc_pool, pool_te["err"])] + [(s, sc_te[s], base[s]["err"]) for s in te]:
                row = {"threshold_deg": t, "train_country": "+".join(sorted(set(country[s] for s in tr))), "test_unit": label, "n_pixels": int(len(err)), "error_rate": float(err.mean())}
                for m in ("random", "distance", "norm_margin", "combined"):
                    row[f"AURC_{m}"] = aurc_fast(sc[m], err)
                rows_loco.append(row)
            for target in cfg["decision"]["target_risks"]:
                for m in ("distance", "norm_margin", "combined"):
                    tau = D.choose_tau(utr[m], ytr, target, rng)
                    for s in te:
                        acc = sc_te[s][m] <= tau
                        rows_loco_op.append({"threshold_deg": t, "train_country": "+".join(sorted(set(country[x] for x in tr))), "test_site": s, "method": m,
                                             "target_risk_train": target, "coverage": float(acc.mean()),
                                             "selective_risk": float(base[s]["err"][acc].mean()) if acc.any() else None,
                                             "full_coverage_error": float(base[s]["err"].mean())})
        C.log("all", "extra", "PART_B_DONE", f"t={t}")


def part_d(val, cfg, client, rows_aoa):
    from . import sources as S
    from .run import window_bbox
    predictors, primary = cfg["predictor_dems"], cfg["primary_dem"]
    kz = {}
    for key, s in cfg["kazakhstan"].items():
        try:
            lon, lat = s["center"]
            epsg = C.utm_epsg(lon, lat)
            bbox = window_bbox(s, [])
            grid = S.make_grid(bbox, epsg, cfg["grid_res_m"])
            z, _ = S.fetch_pc_dems(client, key, (bbox[0], bbox[1], bbox[2], bbox[3]), grid)
            if all(p in z for p in predictors):
                kz[key] = {p: z[p] for p in predictors}
            else:
                C.log(key, "extra-aoa", "SKIPPED", "predictor DEMs missing")
        except Exception as e:  # noqa: BLE001
            C.log_exc(key, "extra-aoa", e)
    for t in cfg["thresholds_deg"]:
        base = E._tables(val, t, predictors, primary=primary)
        pool = D.pool(base)
        lo = {k: float(pool[k].min()) for k in D.FEATURES}
        hi = {k: float(pool[k].max()) for k in D.FEATURES}
        plo = {k: float(np.percentile(pool[k], 0.5)) for k in D.FEATURES}
        phi = {k: float(np.percentile(pool[k], 99.5)) for k in D.FEATURES}
        for key, zs in kz.items():
            f = T.decision_features(zs, primary, float(cfg["grid_res_m"]), t)
            ok = np.ones(f["dist"].shape, bool)
            for k in D.FEATURES:
                ok &= np.isfinite(f[k])
            n = int(ok.sum())
            if n == 0:
                continue
            out_mm = np.zeros(n, bool); out_p = np.zeros(n, bool)
            row = {"threshold_deg": t, "site": key, "n_pixels": n}
            for k in D.FEATURES:
                v = f[k][ok].astype("float64")
                a = (v < lo[k]) | (v > hi[k]); b = (v < plo[k]) | (v > phi[k])
                out_mm |= a; out_p |= b
                row[f"outside_minmax_{k}"] = float(a.mean()); row[f"outside_p0.5_99.5_{k}"] = float(b.mean())
            row["outside_minmax_any"] = float(out_mm.mean()); row["outside_p0.5_99.5_any"] = float(out_p.mean())
            row["share_slope_gt_train_p99.5"] = float((f["slope"][ok] > phi["slope"]).mean())
            row["train_slope_p99.5"] = phi["slope"]
            rows_aoa.append(row)
        C.log("all", "extra", "PART_D_DONE", f"t={t}")


def main():
    from . import sources as S
    from . import icesat2 as I
    from .icesat2_riskcov import acquire_validation
    cfg = json.loads((I.ROOT / "config.json").read_text(encoding="utf-8"))
    out = C.OUT
    (out / "tables").mkdir(parents=True, exist_ok=True)
    client = S.pc_client()
    val = acquire_validation(cfg, client)
    if len(val) < 2:
        C.write_json(out / "extra_error.json", {"error": "fewer than 2 validation sites", "sites": sorted(val)})
        return
    rows_boot, rows_cal, rows_site, rows_loco, rows_loco_op, rows_aoa = [], [], [], [], [], []
    for name, fn, args in (("A_C", part_a_c, (val, cfg, rows_boot, rows_cal, rows_site)), ("B", part_b, (val, cfg, rows_loco, rows_loco_op)),
                           ("D", part_d, (val, cfg, client, rows_aoa))):
        try:
            fn(*args)
        except Exception as e:  # noqa: BLE001
            C.log_exc("all", f"extra-{name}", e)
    C.write_csv(out / "tables" / "extra_paired_bootstrap.csv", rows_boot)
    C.write_csv(out / "tables" / "extra_site_aurc.csv", rows_site)
    C.write_csv(out / "tables" / "extra_site_calibration.csv", rows_cal)
    C.write_csv(out / "tables" / "extra_leave_one_country_out_aurc.csv", rows_loco)
    C.write_csv(out / "tables" / "extra_leave_one_country_out_operating.csv", rows_loco_op)
    C.write_csv(out / "tables" / "extra_kz_feature_range.csv", rows_aoa)
    C.write_csv(out / "extra_run_status.csv", C.AUDIT, ["time", "site", "source", "status", "details", "count"])
    C.write_json(out / "extra_errors.json", C.ERRORS)
    print("DONE-EXTRA")


if __name__ == "__main__":
    main()
