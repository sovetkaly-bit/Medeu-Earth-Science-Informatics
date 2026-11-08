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
