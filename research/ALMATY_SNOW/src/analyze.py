"""Season metrics, trends and figures from the acquired tables. Offline: reads out/*.csv only."""
import json
import os

import numpy as np
import pandas as pd

from src.common import season_of, snow_run_dates, theil_sen_mk

CFG = json.load(open(os.path.join(os.path.dirname(__file__), "..", "config.json")))


def season_table(daily, cfg=None):
    """daily: columns date, band, band_px, clear_px, snow_px. Returns one row per (band, season)."""
    cfg = cfg or CFG["modis"]
    d = daily.copy()
    d["date"] = pd.to_datetime(d["date"])
    d["season"] = d["date"].map(season_of)
    d = d[d["season"].notna()].copy()
    d["season"] = d["season"].astype(int)
    d["clear_share"] = d["clear_px"] / d["band_px"]
    d["frac"] = np.where(d["clear_px"] > 0, d["snow_px"] / d["clear_px"].where(d["clear_px"] > 0), 0.0)
    rows = []
    for (band, season), g in d.groupby(["band", "season"]):
        g = g.sort_values("date")
        n_season_days = 273 if not ((season + 1) % 4 == 0 and ((season + 1) % 100 != 0 or (season + 1) % 400 == 0)) else 274
        valid = g["clear_share"] >= cfg["min_clear_share_day"]
        valid_share = float(valid.sum()) / n_season_days
        onset, end = snow_run_dates(pd.DatetimeIndex(g["date"]), g["frac"].values, g["clear_share"].values,
                                    cfg["min_clear_share_day"], cfg["snow_state_share"],
                                    cfg["run_min_obs"], cfg["run_min_span_days"])
        snow_days_valid = int(((g["frac"] >= cfg["snow_state_share"]) & valid).sum())
        accepted = valid_share >= cfg["min_valid_day_share_season"]
        s0 = pd.Timestamp("%d-09-01" % season)
        rows.append({
            "band": int(band), "season": int(season), "valid_day_share": round(valid_share, 3), "accepted": bool(accepted),
            "onset_date": onset.date().isoformat() if onset is not None else "",
            "end_date": end.date().isoformat() if end is not None else "",
            "onset_doy_from_1sep": int((onset - s0).days) if onset is not None else np.nan,
            "end_doy_from_1sep": int((end - s0).days) if end is not None else np.nan,
            "snow_state_valid_days": snow_days_valid,
            "mean_frac_valid_days": float(g.loc[valid, "frac"].mean()) if valid.any() else np.nan,
        })
    t = pd.DataFrame(rows)
    if len(t):
        t["span_days"] = t["end_doy_from_1sep"] - t["onset_doy_from_1sep"]
    return t


def monthly_table(daily):
    d = daily.copy()
    d["date"] = pd.to_datetime(d["date"])
    d["year"], d["month"] = d["date"].dt.year, d["date"].dt.month
    g = d.groupby(["band", "year", "month"]).agg(clear_px=("clear_px", "sum"), snow_px=("snow_px", "sum"),
                                                  band_px=("band_px", "sum"), days=("date", "nunique")).reset_index()
    g["snow_freq_of_clear"] = np.where(g["clear_px"] > 0, g["snow_px"] / g["clear_px"].where(g["clear_px"] > 0), np.nan)
    g["clear_share"] = g["clear_px"] / g["band_px"]
    return g


def trend_rows(season_df, min_n):
    rows = []
    for (band,), g in season_df[season_df["accepted"]].groupby(["band"]):
        for metric in ("onset_doy_from_1sep", "end_doy_from_1sep", "span_days", "snow_state_valid_days"):
            for lo in (2001, 2006):
                h = g[g["season"] >= lo]
                r = theil_sen_mk(h["season"], h[metric], min_n)
                rows.append({"band": int(band), "metric": metric, "window_from": lo,
                             **(r if r else {"n": int(h[metric].notna().sum()), "note": "n below minimum"})})
    return pd.DataFrame(rows)


def terra_trends(tc, min_n):
    rows = []
    def ann(df, col, how):
        return df.groupby("year")[col].agg(how)
    for b, g in tc.groupby("band"):
        sets = {
            "annual_precip_mm": ann(g[g["year"] <= 2023], "precip_mm", "sum"),
            "DJF_precip_mm": ann(g[g["month"].isin([12, 1, 2])], "precip_mm", "sum"),
            "MAM_precip_mm": ann(g[g["month"].isin([3, 4, 5])], "precip_mm", "sum"),
            "JJA_precip_mm": ann(g[g["month"].isin([6, 7, 8])], "precip_mm", "sum"),
            "March_swe_mm": g[g["month"] == 3].set_index("year")["swe_mm"],
            "April_swe_mm": g[g["month"] == 4].set_index("year")["swe_mm"],
            "DJF_tmean_c": ann(g[g["month"].isin([12, 1, 2])].assign(t=lambda x: (x.tmax_c + x.tmin_c) / 2), "t", "mean"),
        }
        for name, s in sets.items():
            for lo in (1970, 2001):
                h = s[s.index >= lo]
                r = theil_sen_mk(h.index.values, h.values, min_n)
                rows.append({"band": int(b), "metric": name, "window_from": lo,
                             **(r if r else {"n": int(len(h)), "note": "n below minimum"})})
    return pd.DataFrame(rows)


def figures(out, monthly, seasons):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    bands = CFG["bands_m"]
    # Fig B: heat map of snow frequency, band x time (monthly)
    fig, axes = plt.subplots(len(bands), 1, figsize=(10, 1.1 * len(bands) + 1), sharex=True)
    for i, ax in enumerate(np.atleast_1d(axes), start=1):
        g = monthly[monthly["band"] == i]
        if len(g):
            t = pd.to_datetime(dict(year=g["year"], month=g["month"], day=1))
            ax.scatter(t, [0] * len(t), c=g["snow_freq_of_clear"], cmap="Blues", vmin=0, vmax=1, marker="s", s=14)
        ax.set_yticks([]); ax.set_ylabel("%d-%d m" % tuple(bands[i - 1]), rotation=0, ha="right", va="center", fontsize=8)
    fig.suptitle("MODIS Terra MOD10A1: snow frequency among clear observations, by month and elevation band")
    fig.savefig(os.path.join(out, "figB_snow_frequency_by_band.png"), dpi=300, bbox_inches="tight"); plt.close(fig)
    # Fig C: onset/end by band, accepted seasons only
    fig, ax = plt.subplots(1, 2, figsize=(11, 4), sharex=True)
    for i in range(1, len(bands) + 1):
        g = seasons[(seasons["band"] == i) & seasons["accepted"]]
        ax[0].plot(g["season"], g["onset_doy_from_1sep"], "o-", ms=3, lw=0.8, label="%d-%d m" % tuple(bands[i - 1]))
        ax[1].plot(g["season"], g["end_doy_from_1sep"], "o-", ms=3, lw=0.8)
    ax[0].set_title("Snow onset (days from 1 Sep)"); ax[1].set_title("Snow end (days from 1 Sep)")
    ax[0].legend(fontsize=6); fig.suptitle("Accepted seasons only (valid-day share >= 50%)")
    fig.savefig(os.path.join(out, "figC_onset_end_by_band.png"), dpi=300, bbox_inches="tight"); plt.close(fig)


def main(out=None):
    out = out or os.environ.get("ALMATY_OUT", "out")
    cfg = CFG
    daily = pd.read_csv(os.path.join(out, "modis_daily_by_band.csv"))
    seasons = season_table(daily)
    monthly = monthly_table(daily)
    seasons.to_csv(os.path.join(out, "snow_season_by_band.csv"), index=False)
    monthly.to_csv(os.path.join(out, "snow_monthly_by_band.csv"), index=False)
    tr = trend_rows(seasons, cfg["trend"]["min_n"])
    tr.to_csv(os.path.join(out, "trends_snow_modis.csv"), index=False)
    p = os.path.join(out, "terraclimate_monthly_by_band.csv")
    if os.path.exists(p):
        terra_trends(pd.read_csv(p), cfg["trend"]["min_n"]).to_csv(os.path.join(out, "trends_terraclimate.csv"), index=False)
    figures(out, monthly, seasons)
    print("seasons:", len(seasons), "accepted:", int(seasons["accepted"].sum()))


if __name__ == "__main__":
    main()
