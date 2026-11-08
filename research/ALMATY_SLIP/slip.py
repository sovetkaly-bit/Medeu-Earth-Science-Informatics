"""Slippery-day indicators (ERA5 daily via Open-Meteo), Oct-Apr, 1991-2025, trends per decade."""
import json, sys, time, requests, numpy as np, pandas as pd
from scipy import stats

LOCS = {"Almaty_city_800m": (43.25, 76.95), "Medeu_1700m": (43.157, 77.059), "Shymbulak_2200m": (43.128, 77.081)}
URL = "https://archive-api.open-meteo.com/v1/archive"


def get(lat, lon):
    p = dict(latitude=lat, longitude=lon, start_date="1991-01-01", end_date="2025-12-31", models="era5_seamless",
             daily="temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum,rain_sum,snowfall_sum",
             timezone="Asia/Almaty")
    for k in range(6):
        try:
            r = requests.get(URL, params=p, timeout=300)
            if r.status_code == 200:
                return pd.DataFrame(r.json()["daily"])
            print("retry", r.status_code, r.text[:150], file=sys.stderr)
        except requests.exceptions.RequestException as e:
            print("exc", repr(e)[:100], file=sys.stderr)
        time.sleep(30 * (k + 1))
    raise RuntimeError("fail")


def tr(x, y):
    m = np.isfinite(y); x = np.asarray(x)[m]; y = np.asarray(y)[m]
    return dict(slope_per_10yr=float(stats.theilslopes(y, x)[0] * 10), p=float(stats.kendalltau(x, y)[1]), mean=float(y.mean()), n=int(len(y)))


def main(out):
    res, rows = {}, []
    for name, (lat, lon) in LOCS.items():
        d = get(lat, lon); d["time"] = pd.to_datetime(d.time)
        d["m"] = d.time.dt.month
        d["season"] = np.where(d.m >= 7, d.time.dt.year + 1, d.time.dt.year)
        w = d[d.m.isin([10, 11, 12, 1, 2, 3, 4])].copy()
        tmax, tmin, tm, pr, rain, sn = (w[c] for c in ["temperature_2m_max", "temperature_2m_min", "temperature_2m_mean", "precipitation_sum", "rain_sum", "snowfall_sum"])
        w["freeze_thaw"] = (tmin < 0) & (tmax > 0)                      # переход через 0 °C за сутки
        w["wet_near0"] = (pr >= 0.5) & (tm >= -3) & (tm <= 2)             # осадки при околонулевой температуре
        w["rain_on_cold"] = (rain >= 0.5) & (tmin < -1)                  # дождь при ночном минусе -> гололёд
        w["thaw_after_snow"] = (tmax > 1) & (sn.shift(1) >= 1)           # оттепель после снегопада
        g = w.groupby("season").agg(n=("m", "size"), freeze_thaw=("freeze_thaw", "sum"), wet_near0=("wet_near0", "sum"),
                                    rain_on_cold=("rain_on_cold", "sum"), thaw_after_snow=("thaw_after_snow", "sum"),
                                    precip_OctApr=("precipitation_sum", "sum"), rain_OctApr=("rain_sum", "sum"),
                                    snow_OctApr=("snowfall_sum", "sum")).reset_index()
        g = g[(g.n >= 205) & (g.season >= 1992) & (g.season <= 2025)]
        g.insert(0, "loc", name); rows.append(g)
        res[name] = {k: tr(g.season, g[k]) for k in ["freeze_thaw", "wet_near0", "rain_on_cold", "thaw_after_snow", "precip_OctApr", "rain_OctApr", "snow_OctApr"]}
        mm = w.groupby("m")[["freeze_thaw", "wet_near0", "rain_on_cold"]].sum() / g.season.nunique()
        res[name]["mean_days_by_month"] = mm.round(1).to_dict()
        res[name]["rain_share_OctApr_pct"] = tr(g.season, 100 * g.rain_OctApr / (g.rain_OctApr + g.snow_OctApr * 0.1 + 1e-9))
        print(name, res[name]["freeze_thaw"], flush=True)
    df = pd.concat(rows); assert len(df) > 50
    df.to_csv(f"{out}/slippery_by_season.csv", index=False)
    json.dump(res, open(f"{out}/slippery_trends.json", "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
