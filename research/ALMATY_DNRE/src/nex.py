"""NEX-GDDP-CMIP6 (Planetary Computer): delta-method change for Almaty mountain points."""
import json, sys, warnings, numpy as np, pandas as pd, xarray as xr
import planetary_computer as pc
from pystac_client import Client
warnings.filterwarnings("ignore")

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
PTS = {"Almaty_city": (43.25, 76.95), "Medeu": (43.157, 77.059), "Kok-Zhailau": (43.17, 76.99)}
MODELS = ["ACCESS-CM2", "CanESM5", "MPI-ESM1-2-HR", "MRI-ESM2-0", "NorESM2-MM", "UKESM1-0-LL", "INM-CM5-0", "EC-Earth3"]
SCEN = ["ssp245", "ssp585"]
VARS = ["tas", "pr"]
PERIODS = {"base": (1995, 2014), "2030": (2025, 2034), "2040": (2035, 2044), "2050": (2045, 2054)}
cat = Client.open(STAC, modifier=pc.sign_inplace)


def series(model, scen, var, years, lat, lon):
    """Return DataArray (time) at nearest grid cell for given years."""
    out = []
    for y in years:
        sc = "historical" if y <= 2014 else scen
        items = list(cat.search(collections=["nasa-nex-gddp-cmip6"],
                                query={"cmip6:model": {"eq": model}, "cmip6:scenario": {"eq": sc}, "cmip6:year": {"eq": y}}).items())
        if not items:
            return None
        it = items[0]
        if var not in it.assets:
            return None
        ds = xr.open_dataset(it.assets[var].href + "", engine="h5netcdf")
        lo = lon if ds.lon.max() <= 180 else lon % 360
        out.append(ds[var].sel(lat=lat, lon=lo, method="nearest").load())
    return xr.concat(out, "time")


def main(out):
    rec = []
    for model in MODELS:
        for scen in SCEN:
            for pname, (lat, lon) in PTS.items():
                try:
                    res = {}
                    for var in VARS:
                        base = series(model, scen, var, range(2005, 2015), lat, lon)  # 10 yr of historical tail (compute-limited)
                        res[var] = {"base": base}
                        for p in ["2030", "2040", "2050"]:
                            a, b = PERIODS[p]
                            res[var][p] = series(model, scen, var, range(a, b + 1), lat, lon)
                    if any(v is None for r in res.values() for v in r.values()):
                        print("skip", model, scen, pname, flush=True); continue
                    def seas(da, months, fn):
                        s = da.sel(time=da.time.dt.month.isin(months))
                        return float(fn(s))
                    for p in ["2030", "2040", "2050"]:
                        row = dict(model=model, scen=scen, point=pname, period=p)
                        for sname, months in {"DJF": [12, 1, 2], "MAM": [3, 4, 5], "JJA": [6, 7, 8], "SON": [9, 10, 11], "NDJFM": [11, 12, 1, 2, 3], "year": list(range(1, 13))}.items():
                            row[f"dT_{sname}"] = seas(res["tas"][p], months, np.mean) - seas(res["tas"]["base"], months, np.mean)
                            b_pr = seas(res["pr"]["base"], months, np.mean)
                            row[f"dPr_{sname}_pct"] = 100 * (seas(res["pr"][p], months, np.mean) / b_pr - 1) if b_pr > 0 else np.nan
                        # share of days with tas>0 in DJF (warm-winter proxy for rain instead of snow)
                        f = lambda da: float((da.sel(time=da.time.dt.month.isin([12, 1, 2])) - 273.15 > 0).mean())
                        row["frac_days_T>0_DJF_base"] = f(res["tas"]["base"]); row["frac_days_T>0_DJF"] = f(res["tas"][p])
                        rec.append(row)
                    print("ok", model, scen, pname, flush=True)
                except Exception as e:
                    print("ERR", model, scen, pname, repr(e)[:200], flush=True)
    df = pd.DataFrame(rec)
    assert len(df) > 0, "empty NEX result"
    df.to_csv(f"{out}/nex_delta_by_model.csv", index=False)
    num = df.select_dtypes("number").columns
    summ = df.groupby(["scen", "point", "period"])[list(num)].agg(["median", "min", "max"]).round(2)
    summ.columns = ["_".join(c) for c in summ.columns]
    summ.reset_index().to_csv(f"{out}/nex_delta_ensemble.csv", index=False)
    json.dump({"models_ok": sorted(df.model.unique().tolist()), "n_rows": len(df)}, open(f"{out}/nex_meta.json", "w"))


if __name__ == "__main__":
    main(sys.argv[1])
