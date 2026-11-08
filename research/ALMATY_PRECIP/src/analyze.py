import os, sys
import numpy as np, pandas as pd
from scipy.stats import kendalltau, theilslopes

def trend(y):
    y = y.dropna()
    if len(y) < 10:
        return None
    x = y.index.values.astype(float)
    sl, ic, lo, hi = theilslopes(y.values, x)
    tau, p = kendalltau(x, y.values)
    return dict(n=len(y), first=int(x.min()), last=int(x.max()), slope_per_10y=sl * 10, ci_lo=lo * 10, ci_hi=hi * 10, tau=tau, p=p)

def main(out="out"):
    rows = []
    f = os.path.join(out, "merra2_monthly_almaty.csv")
    if os.path.exists(f):
        d = pd.read_csv(f); d["month"] = pd.to_datetime(d["month"]); d["y"] = d.month.dt.year; d["m"] = d.month.dt.month
        # MERRA-2 fluxes are kg m-2 s-1 -> mm/month
        dim = d.month.dt.days_in_month * 86400
        d["P"] = d.PRECTOT * dim; d["S"] = d.PRECSNO * dim; d["R"] = d.P - d.S
        d["season"] = np.where(d.m.isin([12, 1, 2]), "DJF", np.where(d.m.isin([3, 4, 5]), "MAM", np.where(d.m.isin([6, 7, 8]), "JJA", "SON")))
        d["wy"] = np.where(d.m >= 9, d.y + 1, d.y)
        for name, sub in (("DJF", d[d.season == "DJF"]), ("MAM", d[d.season == "MAM"]), ("NOV-MAR", d[d.m.isin([11, 12, 1, 2, 3])])):
            g = sub.groupby("wy" if name != "MAM" else "y")[["P", "S", "R"]].sum()
            g["snow_share"] = g.S / g.P
            for col in ("P", "S", "R", "snow_share"):
                for w in (1980, 2001):
                    t = trend(g.loc[g.index >= w, col])
                    if t: rows.append(dict(source="MERRA-2", season=name, metric=col, window_from=w, **t))
        d.to_csv(os.path.join(out, "merra2_monthly_mm.csv"), index=False)
    f = os.path.join(out, "imerg_monthly_almaty.csv")
    if os.path.exists(f):
        d = pd.read_csv(f); d["month"] = pd.to_datetime(d["month"]); d["y"] = d.month.dt.year; d["m"] = d.month.dt.month
        d["P"] = d.precipitation * 24 * d.month.dt.days_in_month  # mm/h -> mm/month
        d["wy"] = np.where(d.m >= 9, d.y + 1, d.y)
        for name, sub in (("annual", d), ("DJF", d[d.m.isin([12, 1, 2])]), ("MAM", d[d.m.isin([3, 4, 5])])):
            g = sub.groupby("y")["P"].sum()
            t = trend(g)
            if t: rows.append(dict(source="IMERG", season=name, metric="P", window_from=2000, **t))
    pd.DataFrame(rows).round(4).to_csv(os.path.join(out, "trends_precip_phase.csv"), index=False)
    print(pd.DataFrame(rows).round(3).to_string())

if __name__ == "__main__":
    main(*sys.argv[1:])
