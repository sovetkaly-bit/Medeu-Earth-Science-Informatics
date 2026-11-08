"""NEX-GDDP-CMIP6 for one model x scenario, 3 Almaty points at once. Delta vs 2005-2014 (historical tail)."""
import json, sys, warnings, numpy as np, pandas as pd, xarray as xr, fsspec
import planetary_computer as pc
from pystac_client import Client
warnings.filterwarnings("ignore")
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
PTS = {"Almaty_city": (43.25, 76.95), "Medeu": (43.157, 77.059), "Kok-Zhailau": (43.17, 76.99)}
PERIODS = {"2030s": (2025, 2034), "2040s": (2035, 2044), "2050s": (2045, 2054)}
SEAS = {"DJF": [12, 1, 2], "MAM": [3, 4, 5], "NDJFM": [11, 12, 1, 2, 3], "year": list(range(1, 13))}
cat = Client.open(STAC, modifier=pc.sign_inplace)


def year_data(model, scen, var, y):
    sc = "historical" if y <= 2014 else scen
    items = list(cat.search(collections=["nasa-nex-gddp-cmip6"], query={"cmip6:model": {"eq": model}, "cmip6:scenario": {"eq": sc}, "cmip6:year": {"eq": y}}).items())
    if not items or var not in items[0].assets:
        raise RuntimeError(f"no item {model} {sc} {y} {var}")
    href = items[0].assets[var].href
    with fsspec.open(href).open() as f:
        ds = xr.open_dataset(f, engine="h5netcdf")
        out = {}
        for n, (lat, lon) in PTS.items():
            lo = lon if float(ds.lon.max()) <= 180 else lon % 360
            out[n] = ds[var].sel(lat=lat, lon=lo, method="nearest").load()
    return out


def series(model, scen, var, years):
    import time
    parts = {n: [] for n in PTS}
    for y in years:
        for k in range(5):
            try:
                d = year_data(model, scen, var, y); break
            except Exception as e:
                print("retry", model, scen, var, y, k, repr(e)[:150], flush=True); time.sleep(30 * (k + 1))
        else:
            raise RuntimeError(f"giving up {model} {scen} {var} {y}")
        for n in PTS: parts[n].append(d[n])
        print("got", model, scen, var, y, flush=True)
    return {n: xr.concat(parts[n], "time") for n in PTS}


def main(out, model, scen):
    S = {}
    for var in ["tas", "pr"]:
        S[var] = {"base": series(model, scen, var, range(2005, 2015))}
        for p, (a, b) in PERIODS.items():
            S[var][p] = series(model, scen, var, range(a, b + 1))
    rows = []
    for n in PTS:
        for p in PERIODS:
            for sn, months in SEAS.items():
                def m(var, per):
                    da = S[var][per][n]; return float(da.sel(time=da.time.dt.month.isin(months)).mean())
                tb, tp = m("tas", "base"), m("tas", p)
                prb, prp = m("pr", "base"), m("pr", p)
                fz = lambda per: float((S["tas"][per][n].sel(time=S["tas"][per][n].time.dt.month.isin(months)) - 273.15 > 0).mean())
                rows.append(dict(model=model, scen=scen, point=n, period=p, season=sn, dT=tp - tb,
                                 dPr_pct=100 * (prp / prb - 1) if prb > 0 else np.nan,
                                 frac_T_gt0_base=fz("base"), frac_T_gt0=fz(p)))
    pd.DataFrame(rows).to_csv(f"{out}/nex_{model}_{scen}.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
