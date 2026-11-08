"""Shared helpers: wet-bulb temperature, Theil-Sen/Mann-Kendall."""
import numpy as np
from scipy import stats


def sat_vp_hpa(t_c):
    return 6.112 * np.exp(17.62 * t_c / (243.12 + t_c))


def wet_bulb_c(t_c, rh_pct, p_hpa):
    """Psychrometric wet-bulb temperature (deg C), vectorised bisection. t_c deg C, rh %, p hPa."""
    t = np.asarray(t_c, float)
    rh = np.clip(np.asarray(rh_pct, float), 1.0, 100.0)
    p = np.broadcast_to(np.asarray(p_hpa, float), t.shape)
    e = rh / 100.0 * sat_vp_hpa(t)
    lo = t - 40.0
    hi = t.copy()
    for _ in range(45):
        mid = 0.5 * (lo + hi)
        gamma = 0.00066 * (1.0 + 0.00115 * mid)
        f = sat_vp_hpa(mid) - p * gamma * (t - mid) - e
        pos = f > 0
        hi = np.where(pos, mid, hi)
        lo = np.where(pos, lo, mid)
    return 0.5 * (lo + hi)


def trend_per_decade(years, values, min_n=10):
    y = np.asarray(years, float)
    v = np.asarray(values, float)
    m = np.isfinite(v)
    y, v = y[m], v[m]
    if len(v) < min_n:
        return dict(n=int(len(v)), slope_per_10yr=np.nan, p=np.nan)
    sl = stats.theilslopes(v, y)[0] * 10.0
    tau, p = stats.kendalltau(y, v)
    return dict(n=int(len(v)), slope_per_10yr=float(sl), p=float(p))
