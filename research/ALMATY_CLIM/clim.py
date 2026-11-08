"""CMIP6 HighResMIP (Open-Meteo Climate API): change vs 1995-2014 for 2030s/2040s/2050s, Almaty points."""
import json, sys, time, requests, numpy as np, pandas as pd

LOCS = {"Almaty_city_800m": (43.25, 76.95), "Medeu_1700m": (43.157, 77.059), "Kok-Zhailau_2000m": (43.17, 76.99)}
MODELS = ["CMCC_CM2_VHR4", "FGOALS_f3_H", "HiRAM_SIT_HR", "MRI_AGCM3_2_S", "EC_Earth3P_HR", "MPI_ESM1_2_XR", "NICAM16_8S"]
URL = "https://climate-api.open-meteo.com/v1/climate"
VARS = "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum,rain_sum,snowfall_sum"
PER = {"2030s": (2025, 2034), "2040s": (2035, 2044), "2050s": (2045, 2050)}
SEAS = {"DJF": [12, 1, 2], "MAM": [3, 4, 5], "NDJFM": [11, 12, 1, 2, 3], "year": list(range(1, 13))}


def get(lat, lon, model):
    p = dict(latitude=lat, longitude=lon, start_date="1995-01-01", end_date="2050-12-31", models=model, daily=VARS)
    for k in range(6):
        try:
            r = requests.get(URL, params=p, timeout=300)
            if r.status_code == 200:
                d = r.json()["daily"]
                df = pd.DataFrame(d); df["time"] = pd.to_datetime(df.time)
                return df
            print("retry", model, r.status_code, r.text[:200], file=sys.stderr, flush=True)
        except requests.exceptions.RequestException as e:
            print("exc", repr(e)[:100], file=sys.stderr, flush=True)
        time.sleep(30 * (k + 1))
    return None


def main(out):
    rows = []
    for name, (lat, lon) in LOCS.items():
        for m in MODELS:
            df = get(lat, lon, m); time.sleep(2)
            if df is None:
                print("skip", name, m, flush=True); continue
            tcol = [c for c in df.columns if c.startswith("temperature_2m_mean")]
            if not tcol:
                print("nocol", name, m, df.columns.tolist(), flush=True); continue
            col = lambda base: [c for c in df.columns if c.startswith(base)][0]
            t, pr, rn, sn = (df[col(b)] for b in ["temperature_2m_mean", "precipitation_sum", "rain_sum", "snowfall_sum"])
            y = df.time.dt.year; mo = df.time.dt.month
            for sname, months in SEAS.items():
                ms = mo.isin(months)
                base = (y >= 1995) & (y <= 2014) & ms
                for pn, (a, b) in PER.items():
                    sel = (y >= a) & (y <= b) & ms
                    nb = base.sum(); ns = sel.sum()
                    if ns == 0 or nb == 0: continue
                    # means per day -> compare daily means; precip/rain/snow as mean daily mm (cm)
                    rows.append(dict(point=name, model=m, season=sname, period=pn,
                                     dT=float(t[sel].mean() - t[base].mean()),
                                     dPr_pct=float(100 * (pr[sel].mean() / pr[base].mean() - 1)) if pr[base].mean() > 0 else np.nan,
                                     dRain_pct=float(100 * (rn[sel].mean() / rn[base].mean() - 1)) if rn[base].mean() > 0 else np.nan,
                                     dSnow_pct=float(100 * (sn[sel].mean() / sn[base].mean() - 1)) if sn[base].mean() > 0 else np.nan,
                                     frac_T_gt0_base=float((t[base] > 0).mean()), frac_T_gt0=float((t[sel] > 0).mean())))
            print("ok", name, m, flush=True)
    d = pd.DataFrame(rows); assert len(d) > 0, "empty"
    d.to_csv(f"{out}/cmip6_hr_delta_by_model.csv", index=False)
    num = [c for c in d.columns if c.startswith(("dT", "dPr", "dRain", "dSnow", "frac"))]
    s = d.groupby(["point", "season", "period"])[num].agg(["median", "min", "max"]).round(2)
    s.columns = ["_".join(c) for c in s.columns]; s.reset_index().to_csv(f"{out}/cmip6_hr_delta_ensemble.csv", index=False)
    json.dump({"models_ok": sorted(d.model.unique().tolist())}, open(f"{out}/meta.json", "w"))


if __name__ == "__main__":
    main(sys.argv[1])
