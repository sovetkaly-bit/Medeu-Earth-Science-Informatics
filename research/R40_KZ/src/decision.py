"""R40 decision experiment: BELOW / ABOVE / ABSTAIN for slope-threshold classification.

Pure numpy. Predictors use only decision-time features (see terrain.decision_features);
reference classes enter only (a) as the error label used to *train/evaluate* the
abstention score on other folds/sites and (b) as ground truth for scoring.
"""
from __future__ import annotations
import numpy as np
from scipy import ndimage as ndi
from . import terrain as T

METHODS = ["random", "distance", "norm_margin", "dem_disagreement", "local_variability",
           "scale_stability", "combined"]
FEATURES = ["dist", "dem_disagreement_std", "local_slope_std", "scale_instab", "tri", "vote_split", "scale_flip"]
BLOCK_M = 1000.0  # spatial block size for CV / bootstrap


# ----------------------------------------------------------------------------- reference
def reference_fields(ref_fine, rf, support_m, t, algorithm="horn"):
    """Reference classes on the support grid (cell = support_m).

    A (primary, support-matched): slope of the block-mean reference DTM, same algorithm.
    B (sensitivity): fraction of fine-resolution slope pixels >= t inside the cell; class = frac >= 0.5.
    """
    k = int(round(support_m / rf))
    if abs(k * rf - support_m) > 1e-6:
        raise ValueError("support not multiple of reference resolution")
    zc = T.block_mean(ref_fine, k)
    sA = T.slope_deg(zc, support_m, algorithm)
    yA = T.classes(sA, t)
    sf = T.slope_deg(ref_fine, rf, algorithm)
    ind = np.where(np.isfinite(sf), (sf >= t).astype("float64"), np.nan)
    frac = T.block_mean(ind, k)
    yB = np.where(np.isfinite(frac), (frac >= 0.5).astype("float32"), np.nan)
    return {"slope_A": sA, "y_A": yA, "frac_B": frac.astype("float32"), "y_B": yB}


# ----------------------------------------------------------------------------- tables
def correlated_noise(shape, sigma_m, rng, corr_px=2.0):
    n = ndi.gaussian_filter(rng.standard_normal(shape), corr_px)
    n /= max(n.std(), 1e-12)
    return n * sigma_m


def build_table(site, z30, ref_fine, rf, t, primary="cop-dem-glo-30", support_m=30, algorithm="horn",
                noise_m=0.0, ref_mode="A", seed=0, dems=None):
    """Return dict of flat arrays for pixels where features and reference are valid."""
    rng = np.random.default_rng(seed)
    names = sorted(dems or z30.keys())
    k = int(round(support_m / 30))
    zs = {}
    for n in names:
        z = z30[n].astype("float64")
        if noise_m > 0:
            z = z + correlated_noise(z.shape, noise_m, rng)
        zs[n] = T.block_mean(z, k) if k > 1 else z
    res = 30.0 * k
    f = T.decision_features(zs, primary, res, t) if algorithm == "horn" else _features_alg(zs, primary, res, t, algorithm)
    ref = reference_fields(ref_fine, rf, res, t, algorithm)
    y = ref["y_A"] if ref_mode == "A" else ref["y_B"]
    ok = np.isfinite(y)
    for key in FEATURES + ["pred"]:
        ok &= np.isfinite(f[key])
    H, W = y.shape
    rr, cc = np.nonzero(ok)
    blk_px = max(int(BLOCK_M / res), 1)
    tab = {key: f[key][ok].astype("float64") for key in FEATURES + ["pred", "slope"]}
    tab["y"] = y[ok].astype("float64")
    tab["err"] = (tab["pred"] != tab["y"]).astype("float64")
    tab["block"] = (rr // blk_px) * 100000 + (cc // blk_px)
    tab["site"] = np.array([site] * len(rr))
    tab["ref_slope"] = ref["slope_A"][ok].astype("float64")
    tab["rowcol"] = np.stack([rr, cc], axis=1)
    tab["shape"] = (H, W)
    tab["mask"] = ok
    return tab


def _features_alg(zs, primary, res, t, algorithm):
    """decision_features with a non-default slope algorithm (sensitivity run)."""
    orig = T.slope_deg
    try:
        T.slope_deg = lambda z, r, method="horn": orig(z, r, algorithm)
        return T.decision_features(zs, primary, res, t)
    finally:
        T.slope_deg = orig


# ----------------------------------------------------------------------------- selective metrics
def _order(u, rng):
    jitter = rng.random(len(u))
    return np.lexsort((jitter, u))  # primary key u ascending (most confident first)


def risk_coverage(u, err, rng=None):
    rng = rng or np.random.default_rng(0)
    o = _order(u, rng)
    e = err[o]
    n = np.arange(1, len(e) + 1)
    risk = np.cumsum(e) / n
    cov = n / len(e)
    return cov, risk


def aurc(u, err, rng=None):
    return float(risk_coverage(u, err, rng)[1].mean())


def eaurc(u, err, rng=None):
    oracle = aurc(err, err, rng)
    return aurc(u, err, rng) - oracle


def risk_at_coverage(u, err, cov_levels=(0.95, 0.9, 0.8, 0.7, 0.5), rng=None):
    cov, risk = risk_coverage(u, err, rng)
    return {f"risk@{c:.2f}": float(risk[min(int(np.ceil(c * len(cov))) - 1, len(cov) - 1)]) for c in cov_levels}


# ----------------------------------------------------------------------------- logistic model
def fit_logit(X, y, l2=1.0, iters=60):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Xs = (X - mu) / sd
    Xb = np.c_[np.ones(len(Xs)), Xs]
    w = np.zeros(Xb.shape[1])
    pen = np.r_[0.0, np.ones(len(w) - 1)] * l2
    for _ in range(iters):
        z = np.clip(Xb @ w, -30, 30)
        p = 1 / (1 + np.exp(-z))
        W = p * (1 - p) + 1e-6
        g = Xb.T @ (p - y) + pen * w
        H = (Xb * W[:, None]).T @ Xb + np.diag(pen)
        step = np.linalg.solve(H, g)
        w -= step
        if np.max(np.abs(step)) < 1e-7:
            break
    return {"w": w, "mu": mu, "sd": sd}


def predict_logit(m, X):
    Xb = np.c_[np.ones(len(X)), (X - m["mu"]) / m["sd"]]
    return 1 / (1 + np.exp(-np.clip(Xb @ m["w"], -30, 30)))


def _X(tab):
    return np.stack([tab[f] for f in FEATURES], axis=1)


def _subsample(tab, n, rng):
    N = len(tab["err"])
    if N <= n:
        return np.arange(N)
    return np.sort(rng.choice(N, n, replace=False))


def cv_scores(tables, scheme="loso", folds=5, seed=0, train_cap=120000):
    """Out-of-sample p_err for the combined model.

    loso : leave-one-site-out (spatially independent territories)
    block: within-site K-fold over 1-km spatial blocks
    Returns dict site -> p_err array (same order as table pixels).
    """
    rng = np.random.default_rng(seed)
    out = {}
    names = list(tables)
    for s in names:
        tab = tables[s]
        p = np.full(len(tab["err"]), np.nan)
        if scheme == "loso":
            others = [o for o in names if o != s]
            if not others:
                continue
            Xs, ys = [], []
            for o in others:
                idx = _subsample(tables[o], train_cap // len(others), rng)
                Xs.append(_X(tables[o])[idx]); ys.append(tables[o]["err"][idx])
            m = fit_logit(np.concatenate(Xs), np.concatenate(ys))
            p = predict_logit(m, _X(tab))
        else:
            blocks = np.unique(tab["block"])
            perm = rng.permutation(len(blocks))
            fold_of = {b: perm[i] % folds for i, b in enumerate(blocks)}
            f = np.array([fold_of[b] for b in tab["block"]])
            X = _X(tab)
            for k in range(folds):
                tr, te = f != k, f == k
                if tr.sum() < 200 or te.sum() == 0:
                    continue
                idx = np.nonzero(tr)[0]
                idx = idx[_subsample({"err": tab["err"][idx]}, train_cap, rng)]
                m = fit_logit(X[idx], tab["err"][idx])
                p[te] = predict_logit(m, X[te])
        out[s] = p
    return out


def scores_for(tab, p_combined, rng=None):
    """Uncertainty score u for every method (higher = more uncertain)."""
    rng = rng or np.random.default_rng(1)
    u = {
        "random": rng.random(len(tab["err"])),
        "distance": -tab["dist"],
        "norm_margin": -tab["dist"] / (tab["dem_disagreement_std"] + 0.25),
        "dem_disagreement": tab["dem_disagreement_std"] + 0.5 * tab["vote_split"],
        "local_variability": tab["local_slope_std"],
        "scale_stability": tab["scale_instab"],
    }
    if p_combined is not None and np.all(np.isfinite(p_combined)):
        u["combined"] = p_combined
    return u


def pool(tables, sites=None):
    sites = sites or list(tables)
    keys = FEATURES + ["pred", "y", "err", "slope", "ref_slope"]
    d = {k: np.concatenate([tables[s][k] for s in sites]) for k in keys}
    d["block"] = np.concatenate([tables[s]["block"] + 10**9 * (i + 1) for i, s in enumerate(sites)])
    return d


def evaluate(tables, p_by_site, n_boot=200, seed=0, cap=80000):
    """AURC table per site and pooled, with spatial-block bootstrap CIs on pooled values and on
    differences to the distance baseline."""
    rng = np.random.default_rng(seed)
    rows = []
    for s in list(tables) + ["POOLED"]:
        tab = pool(tables) if s == "POOLED" else tables[s]
        p = np.concatenate([p_by_site[x] for x in tables]) if s == "POOLED" else p_by_site.get(s)
        u = scores_for(tab, p, rng)
        n = len(tab["err"])
        base = float(tab["err"].mean())
        for mname, uu in u.items():
            row = {"site": s, "method": mname, "n_pixels": n, "error_rate_full_coverage": base,
                   "AURC": aurc(uu, tab["err"], rng), "E_AURC": eaurc(uu, tab["err"], rng)}
            row.update(risk_at_coverage(uu, tab["err"], rng=rng))
            rows.append(row)
    # block bootstrap on pooled sample (thinned for speed)
    tab = pool(tables)
    p = np.concatenate([p_by_site[x] for x in tables])
    idx_all = _subsample(tab, cap, rng)
    sub = {k: tab[k][idx_all] for k in tab}
    p_sub = p[idx_all]
    u = scores_for(sub, p_sub, rng)
    blocks = np.unique(sub["block"])
    by_block = {b: np.nonzero(sub["block"] == b)[0] for b in blocks}
    boots = {m: [] for m in u}
    for _ in range(n_boot):
        pick = rng.choice(blocks, len(blocks), replace=True)
        idx = np.concatenate([by_block[b] for b in pick])
        for m, uu in u.items():
            boots[m].append(aurc(uu[idx], sub["err"][idx], rng))
    ci = []
    for m in u:
        a = np.array(boots[m]); d = a - np.array(boots["distance"])
        ci.append({"method": m, "AURC_boot_mean": float(a.mean()), "AURC_lo95": float(np.percentile(a, 2.5)),
                   "AURC_hi95": float(np.percentile(a, 97.5)),
                   "dAURC_vs_distance_mean": float(d.mean()), "dAURC_lo95": float(np.percentile(d, 2.5)),
                   "dAURC_hi95": float(np.percentile(d, 97.5)), "n_blocks": int(len(blocks)),
                   "n_boot": n_boot, "n_pixels_used": int(len(idx_all))})
    return rows, ci


def calibration(p, err, bins=10):
    """Reliability table for p_err, ECE and Brier (with skill vs constant error rate)."""
    q = np.quantile(p, np.linspace(0, 1, bins + 1))
    q[-1] += 1e-9
    rows, ece = [], 0.0
    for i in range(bins):
        m = (p >= q[i]) & (p < q[i + 1])
        if m.sum() == 0:
            continue
        rows.append({"bin": i, "n": int(m.sum()), "mean_p_err": float(p[m].mean()), "observed_err": float(err[m].mean())})
        ece += m.mean() * abs(p[m].mean() - err[m].mean())
    brier = float(np.mean((p - err) ** 2))
    brier0 = float(np.mean((err.mean() - err) ** 2))
    return rows, {"ECE": float(ece), "Brier": brier, "Brier_const": brier0,
                  "Brier_skill": float(1 - brier / brier0) if brier0 > 0 else None}


def choose_tau(u, err, target_risk, rng=None):
    """Largest-coverage threshold on u with selective risk <= target (on training data)."""
    rng = rng or np.random.default_rng(0)
    o = _order(u, rng)
    risk = np.cumsum(err[o]) / np.arange(1, len(o) + 1)
    good = np.nonzero(risk <= target_risk)[0]
    if len(good) == 0:
        return -np.inf
    return float(u[o][good.max()])


def decide(pred, u, tau):
    """BELOW=0 / ABOVE=1 / ABSTAIN=2."""
    d = pred.astype("int8").copy()
    d[u > tau] = 2
    return d
