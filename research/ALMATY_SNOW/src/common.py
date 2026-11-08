"""Pure helpers: bands, season run detection, trends. No network access here."""
import numpy as np
import pandas as pd
from scipy import stats


def assign_bands(elev, bands):
    """Return int array: band index 1..N by elevation (m), 0 where outside bands or NaN."""
    out = np.zeros(elev.shape, dtype=np.uint8)
    for i, (lo, hi) in enumerate(bands, start=1):
        out[(elev >= lo) & (elev < hi)] = i
    return out


def season_of(date):
    """Season label = year of the 1 Sep start (Sep Y .. May Y+1 -> Y); None for Jun-Aug."""
    if date.month >= 9:
        return date.year
    if date.month <= 5:
        return date.year - 1
    return None


def snow_run_dates(dates, frac, clear_share, min_clear_share, snow_state_share, run_min_obs, run_min_span_days):
    """First and last date of a run of valid observations that are all snow-covered.

    dates: sorted pandas.DatetimeIndex; frac: snow share among clear pixels; clear_share: clear pixels / band pixels.
    A day is valid if clear_share >= min_clear_share; snow state if frac >= snow_state_share.
    A run = at least run_min_obs consecutive valid observations in snow state spanning >= run_min_span_days.
    Onset = first date of the first run; end = last date of the last run. Cloud gaps do not break a run.
    """
    valid = clear_share >= min_clear_share
    d = pd.DatetimeIndex(dates)[valid]
    s = (np.asarray(frac)[valid] >= snow_state_share)
    runs = []
    i = 0
    n = len(d)
    while i < n:
        if s[i]:
            j = i
            while j + 1 < n and s[j + 1]:
                j += 1
            if (j - i + 1) >= run_min_obs and (d[j] - d[i]).days >= run_min_span_days:
                runs.append((d[i], d[j]))
            i = j + 1
        else:
            i += 1
    if not runs:
        return None, None
    return runs[0][0], runs[-1][1]


def theil_sen_mk(years, values, min_n=10):
    """Theil-Sen slope per 10 years with 95% interval and Mann-Kendall (Kendall tau) p. None if n < min_n."""
    x = np.asarray(years, dtype=float)
    y = np.asarray(values, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < min_n:
        return None
    slope, intercept, lo, hi = stats.theilslopes(y, x, 0.95)
    tau, p = stats.kendalltau(x, y)
    return {"n": int(len(x)), "first": int(x.min()), "last": int(x.max()),
            "slope_per_10y": float(slope * 10), "ci_lo_per_10y": float(lo * 10), "ci_hi_per_10y": float(hi * 10),
            "tau": float(tau), "p": float(p)}
