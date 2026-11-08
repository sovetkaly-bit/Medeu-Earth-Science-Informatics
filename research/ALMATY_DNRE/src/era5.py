"""Hourly ERA5-Land (Open-Meteo archive) -> wet-bulb, snowmaking hours Nov-Mar, trends."""
import json, sys, time, requests, numpy as np, pandas as pd
from common import wet_bulb_c, trend_per_decade

LOCS = {
    "Almaty_city_800m": (43.25, 76.95),
    "Medeu_1700m": (43.157, 77.059),
    "Shymbulak_2200m": (43.128, 77.081),
    "Kok-Zhailau_2000m": (43.17, 76.99),
    "BigAlmatyLake_2500m": (43.05, 76.99),
}
Y0, Y1 = 1991, 2025
URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch(lat, lon, y, y2=None):
    y2 = y2 or y
    p = dict(latitude=lat, longitude=lon, start_date=f"{y}-01-01", end_date=f"{y2}-12-31",
             hourly="temperature_2m,relative_humidity_2m,surface_pressure",
             models="era5_land", timezone="Asia/Almaty")
    for k in range(4):
        try:
            r = requests.get(URL, params=p, timeout=180)
        except requests.exceptions.RequestException as e:
            print("exc", y, repr(e)[:120], file=sys.stderr); time.sleep(60 * (k + 1)); continue
        if r.status_code == 200:
            h = r.json()["hourly"]
            return pd.DataFrame(h).assign(time=lambda d: pd.to_datetime(d.time))
        print("retry", y, r.status_code, r.text[:200], file=sys.stderr)
        time.sleep(60 * (k + 1))
    raise RuntimeError(f"fail {lat},{lon},{y}")


def main(out):
    rows, tr, elev = [], {}, {}
    for name, (lat, lon) in LOCS.items():
        dfs = []
        for y in range(Y0, Y1 + 1, 5):  # 5-year chunks: 7 calls per point
            dfs.append(fetch(lat, lon, y, min(y + 4, Y1))); time.sleep(5)
        d = pd.concat(dfs, ignore_index=True)
        d["tw"] = wet_bulb_c(d.temperature_2m.values, d.relative_humidity_2m.values, d.surface_pressure.values)
        d["m"] = d.time.dt.month
        d["season"] = np.where(d.m >= 7, d.time.dt.year + 1, d.time.dt.year)  # winter labelled by end year
        w = d[d.m.isin([11, 12, 1, 2, 3])]
        g = w.groupby("season").agg(
            n=("tw", "size"),
            h_tw_m2=("tw", lambda s: int((s <= -2).sum())),
            h_tw_m5=("tw", lambda s: int((s <= -5).sum())),
            h_tw_m8=("tw", lambda s: int((s <= -8).sum())),
            t_mean=("temperature_2m", "mean"), tw_mean=("tw", "mean")).reset_index()
        g = g[(g.n >= 3600) & (g.season >= Y0 + 1) & (g.season <= Y1)]
        g.insert(0, "loc", name); rows.append(g)
        # monthly snowmaking hours Tw<=-2 (mean over seasons)
        mm = w.assign(ok=w.tw <= -2).groupby(["season", "m"]).ok.sum().groupby("m").mean().round(0).to_dict()
        tr[name] = {k: trend_per_decade(g.season, g[k]) for k in ["h_tw_m2", "h_tw_m5", "t_mean", "tw_mean"]}
        tr[name]["mean_hours_by_month_tw_le_-2"] = {int(k): float(v) for k, v in mm.items()}
        tr[name]["mean_hours_season"] = {k: float(g[k].mean()) for k in ["h_tw_m2", "h_tw_m5", "h_tw_m8"]}
        print(name, tr[name]["h_tw_m2"], tr[name]["mean_hours_season"], flush=True)
    res = pd.concat(rows)
    assert len(res) > 100, "empty ERA5 result"
    res.to_csv(f"{out}/snowmaking_hours_by_season.csv", index=False)
    json.dump(tr, open(f"{out}/snowmaking_trends.json", "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1])
