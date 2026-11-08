import sys, json, traceback
import planetary_computer as pc
from pystac_client import Client
cat = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=pc.sign_inplace)
col = cat.get_collection("nasa-nex-gddp-cmip6")
print("SUMMARIES", json.dumps({k: v for k, v in col.summaries.to_dict().items() if "cmip6" in k}, ensure_ascii=False)[:3000])
for model in ["UKESM1-0-LL", "INM-CM5-0", "NorESM2-MM", "CanESM5", "ACCESS-CM2"]:
    for sc, y in [("historical", 2010), ("ssp245", 2030)]:
        try:
            its = list(cat.search(collections=["nasa-nex-gddp-cmip6"], query={"cmip6:model": {"eq": model}, "cmip6:scenario": {"eq": sc}, "cmip6:year": {"eq": y}}).items())
            print(model, sc, y, "items", len(its), [list(i.assets.keys()) for i in its][:1], [i.id for i in its][:1])
        except Exception as e:
            print(model, sc, y, "ERR", repr(e)[:300])

import fsspec, xarray as xr, traceback
for model in ["UKESM1-0-LL", "INM-CM5-0", "NorESM2-MM", "CanESM5", "ACCESS-CM2"]:
    try:
        it = list(cat.search(collections=["nasa-nex-gddp-cmip6"], query={"cmip6:model": {"eq": model}, "cmip6:scenario": {"eq": "historical"}, "cmip6:year": {"eq": 2005}}).items())[0]
        href = it.assets["tas"].href
        print(model, "HREF", href.split("?")[0])
        with fsspec.open(href).open() as f:
            ds = xr.open_dataset(f, engine="h5netcdf")
            print(model, "DIMS", dict(ds.sizes), "LON", float(ds.lon.min()), float(ds.lon.max()), "LAT", float(ds.lat.min()), float(ds.lat.max()))
            v = ds["tas"].sel(lat=43.25, lon=76.95, method="nearest").load()
            print(model, "OK", v.shape, float(v.mean()))
    except Exception:
        print(model, "FAIL", traceback.format_exc()[-700:])
