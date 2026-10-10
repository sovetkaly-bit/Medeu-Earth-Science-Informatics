"""Territory geometries from OpenStreetMap (Overpass, Nominatim fallback) with explicit provenance.

Never replaces a missing boundary by an invented square: if no polygon is found the status says so,
a *functional footprint* (buffered hull of mapped aerialways / pistes / tourism / sport features) may be
offered, clearly labelled as derived, and otherwise only a processing window is used (no territory claim).
"""
from __future__ import annotations
import math
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, mapping, shape
from shapely.ops import linemerge, polygonize, unary_union, transform as shp_transform
from pyproj import Transformer
from . import common as C

OVERPASS = ["https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]


def _query(cfg_site, radius_deg=0.12):
    lon, lat = cfg_site["center"]
    s, w, n, e = lat - radius_deg, lon - radius_deg * 1.4, lat + radius_deg, lon + radius_deg * 1.4
    bb = f"({s:.5f},{w:.5f},{n:.5f},{e:.5f})"
    rx = cfg_site["osm_name_regex"].replace('"', '\\"')
    return f"""[out:json][timeout:150];
(
  nwr["name"~"{rx}",i]{bb};
  nwr["name:ru"~"{rx}",i]{bb};
  nwr["name:en"~"{rx}",i]{bb};
  nwr["name:kk"~"{rx}",i]{bb};
  nwr["landuse"="winter_sports"]{bb};
  nwr["aerialway"]{bb};
  nwr["piste:type"]{bb};
  nwr["tourism"~"resort|attraction|viewpoint|alpine_hut|hotel|camp_site|theme_park"]{bb};
  nwr["leisure"~"sports_centre|ice_rink|stadium|pitch|resort|park|nature_reserve"]{bb};
  nwr["boundary"~"protected_area|national_park"]{bb};
);
out geom tags;""", (s, w, n, e)


def _coords(g):
    return [(p["lon"], p["lat"]) for p in g]


def _element_geom(el):
    t = el["type"]
    try:
        if t == "node":
            return Point(el["lon"], el["lat"])
        if t == "way" and el.get("geometry"):
            c = _coords(el["geometry"])
            if len(c) >= 4 and c[0] == c[-1]:
                tags = el.get("tags", {})
                is_line = bool(tags.get("aerialway")) or (
                    bool(tags.get("piste:type")) and tags.get("area") != "yes" and tags.get("landuse") != "winter_sports")
                if not is_line:
                    return Polygon(c).buffer(0)
            return LineString(c) if len(c) >= 2 else None
        if t == "relation":
            outers, inners = [], []
            for m in el.get("members", []):
                if m.get("type") != "way" or not m.get("geometry"):
                    continue
                ls = LineString(_coords(m["geometry"]))
                (inners if m.get("role") == "inner" else outers).append(ls)
            if not outers:
                return None
            polys = list(polygonize(linemerge(outers)))
            if not polys:
                return None
            outer = unary_union(polys)
            if inners:
                hol = list(polygonize(linemerge(inners)))
                if hol:
                    outer = outer.difference(unary_union(hol))
            return outer.buffer(0)
    except Exception:  # noqa: BLE001
        return None
    return None


def _prio(tags):
    if tags.get("landuse") == "winter_sports" or tags.get("leisure") == "resort" or tags.get("tourism") == "resort":
        return 0
    if tags.get("boundary") in ("protected_area", "national_park") or tags.get("leisure") in ("park", "nature_reserve"):
        return 1
    if tags.get("leisure") in ("sports_centre", "stadium", "ice_rink", "pitch") or tags.get("tourism") in ("attraction", "theme_park", "camp_site"):
        return 2
    if tags.get("natural") in ("plateau", "valley", "peak") or tags.get("place") in ("locality", "square"):
        return 3
    return 9


def _area_km2(g, to_utm):
    return shp_transform(to_utm, g).area / 1e6


def fetch_site(site, cfg_site):
    """Return dict with territory polygon (WGS84), status and provenance."""
    lon0, lat0 = cfg_site["center"]
    epsg = C.utm_epsg(lon0, lat0)
    to_utm = Transformer.from_crs(4326, epsg, always_xy=True).transform
    to_wgs = Transformer.from_crs(epsg, 4326, always_xy=True).transform
    q, bbox = _query(cfg_site)
    prov = {"site": site, "queried_at": C.now(), "osm_query": q, "bbox_s_w_n_e": bbox, "config_center_lonlat": [lon0, lat0]}
    elements, used = None, None
    for url in OVERPASS:
        try:
            r = C.http_json(url, data={"data": q}, timeout=170, retries=2)
            elements, used = r.get("elements", []), url
            break
        except Exception as e:  # noqa: BLE001
            prov.setdefault("overpass_errors", []).append(f"{url}: {e!r}"[:300])
    if elements is None:
        prov["status"] = "OVERPASS_UNAVAILABLE"
        return {"territory": None, "footprint": None, "status": "OVERPASS_UNAVAILABLE", "prov": prov, "candidates": []}
    prov["overpass_endpoint"] = used
    prov["n_elements"] = len(elements)
    import re
    rx = re.compile(cfg_site["osm_name_regex"], re.I)
    cands, feats = [], []
    for el in elements:
        tags = el.get("tags", {})
        g = _element_geom(el)
        if g is None or g.is_empty:
            continue
        names = " | ".join(tags.get(k, "") for k in ("name", "name:ru", "name:en", "name:kk"))
        named = bool(rx.search(names))
        row = {"osm": f"{el['type']}/{el['id']}", "name": tags.get("name") or tags.get("name:en") or "",
               "named_match": named, "geom_type": g.geom_type, "prio": _prio(tags),
               "tags": {k: v for k, v in tags.items() if k in ("landuse", "leisure", "tourism", "natural", "boundary", "place", "sport", "aerialway", "piste:type", "protect_class")}}
        c = g.centroid
        row["dist_to_config_center_km"] = round(Point(*to_utm(c.x, c.y)).distance(Point(*to_utm(lon0, lat0))) / 1000, 3)
        if g.geom_type in ("Polygon", "MultiPolygon"):
            row["area_km2"] = round(_area_km2(g, to_utm), 4)
        cands.append((row, g))
        if row["dist_to_config_center_km"] <= cfg_site.get("footprint_radius_km", 3.5) and (
                tags.get("aerialway") or tags.get("piste:type") or tags.get("tourism") or tags.get("leisure")):
            feats.append(g)
    prov["n_candidates"] = len(cands)
    amin, amax = cfg_site.get("polygon_area_km2", [0.02, 150.0])
    polys = [(r, g) for r, g in cands if r["named_match"] and "area_km2" in r and amin <= r["area_km2"] <= amax]
    polys.sort(key=lambda x: (x[0]["prio"], x[0]["dist_to_config_center_km"]))
    territory, status, chosen = None, "NO_OSM_POLYGON_FOUND", None
    if polys:
        chosen, territory = polys[0]
        status = "OSM_POLYGON_NAMED_MATCH"
        prov["selection_rule"] = ("named OSM polygon, area within bounds; priority winter_sports/resort < protected area/park < sports/tourism "
                                  "< natural/place; ties by distance to configured centre")
        prov["chosen"] = chosen
    footprint = None
    if feats:
        try:
            u = shp_transform(to_utm, unary_union(feats))
            fp = u.buffer(250).buffer(-200)
            if fp.is_empty:
                fp = u.buffer(150)
            footprint = shp_transform(to_wgs, fp)
            prov["footprint_note"] = ("DERIVED from mapped aerialway/piste/tourism/leisure features within "
                                      f"{cfg_site.get('footprint_radius_km', 3.5)} km of the configured centre, buffered 250 m then eroded 200 m; "
                                      "NOT an official boundary")
            prov["footprint_area_km2"] = round(fp.area / 1e6, 4)
            prov["n_footprint_features"] = len(feats)
        except Exception as e:  # noqa: BLE001
            prov["footprint_error"] = repr(e)
    if territory is None and footprint is not None and prov.get("footprint_area_km2", 0) >= 0.1:
        status = "FUNCTIONAL_FOOTPRINT_ONLY"
    prov["status"] = status
    cand_rows = [r for r, _ in sorted(cands, key=lambda x: (not x[0]["named_match"], x[0]["prio"], x[0]["dist_to_config_center_km"]))][:200]
    return {"territory": territory, "footprint": footprint, "status": status, "prov": prov, "candidates": cand_rows,
            "named_nodes": [r for r, g in cands if r["named_match"] and g.geom_type == "Point"][:20]}


def nominatim_fallback(site, cfg_site):
    """Secondary lookup (single request) when Overpass gave no named polygon."""
    try:
        import time
        time.sleep(1.2)
        res = C.http_json("https://nominatim.openstreetmap.org/search",
                          params={"q": cfg_site.get("nominatim_query", site), "format": "jsonv2", "polygon_geojson": 1, "limit": 5,
                                  "viewbox": "{},{},{},{}".format(cfg_site["center"][0] - 0.3, cfg_site["center"][1] + 0.3,
                                                                    cfg_site["center"][0] + 0.3, cfg_site["center"][1] - 0.3), "bounded": 1})
        out = []
        for r in res:
            g = r.get("geojson")
            out.append({"osm": f"{r.get('osm_type')}/{r.get('osm_id')}", "display_name": r.get("display_name"), "category": r.get("category"),
                        "type": r.get("type"), "geom_type": (g or {}).get("type"), "lat": r.get("lat"), "lon": r.get("lon")})
        return out
    except Exception as e:  # noqa: BLE001
        return [{"error": repr(e)}]


def to_geojson(items):
    feats = []
    for it in items:
        if it["geom"] is None:
            continue
        feats.append({"type": "Feature", "geometry": mapping(it["geom"]), "properties": it["props"]})
    return {"type": "FeatureCollection", "features": feats}
