"""R40 experiment orchestration on in-memory site data (validation sites with reference DTM + Kazakhstan application)."""
from __future__ import annotations
import numpy as np
from . import common as C
from . import decision as D
from . import terrain as T

STRESS = [
    {"name": "baseline", "kw": {}},
    {"name": "noise_2m", "kw": {"noise_m": 2.0}},
    {"name": "noise_5m", "kw": {"noise_m": 5.0}},
    {"name": "support_60m", "kw": {"support_m": 60}},
    {"name": "support_90m", "kw": {"support_m": 90}},
    {"name": "algorithm_zt", "kw": {"algorithm": "zt"}},
    {"name": "algorithm_evans", "kw": {"algorithm": "evans"}},
    {"name": "reference_fraction_rule_B", "kw": {"ref_mode": "B"}},
    {"name": "primary_nasadem", "kw": {"primary": "nasadem"}},
    {"name": "primary_alos", "kw": {"primary": "alos-dem"}},
]


def _tables(val, t, predictors, **kw):
    out = {}
    for s, v in val.items():
        dems = [d for d in predictors if d in v["z"]]
        if len(dems) < len(predictors):
            continue
        out[s] = D.build_table(s, v["z"], v["ref_fine"], v["rf"], t, dems=dems, **kw)
    return out


def dem_error_table(val, predictors):
    """Elevation/slope error of each global DEM against the independent reference (support-matched, 30 m)."""
    rows = []
    for s, v in val.items():
        zr = T.block_mean(v["ref_fine"], int(round(30 / v["rf"])))
        sr = T.slope_deg(zr, 30.0)
        for d in predictors:
            if d not in v["z"]:
                continue
            z = v["z"][d].astype("float64")
            m = np.isfinite(z) & np.isfinite(zr)
            if m.sum() < 100:
                continue
            dz = (z - zr)[m]
            sd = T.slope_deg(z, 30.0)
            ms = np.isfinite(sd) & np.isfinite(sr)
            ds = (sd - sr)[ms]
            rows.append({"site": s, "dem": d, "n_elev": int(m.sum()), "elev_bias_m_incl_datum": float(dz.mean()),
                         "elev_median_m": float(np.median(dz)), "elev_rmse_debiased_m": float(dz.std()),
                         "elev_NMAD_m": float(1.4826 * np.median(np.abs(dz - np.median(dz)))),
                         "slope_bias_deg": float(ds.mean()), "slope_rmse_deg": float(np.sqrt((ds ** 2).mean())),
                         "slope_MAE_deg": float(np.abs(ds).mean()), "n_slope": int(ms.sum())})
    return rows


def shared_error_table(val, thresholds, predictors):
    """Is agreement of global DEMs evidence of correctness? Compare consensus error with reference."""
    rows = []
    for t in thresholds:
        for s, v in val.items():
            if not all(d in v["z"] for d in predictors):
                continue
            sl = {d: T.slope_deg(v["z"][d], 30.0) for d in predictors}
            ref = D.reference_fields(v["ref_fine"], v["rf"], 30.0, t)["y_A"]
            cl = {d: T.classes(sl[d], t) for d in predictors}
            ok = np.isfinite(ref)
            for d in predictors:
                ok &= np.isfinite(cl[d])
            if ok.sum() < 100:
                continue
            stack = np.stack([cl[d][ok] for d in predictors])
            y = ref[ok]
            unanimous = np.all(stack == stack[0], axis=0)
            wrong_each = [(cl[d][ok] != y) for d in predictors]
            all_wrong = np.all(np.stack(wrong_each), axis=0)
            any_wrong = np.any(np.stack(wrong_each), axis=0)
            cons_err = (stack[0][unanimous] != y[unanimous]).mean() if unanimous.any() else np.nan
            rows.append({"site": s, "threshold_deg": t, "n": int(ok.sum()), "unanimous_share": float(unanimous.mean()),
                         "error_rate_when_unanimous": float(cons_err),
                         "error_rate_when_split": float((stack[0][~unanimous] != y[~unanimous]).mean()) if (~unanimous).any() else np.nan,
                         "share_of_any_dem_errors_that_are_shared_by_all": float(all_wrong.sum() / max(any_wrong.sum(), 1)),
                         **{f"error_rate_{d}": float(w.mean()) for d, w in zip(predictors, wrong_each)}})
    return rows


def run_validation(val, cfg, outdir):
    """Spatially independent validation of the BELOW/ABOVE/ABSTAIN rules. Returns trained models for application."""
    predictors = cfg["predictor_dems"]
    primary = cfg["primary_dem"]
    th = cfg["thresholds_deg"]
    nb = cfg["decision"]["n_boot"]
    results = {"aurc": [], "ci": [], "calib": [], "calib_metrics": [], "rc": [], "oper": [], "stress": []}
    models, taus = {}, {}
    if len(val) < 2:
        C.log("validation", "R40", "VALIDATION_IMPOSSIBLE", f"only {len(val)} site(s) with reference DTM")
        return results, models, taus
    for t in th:
        base = _tables(val, t, predictors, primary=primary)
        if len(base) < 2:
            C.log("validation", f"t={t}", "VALIDATION_IMPOSSIBLE", "fewer than 2 sites with full predictor set")
            continue
        for scheme in ("loso", "block"):
            p = D.cv_scores(base, scheme)
            p = {s: (v if np.all(np.isfinite(v)) else np.where(np.isfinite(v), v, np.nanmean(v))) for s, v in p.items()}
            rows, ci = D.evaluate(base, p, n_boot=nb)
            for r in rows:
                r.update(threshold_deg=t, scheme=scheme)
            for r in ci:
                r.update(threshold_deg=t, scheme=scheme)
            results["aurc"] += rows
            results["ci"] += ci
            if scheme == "loso":
                pool = D.pool(base)
                pp = np.concatenate([p[s] for s in base])
                cal, met = D.calibration(pp, pool["err"])
                for r in cal:
                    r.update(threshold_deg=t)
                met.update(threshold_deg=t, n=int(len(pp)))
                results["calib"] += cal
                results["calib_metrics"].append(met)
                u = D.scores_for(pool, pp, np.random.default_rng(2))
                for m, uu in u.items():
                    cov, risk = D.risk_coverage(uu, pool["err"], np.random.default_rng(3))
                    idx = np.unique(np.linspace(0, len(cov) - 1, 200).astype(int))
                    results["rc"] += [{"threshold_deg": t, "method": m, "coverage": float(cov[i]), "risk": float(risk[i])} for i in idx]
                # risk-controlled operating points (tau fixed on training sites, evaluated on held-out site)
                rng = np.random.default_rng(5)
                for target in cfg["decision"]["target_risks"]:
                    for s in base:
                        others = [o for o in base if o != s]
                        Xo = np.concatenate([D._X(base[o]) for o in others]); yo = np.concatenate([base[o]["err"] for o in others])
                        idx_t = D._subsample({"err": yo}, 120000, rng)
                        mdl = D.fit_logit(Xo[idx_t], yo[idx_t])
                        for mname in ("combined", "distance"):
                            if mname == "combined":
                                utr = D.predict_logit(mdl, Xo); ute = D.predict_logit(mdl, D._X(base[s]))
                            else:
                                utr = np.concatenate([-base[o]["dist"] for o in others]); ute = -base[s]["dist"]
                            tau = D.choose_tau(utr, yo, target, rng)
                            acc = ute <= tau
                            results["oper"].append({"threshold_deg": t, "heldout_site": s, "method": mname, "target_risk_train": target,
                                                    "tau": tau, "coverage_heldout": float(acc.mean()),
                                                    "selective_risk_heldout": float(base[s]["err"][acc].mean()) if acc.any() else np.nan,
                                                    "full_coverage_error_heldout": float(base[s]["err"].mean())})
        # final models for application to Kazakhstan: trained on all validation sites pooled
        Xa = np.concatenate([D._X(base[s]) for s in base]); ya = np.concatenate([base[s]["err"] for s in base])
        rng = np.random.default_rng(7)
        idx_t = D._subsample({"err": ya}, 150000, rng)
        models[t] = D.fit_logit(Xa[idx_t], ya[idx_t])
        pa = D.predict_logit(models[t], Xa)
        da = np.concatenate([-base[s]["dist"] for s in base])
        for target in cfg["decision"]["target_risks"]:
            taus[(t, target, "combined")] = D.choose_tau(pa, ya, target, rng)
            taus[(t, target, "distance")] = D.choose_tau(da, ya, target, rng)
        # stress tests (LOSO combined + all heuristics, pooled)
        for st in STRESS:
            kw = dict(st["kw"])
            prim = kw.pop("primary", primary)
            try:
                tabs = _tables(val, t, predictors, primary=prim, seed=11, **kw)
                if len(tabs) < 2:
                    continue
                p = D.cv_scores(tabs, "loso", seed=3)
                p = {s: (v if np.all(np.isfinite(v)) else np.where(np.isfinite(v), v, np.nanmean(v))) for s, v in p.items()}
                pool = D.pool(tabs); pp = np.concatenate([p[s] for s in tabs])
                u = D.scores_for(pool, pp, np.random.default_rng(4))
                row = {"threshold_deg": t, "stress": st["name"], "n_pixels": int(len(pool["err"])),
                       "error_rate_full_coverage": float(pool["err"].mean())}
                for m, uu in u.items():
                    row[f"AURC_{m}"] = D.aurc(uu, pool["err"], np.random.default_rng(6))
                results["stress"].append(row)
            except Exception as e:  # noqa: BLE001
                C.log_exc("validation", f"stress:{st['name']}:t={t}", e)
    return results, models, taus


def apply_to_site(zdict, grid_res, t, predictors, primary, model, tau_c, tau_d, mask=None):
    """Decision maps for one site (no reference): returns dict of arrays on the grid."""
    zs = {d: zdict[d] for d in predictors if d in zdict}
    if len(zs) < len(predictors):
        return None
    f = T.decision_features(zs, primary, grid_res, t)
    ok = np.ones(f["dist"].shape, bool)
    for k in D.FEATURES + ["pred"]:
        ok &= np.isfinite(f[k])
    X = np.stack([f[k][ok] for k in D.FEATURES], axis=1)
    perr = np.full(f["dist"].shape, np.nan, "float32")
    perr[ok] = D.predict_logit(model, X)
    pred = f["pred"]
    dec_c = np.full(pred.shape, 255, "uint8")
    dec_c[ok] = D.decide(pred[ok], perr[ok], tau_c).astype("uint8")
    dec_d = np.full(pred.shape, 255, "uint8")
    dec_d[ok] = D.decide(pred[ok], -f["dist"][ok], tau_d).astype("uint8")
    return {"feat": f, "perr": perr, "dec_combined": dec_c, "dec_distance": dec_d, "ok": ok}


def sensitivity_flips(zdict, predictors, primary, thresholds, mask):
    """Share of pixels (in mask) whose class changes with algorithm / support / DEM choice. No reference involved."""
    rows = []
    z = zdict[primary]
    sh = {a: T.slope_deg(z, 30.0, a) for a in T.ALGORITHMS}
    s60 = T.coarse_slope(z, 30.0, 2)
    s90 = T.coarse_slope(z, 30.0, 3)
    sl = {d: T.slope_deg(zdict[d], 30.0) for d in predictors if d in zdict}
    for t in thresholds:
        def flip(a, b, name):
            m = mask & np.isfinite(a) & np.isfinite(b)
            if m.sum() < 20:
                return
            rows.append({"threshold_deg": t, "comparison": name, "n": int(m.sum()), "class_change_pct": float(100 * np.mean((a[m] >= t) != (b[m] >= t)))})
        flip(sh["horn"], sh["zt"], "algorithm horn vs zevenbergen-thorne")
        flip(sh["horn"], sh["evans"], "algorithm horn vs evans")
        flip(sh["horn"], s60, "support 30 m vs 60 m (same DEM)")
        flip(sh["horn"], s90, "support 30 m vs 90 m (same DEM)")
        ks = sorted(sl)
        for i, a in enumerate(ks):
            for b in ks[i + 1:]:
                flip(sl[a], sl[b], f"DEM {a} vs {b}")
    return rows
