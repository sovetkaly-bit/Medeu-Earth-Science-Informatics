"""Free regional context layers: USGS earthquake catalogue, OSM protected areas and waterways. Context only."""
from __future__ import annotations
import math
from . import common as C

BBOX = (76.85, 43.05, 77.20, 43.25)
LON, LAT = 77.06, 43.14


def quakes(minmag=4.0, radius_km=150, start="1900-01-01"):
    j = C.http_json("https://earthquake.usgs.gov/fdsnws/event/1/query",
                    params={"format": "geojson", "latitude": LAT, "longitude": LON, "maxradiuskm": radius_km, "minmagnitude": minmag,
                            "starttime": start, "orderby": "magnitude", "limit": 2000})
    rows = []
    for f in j.get("features", []):
        p, (x, y, z) = f["properties"], f["geometry"]["coordinates"]
        d = 6371 * math.acos(min(1, math.sin(math.radians(LAT)) * math.sin(math.radians(y)) + math.cos(math.radians(LAT)) * math.cos(math.radians(y)) * math.cos(math.radians(x - LON))))
        rows.append({"time": p.get("time"), "mag": p.get("mag"), "depth_km": z, "lon": x, "lat": y, "dist_km": round(d, 1), "place": p.get("place")})
    return rows


def osm_context():
    s, w, n, e = BBOX[1] - 0.05, BBOX[0] - 0.05, BBOX[3] + 0.05, BBOX[2] + 0.05
    q = f"""[out:json][timeout:120];(
 nwr["boundary"~"protected_area|national_park"]({s},{w},{n},{e});
 nwr["leisure"="nature_reserve"]({s},{w},{n},{e});
 way["waterway"~"river|stream|canal|drain"]({s},{w},{n},{e});
 way["natural"="water"]({s},{w},{n},{e});
 way["landslide"]({s},{w},{n},{e}); nwr["hazard"]({s},{w},{n},{e}); nwr["man_made"="dam"]({s},{w},{n},{e});
);out geom tags;"""
    from .boundaries import OVERPASS
    last = None
    for _ in range(3):
        for u in OVERPASS:
            try:
                return C.http_json(u, data={"data": q}, timeout=150, retries=1).get("elements", [])
            except Exception as ex:  # noqa: BLE001
                last = repr(ex)[:200]
    raise RuntimeError(last)


def main():
    out = C.OUT
    out.mkdir(parents=True, exist_ok=True)
    try:
        q = quakes()
        C.write_csv(out / "usgs_quakes_M4_150km.csv", q)
        big = [r for r in q if r["mag"] and r["mag"] >= 6]
        C.write_json(out / "quakes_summary.json", {"n_M4plus": len(q), "n_M6plus": len(big), "nearest_M6": sorted(big, key=lambda r: r["dist_km"])[:5],
                                                    "source": "USGS ComCat FDSN, radius 150 km around 77.06E 43.14N, since 1900; catalogue completeness varies in time"})
        print("quakes", len(q), flush=True)
    except Exception as e:  # noqa: BLE001
        C.write_json(out / "quakes_error.json", {"error": repr(e)})
    try:
        els = osm_context()
        tags = {}
        for el in els:
            t = el.get("tags", {})
            k = next((x for x in ("boundary", "leisure", "waterway", "natural", "landslide", "hazard", "man_made") if x in t), "other")
            tags[f"{k}={t.get(k)}"] = tags.get(f"{k}={t.get(k)}", 0) + 1
        C.write_json(out / "osm_context_summary.json", {"n_elements": len(els), "counts": tags})
        C.write_json(out / "osm_context_raw.json", els)
        print("osm", len(els), flush=True)
    except Exception as e:  # noqa: BLE001
        C.write_json(out / "osm_error.json", {"error": repr(e)})


if __name__ == "__main__":
    main()
