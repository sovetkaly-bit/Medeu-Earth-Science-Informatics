"""R40 reproducible cartography: rasters, polygons, figures A-E, summary tables, manifest.

Two stages (both failure-tolerant; every problem lands in exceptions_report.*, nothing is hidden or simulated):

  acquire : copy valid rasters/polygons/tables from the published result branches (r40-results, r40-icesat2), verify their
            SHA-256 against the original run, fetch what was never published (native lidar-DTM windows for the profiles,
            Natural Earth base layers) from official sources.
  build   : OFFLINE. Uses only the package `inputs/` folder; writes derived rasters (nodata masks, pixel-to-polygon masks, aligned common
            grid), vector layers, figures (PNG 300 dpi + PDF + SVG), CSV summaries, verification against decisions_by_site.csv,
            manifest.csv, README.

Usage (from research/R40_KZ):
  python -m src.cartography acquire --assets ASSETS_DIR --package PKG
  python -m src.cartography build   --package PKG [--out OUT]
"""
from __future__ import annotations
import argparse, csv, datetime as dt, json, math, os, shutil, sys, traceback
from pathlib import Path
import numpy as np
from . import common as C
from . import carto_lib as L

CODE_ROOT = Path(__file__).resolve().parents[1]
KZ = ["medeu", "shymbulak", "kok_zhailau", "kok_zhailau_osm"]
VAL = ["davos_parsenn", "zermatt_gornergrat", "alta_snowbird", "park_city"]
THRESH = [7.5, 15, 25]
LABEL = {
    "medeu": "Medeu", "shymbulak": "Shymbulak",
    "kok_zhailau": "Kok-Zhailau, variant 1 (configured centre, provisional)",
    "kok_zhailau_osm": "Kok-Zhailau, variant 2 (centre from OSM-named objects)",
    "davos_parsenn": "Davos-Parsenn (CH)", "zermatt_gornergrat": "Zermatt-Gornergrat (CH)",
    "alta_snowbird": "Alta-Snowbird (US)", "park_city": "Park City (US)"}
SHORT = {"medeu": "Medeu", "shymbulak": "Shymbulak", "kok_zhailau": "Kok-Zhailau V1", "kok_zhailau_osm": "Kok-Zhailau V2",
         "davos_parsenn": "Davos-Parsenn", "zermatt_gornergrat": "Zermatt-Gornergrat", "alta_snowbird": "Alta-Snowbird", "park_city": "Park City"}
ATL08_FILE = {"kz_all": "atl08_kz_all.csv", "davos_parsenn": "atl08_davos_parsenn.csv", "zermatt_gornergrat": "atl08_zermatt_gornergrat.csv",
              "alta_snowbird": "atl08_alta_snowbird.csv", "park_city": "atl08_park_city.csv"}
KZ_BBOX = (76.85, 43.05, 77.20, 43.25)  # W, S, E, N  (ICESat-2 / Figure A inset window)
DEM_META = {
    "cop-dem-glo-30": dict(label="Copernicus GLO-30 (DSM)", datum="EGM2008 orthometric", licence="Copernicus DEM licence: free, attribution 'Contains modified Copernicus data'"),
    "nasadem": dict(label="NASADEM (DSM)", datum="EGM96 orthometric", licence="NASA/USGS public domain"),
}
LICENCE = {
    "osm": "OpenStreetMap contributors, ODbL 1.0 (attribution + share-alike for databases)",
    "ne": "Natural Earth, public domain",
    "atl08": "NASA ICESat-2 ATL08 v007 (NSIDC DAAC), open data",
    "swiss": "swisstopo OGD swissALTI3D: free use, attribution 'Swiss Federal Office of Topography swisstopo'",
    "3dep": "USGS 3DEP: public domain",
    "own": "Derived product of this repository (code licence: see repository); inherits the licence of its sources",
}
NE_URLS = {
    "ne_110m_admin_0_countries.zip": ["https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip",
                                      "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip"],
    "ne_50m_admin_0_countries.zip": ["https://naciscdn.org/naturalearth/50m/cultural/ne_50m_admin_0_countries.zip",
                                     "https://naturalearth.s3.amazonaws.com/50m_cultural/ne_50m_admin_0_countries.zip"],
}
EXC: list[dict] = []   # exceptions report rows


def exc(severity, area, message, detail=""):
    EXC.append(dict(severity=severity, area=area, message=message, detail=str(detail)[:1500]))
    print(f"[EXC:{severity}] {area}: {message} {str(detail)[:200]}", flush=True)


def exc_tb(area, message, e):
    exc("ERROR", area, f"{message}: {e!r}", traceback.format_exc()[-1200:])


# ======================================================================================================== I/O helpers
def read_raster(path):
    import rasterio
    with rasterio.open(path) as ds:
        a = ds.read(1)
        meta = dict(crs=ds.crs.to_string(), epsg=ds.crs.to_epsg(), transform=ds.transform, res=float(ds.res[0]), bounds=tuple(ds.bounds),
                    nodata=ds.nodata, width=ds.width, height=ds.height, dtype=ds.dtypes[0], x0=float(ds.bounds.left), y1=float(ds.bounds.top))
    return a, meta


def write_tif(path, arr, meta, nodata=None, dtype=None, descr=None):
    import rasterio
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    dtype = dtype or str(arr.dtype)
    kw = dict(driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1, dtype=dtype, crs=meta["crs"], transform=meta["transform"],
              nodata=nodata, compress="deflate")
    if dtype == "float32":
        kw["predictor"] = 3
    with rasterio.open(path, "w", **kw) as o:
        o.write(arr.astype(dtype), 1)
        if descr:
            o.set_band_description(1, descr)


def extent_of(meta):
    b = meta["bounds"]
    return (b[0], b[2], b[1], b[3])  # left, right, bottom, top


def project(g, epsg, inverse=False):
    import shapely
    from pyproj import Transformer
    if g is None:
        return None
    tr = Transformer.from_crs(epsg, 4326, always_xy=True) if inverse else Transformer.from_crs(4326, epsg, always_xy=True)

    def _t(coords):
        x, y = tr.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([x, y])
    return shapely.transform(g, _t)


def rasterize_mask(g_utm, meta):
    from rasterio.features import rasterize
    if g_utm is None or g_utm.is_empty:
        return None
    m = rasterize([(g_utm, 1)], out_shape=(meta["height"], meta["width"]), transform=meta["transform"], fill=0, dtype="uint8").astype(bool)
    return m if m.sum() > 0 else None


def sha256(p):
    return C.sha256(p)


def git_head(path):
    import subprocess
    try:
        return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


class Manifest:
    COLS = ["path", "role", "source_url_or_product", "pixel_resolution_m", "crs", "vertical_datum", "extent_native_xmin_ymin_xmax_ymax",
            "extent_wgs84_W_S_E_N", "acquisition_dates", "licence_constraints", "sha256", "size_bytes", "generation_commit", "generation_run_id", "notes"]

    def __init__(self, root):
        self.root = Path(root)
        self.rows: dict[str, dict] = {}

    def add(self, path, role, source, datum="", dates="", licence="", notes="", res="", crs=""):
        rel = str(Path(path).relative_to(self.root)).replace("\\", "/")
        self.rows[rel] = dict(path=rel, role=role, source_url_or_product=source, vertical_datum=datum, acquisition_dates=dates,
                              licence_constraints=licence, notes=notes, pixel_resolution_m=res, crs=crs)

    def finalize(self, commit, run_id, skip=("manifest.csv",)):
        out = []
        files = sorted(p for p in self.root.rglob("*") if p.is_file() and p.name not in skip)
        for p in files:
            rel = str(p.relative_to(self.root)).replace("\\", "/")
            r = self.rows.get(rel)
            if r is None:
                r = dict(path=rel, role="UNREGISTERED", source_url_or_product="", notes="file not registered by the generating script")
                exc("WARN", "manifest", "unregistered file", rel)
            r = dict(r)
            self._auto(p, r)
            r["sha256"] = sha256(p)
            r["size_bytes"] = p.stat().st_size
            r["generation_commit"] = commit
            r["generation_run_id"] = run_id
            out.append(r)
        missing = [k for k in self.rows if not (self.root / k).exists()]
        for k in missing:
            exc("WARN", "manifest", "registered but missing file", k)
        with (self.root / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=self.COLS, extrasaction="ignore")
            w.writeheader()
            w.writerows(out)
        return out

    @staticmethod
    def _auto(p, r):
        try:
            if p.suffix.lower() in (".tif", ".tiff"):
                import rasterio
                from rasterio.warp import transform_bounds
                with rasterio.open(p) as ds:
                    r["crs"] = ds.crs.to_string() if ds.crs else ""
                    r["pixel_resolution_m"] = f"{ds.res[0]:g}"
                    b = ds.bounds
                    r["extent_native_xmin_ymin_xmax_ymax"] = f"{b.left:.2f},{b.bottom:.2f},{b.right:.2f},{b.top:.2f}"
                    if ds.crs:
                        w = transform_bounds(ds.crs, "EPSG:4326", *b)
                        r["extent_wgs84_W_S_E_N"] = ",".join(f"{v:.5f}" for v in w)
            elif p.suffix.lower() in (".gpkg", ".geojson"):
                import geopandas as gpd
                if p.suffix.lower() == ".gpkg":
                    import pyogrio
                    layers = [x[0] for x in pyogrio.list_layers(p)]
                    bb = []
                    for ly in layers:
                        g = gpd.read_file(p, layer=ly)
                        if len(g):
                            bb.append(g.to_crs(4326).total_bounds)
                    r["notes"] = (r.get("notes", "") + f" layers={'|'.join(layers)}").strip()
                else:
                    g = gpd.read_file(p)
                    bb = [g.to_crs(4326).total_bounds] if len(g) else []
                r["crs"] = r.get("crs") or "EPSG:4326"
                if bb:
                    a = np.array(bb)
                    r["extent_wgs84_W_S_E_N"] = ",".join(f"{v:.5f}" for v in (a[:, 0].min(), a[:, 1].min(), a[:, 2].max(), a[:, 3].max()))
        except Exception as e:  # noqa: BLE001
            exc("WARN", "manifest", f"could not read extent of {p.name}", repr(e))


# ======================================================================================================== ACQUIRE
def kz_files(t=None):
    f = ["cop-dem-glo-30_elevation_m.tif", "cop-dem-glo-30_slope_deg_horn.tif", "nasadem_elevation_m.tif", "nasadem_slope_deg_horn.tif"]
    for t in THRESH:
        f += [f"decision_combined_t{t}_risk2.tif", f"p_error_combined_t{t}.tif"]
    return f


def val_files():
    return ["cop-dem-glo-30_elevation_m.tif", "cop-dem-glo-30_slope_deg_horn.tif", "nasadem_elevation_m.tif", "nasadem_slope_deg_horn.tif",
            "reference_dtm_30m_blockmean_m.tif", "reference_slope_30m_deg.tif"]


def acquire(assets, pkg, native=True, ne=True):
    assets, pkg = Path(assets), Path(pkg)
    res, ice = assets / "r40-results", assets / "r40-icesat2"
    inp = pkg / "inputs"
    commits = {"r40-results": git_head(res), "r40-icesat2": git_head(ice), "r40-extra": git_head(assets / "r40-extra"),
               "code_main": os.environ.get("GITHUB_SHA", git_head(CODE_ROOT.parent.parent))}
    if (assets / "commits.json").exists():
        try:
            commits.update(json.loads((assets / "commits.json").read_text()))
        except Exception:  # noqa: BLE001
            pass
    C.write_json(inp / "provenance" / "asset_commits.json", commits)
    inv = assets / "actions_artifacts.json"
    if inv.exists():
        shutil.copy2(inv, inp / "provenance" / "actions_artifacts_inventory.json")
        try:
            arts = json.loads(inv.read_text(encoding="utf-8"))
            C.log("cartography", "actions-artifacts", "INVENTORY", f"{len(arts)} artifacts, {sum(1 for a in arts if not a.get('expired'))} not expired")
        except Exception as e:  # noqa: BLE001
            exc("WARN", "acquire", "Actions artifact inventory unreadable", repr(e))
    else:
        exc("WARN", "acquire", "inventory of existing Actions artifacts not available in this run")
    # integrity table of the original run
    orig = {}
    sh = res / "sha256.txt"
    if sh.exists():
        for line in sh.read_text(encoding="utf-8").splitlines():
            if "  " in line:
                h, p = line.split("  ", 1)
                orig[p.strip()] = h.strip()
    else:
        exc("WARN", "acquire", "r40-results/sha256.txt missing; integrity of reused rasters cannot be checked")
    n_ok = n_bad = 0
    integ = []

    def reuse(src_rel, dst_rel):
        nonlocal n_ok, n_bad
        s, d = res / src_rel, inp / dst_rel
        if not s.exists():
            exc("ERROR", "acquire", "expected asset missing in r40-results", src_rel)
            return False
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)
        o = orig.get(src_rel.replace("\\", "/"))
        h = sha256(d)
        status = "NO_ORIGINAL_HASH" if o is None else ("MATCH" if o == h else "MISMATCH")
        if status == "MISMATCH":
            n_bad += 1
            exc("ERROR", "acquire", "SHA-256 of reused asset differs from original run", src_rel)
        else:
            n_ok += 1
        integ.append(dict(asset=src_rel, sha256_copy=h, sha256_original_run=o or "", status=status))
        return True

    for key in KZ + VAL:
        for f in (kz_files() if key in KZ else val_files()):
            reuse(f"sites/{key}/rasters/{f}", f"rasters/{key}/{f}")
        reuse(f"sites/{key}/window.json", f"provenance/{key}_window.json")
        reuse(f"sites/{key}/sources_provenance.json", f"provenance/{key}_sources_provenance.json")
        reuse(f"boundaries/{key}.geojson", f"boundaries/{key}.geojson")
        reuse(f"boundaries/{key}_provenance.json", f"boundaries/{key}_boundary_provenance.json")
    for t in ("decisions_by_site.csv", "dem_qc.csv", "slope_class_shares.csv", "pairwise_dem_threshold_disagreement.csv"):
        reuse(f"tables/{t}", f"tables/{t}")
    reuse("manifest.json", "provenance/r40-results_manifest.json")
    reuse("run_status.csv", "provenance/r40-results_run_status.csv")
    C.write_csv(inp / "provenance" / "reuse_integrity_check.csv", integ)
    C.log("cartography", "reuse", "INTEGRITY", f"{n_ok} ok, {n_bad} mismatched")
    # ICESat-2 segments (reuse)
    for site, f in ATL08_FILE.items():
        s = ice / "icesat2" / f
        if s.exists():
            (inp / "atl08").mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, inp / "atl08" / f)
        else:
            exc("ERROR", "acquire", "ATL08 csv missing in r40-icesat2", f)
    for f in ("extract_summary.json",):
        if (ice / "icesat2" / f).exists():
            shutil.copy2(ice / "icesat2" / f, inp / "provenance" / f"atl08_{f}")
    shutil.copy2(CODE_ROOT / "config.json", inp / "config.json")
    if ne:
        fetch_natural_earth(inp / "natural_earth")
    if native:
        try:
            fetch_native_reference(inp, json.loads((CODE_ROOT / "config.json").read_text(encoding="utf-8")))
        except Exception as e:  # noqa: BLE001
            exc_tb("acquire", "native lidar-DTM fetch failed as a whole", e)


def fetch_natural_earth(d):
    import requests
    d.mkdir(parents=True, exist_ok=True)
    for name, urls in NE_URLS.items():
        done = False
        for u in urls:
            try:
                r = requests.get(u, timeout=120, headers={"User-Agent": C.UA})
                r.raise_for_status()
                (d / name).write_bytes(r.content)
                (d / (name + ".source.txt")).write_text(f"{u}\nretrieved {C.now()}\n", encoding="utf-8")
                done = True
                C.log("natural-earth", name, "OK", u)
                break
            except Exception as e:  # noqa: BLE001
                C.log("natural-earth", name, "TRY_FAILED", f"{u}: {e!r}")
        if not done:
            exc("ERROR", "acquire", f"Natural Earth base layer {name} could not be downloaded; base map panels will be marked as missing")


def fetch_native_reference(inp, cfg):
    """Native-resolution lidar DTM (swissALTI3D 2 m / USGS 3DEP 10 m) in a 3.2 km square around each validation centre: profiles + hillshade."""
    from pyproj import Transformer
    from . import sources as S
    client = None
    try:
        client = S.pc_client()
    except Exception as e:  # noqa: BLE001
        exc("WARN", "acquire", "Planetary Computer unavailable; USGS 3DEP windows cannot be fetched", repr(e))
    half = 1700.0
    for key in VAL:
        s = cfg["validation"][key]
        lon, lat = s["center"]
        epsg = C.utm_epsg(lon, lat)
        tr = Transformer.from_crs(4326, epsg, always_xy=True)
        cx, cy = tr.transform(lon, lat)
        rf = float(s["ref_res_m"])
        x0 = math.floor((cx - half) / rf) * rf
        y1 = math.ceil((cy + half) / rf) * rf
        n = int(round(2 * half / rf))
        g = S.Grid(epsg, x0, y1, n, n, rf)
        back = Transformer.from_crs(epsg, 4326, always_xy=True)
        xs, ys = zip(*[back.transform(x, y) for x in (x0, x0 + n * rf) for y in (y1, y1 - n * rf)])
        bb = (min(xs) - 0.002, min(ys) - 0.002, max(xs) + 0.002, max(ys) + 0.002)
        try:
            if s["reference"] == "swissalti3d":
                arr, info = S.fetch_swissalti3d(key, bb, g)
            else:
                arr, info = S.fetch_3dep(client, key, bb, g) if client is not None else (None, {"status": "NO_CLIENT"})
        except Exception as e:  # noqa: BLE001
            arr, info = None, {"status": "EXCEPTION", "error": repr(e)}
        C.write_json(inp / "provenance" / f"{key}_reference_native_provenance.json", info)
        if arr is None:
            exc("ERROR", "acquire", f"native lidar-DTM window not obtained for {key}; Figure D falls back to the 30 m block-mean reference only", info.get("status"))
            continue
        S.save_tif(inp / "rasters" / key / f"reference_native_{int(rf)}m_m.tif", arr, g, descr=f"{s['reference']} native {rf:g} m, 3.4 km window around site centre")
        C.log(key, "native-reference", "OK", f"{int(np.isfinite(arr).sum())} valid px")


# ======================================================================================================== BUILD: data model
class Ctx:
    def __init__(self, pkg, out):
        self.pkg, self.out = Path(pkg), Path(out)
        self.inp = self.pkg / "inputs"
        self.man = Manifest(self.out)
        self.cfg = json.loads((self.inp / "config.json").read_text(encoding="utf-8"))
        self.sites: dict[str, dict] = {}
        self.common: dict = {}
        self.captions: list[str] = []
        self.summary_rows: list[dict] = []
        self.verif_rows: list[dict] = []
        self.figures: list[str] = []
        self.ne: dict = {}
        self.inventory: list[dict] = []
        self.asset_commits: dict = {}
        self.atl_dates: dict = {}

    def raster_path(self, key, name):
        return self.inp / "rasters" / key / name


def prov_of(ctx, key, dem):
    p = ctx.inp / "provenance" / f"{key}_sources_provenance.json"
    try:
        j = json.loads(p.read_text(encoding="utf-8"))[dem]
        items = j.get("items", [])
        dates = sorted(set(str(x)[:10] for x in j.get("datetimes", [])))
        src = f"Microsoft Planetary Computer STAC collection '{dem}' ({len(items)} item(s): {', '.join(items[:3])}{'...' if len(items) > 3 else ''})"
        return src, ("; ".join(dates[:4]) if dates else "n/a (item datetime not recorded)")
    except Exception as e:  # noqa: BLE001
        return f"Planetary Computer collection {dem} (provenance json unreadable: {e!r})", "unknown"


def load_boundaries(ctx, key):
    from shapely.geometry import shape
    out = {"territory": None, "footprint": None, "chosen": None, "status": None}
    p = ctx.inp / "boundaries" / f"{key}.geojson"
    if p.exists():
        j = json.loads(p.read_text(encoding="utf-8"))
        for f in j["features"]:
            k = f["properties"].get("kind")
            g = shape(f["geometry"]) if f.get("geometry") else None
            if k == "territory_polygon_osm":
                out["territory"] = g
            elif k == "functional_footprint_derived":
                out["footprint"] = g
    pp = ctx.inp / "boundaries" / f"{key}_boundary_provenance.json"
    if pp.exists():
        pj = json.loads(pp.read_text(encoding="utf-8"))
        out["chosen"], out["status"], out["prov"] = pj.get("chosen"), pj.get("status"), pj
    return out


def load_site(ctx, key):
    group = "kazakhstan" if key in KZ else "validation"
    d = {"key": key, "group": group}
    win = json.loads((ctx.inp / "provenance" / f"{key}_window.json").read_text(encoding="utf-8"))
    d["window"] = win
    cop, meta = read_raster(ctx.raster_path(key, "cop-dem-glo-30_elevation_m.tif"))
    d.update(meta=meta, cop=cop, epsg=meta["epsg"], extent=extent_of(meta), res=meta["res"], x0=meta["x0"], y1=meta["y1"])
    d["nas"], _ = read_raster(ctx.raster_path(key, "nasadem_elevation_m.tif"))
    d["cop_slope"], _ = read_raster(ctx.raster_path(key, "cop-dem-glo-30_slope_deg_horn.tif"))
    d["nas_slope"], _ = read_raster(ctx.raster_path(key, "nasadem_slope_deg_horn.tif"))
    d["hs"] = L.hillshade(cop, meta["res"])
    if group == "kazakhstan":
        d["dec"] = {t: read_raster(ctx.raster_path(key, f"decision_combined_t{t}_risk2.tif"))[0] for t in THRESH}
        d["perr"] = {t: read_raster(ctx.raster_path(key, f"p_error_combined_t{t}.tif"))[0] for t in THRESH}
    else:
        d["ref30"], _ = read_raster(ctx.raster_path(key, "reference_dtm_30m_blockmean_m.tif"))
        d["ref_slope"], _ = read_raster(ctx.raster_path(key, "reference_slope_30m_deg.tif"))
    b = load_boundaries(ctx, key)
    d["bnd"] = b
    d["terr_utm"], d["foot_utm"] = project(b["territory"], d["epsg"]), project(b["footprint"], d["epsg"])
    masks = {"context": np.ones((meta["height"], meta["width"]), bool)}
    if group == "kazakhstan":
        tm, fm = rasterize_mask(d["terr_utm"], meta), rasterize_mask(d["foot_utm"], meta)
        if tm is not None:
            masks["territory_osm_polygon"] = tm
        if fm is not None:
            masks["functional_footprint_derived"] = fm
    d["masks"] = masks
    cfg = ctx.cfg["kazakhstan" if group == "kazakhstan" else "validation"][key]
    d["center"] = cfg["center"]
    return d


def contour_id(d, mask):
    k = d["key"]
    if mask == "context":
        w = d["window"]["grid"]
        return f"WINDOW:{k}:{w['crs']}:x0={w['x0']:.0f},y1={w['y1']:.0f},{w['width']}x{w['height']}@{w['res_m']:g}m"
    if mask == "territory_osm_polygon":
        ch = d["bnd"].get("chosen") or {}
        return f"OSM:{ch.get('osm', 'unknown')}"
    return f"DERIVED:{k}:footprint(buffer250m-erode200m of mapped aerialway/piste/tourism/leisure features)"


# ---------------------------------------------------------------------------------------------- derived rasters / vectors
def derived_rasters(ctx):
    """Separate nodata masks (1 = nodata), pixel-to-polygon masks, aligned common KZ grid mosaic."""
    out = ctx.out / "derived" / "rasters"
    for key, d in ctx.sites.items():
        meta = d["meta"]
        sd = out / key
        items = [("cop_elevation_nodata_mask.tif", (~np.isfinite(d["cop"])), "1 = Copernicus GLO-30 elevation NoData"),
                 ("nasadem_elevation_nodata_mask.tif", (~np.isfinite(d["nas"])), "1 = NASADEM elevation NoData"),
                 ("cop_slope_nodata_mask.tif", (~np.isfinite(d["cop_slope"])), "1 = slope NoData (3x3 neighbourhood incomplete)")]
        if d["group"] == "kazakhstan":
            for t in THRESH:
                items.append((f"decision_t{t}_nodata_mask.tif", d["dec"][t] == L.NODATA_DEC, f"1 = no decision at {t} deg (code 255)"))
            for mn, m in d["masks"].items():
                if mn != "context":
                    items.append((f"mask_{mn}.tif", ~m, "SPECIAL"))
        else:
            items.append(("reference_slope_nodata_mask.tif", ~np.isfinite(d["ref_slope"]), "1 = lidar-reference slope NoData"))
        for name, arr, descr in items:
            if descr == "SPECIAL":
                a = (~arr).astype("uint8")  # inside polygon = 1
                write_tif(sd / name, a, meta, nodata=None, dtype="uint8", descr="1 = pixel centre inside polygon (rasterio.features.rasterize, all_touched=False)")
                ctx.man.add(sd / name, "pixel-to-polygon mask", "rasterised from inputs/boundaries/*.geojson (OSM / derived footprint) on the site 30 m grid",
                            licence=LICENCE["osm"], notes="inside=1, outside=0; pixel-centre rule (all_touched=False) identical to the original run", res=f"{meta['res']:g}", crs=meta["crs"])
            else:
                write_tif(sd / name, arr.astype("uint8"), meta, nodata=None, dtype="uint8", descr=descr)
                ctx.man.add(sd / name, "separate nodata mask", f"derived from {name.split('_nodata')[0]} raster in inputs/rasters/{key}", licence=LICENCE["own"],
                            notes=descr, res=f"{meta['res']:g}", crs=meta["crs"])
    # ---- aligned common grid (KZ windows share EPSG:32643 and the 30 m lattice)
    kz = [ctx.sites[k] for k in KZ if k in ctx.sites]
    if not kz:
        return
    epsgs = {d["epsg"] for d in kz}
    if len(epsgs) != 1 or any(abs(d["res"] - 30) > 1e-9 for d in kz):
        exc("ERROR", "common grid", "Kazakhstan windows do not share one CRS/30 m cell size; common grid not built", epsgs)
        return
    lat = {d["x0"] % 30 for d in kz} | {d["y1"] % 30 for d in kz}
    if lat != {0.0}:
        exc("ERROR", "common grid", "window origins are not multiples of 30 m; common grid would need resampling and is not built", lat)
        return
    X0 = min(d["x0"] for d in kz)
    Y1 = max(d["y1"] for d in kz)
    X1 = max(d["x0"] + d["meta"]["width"] * 30 for d in kz)
    Y0 = min(d["y1"] - d["meta"]["height"] * 30 for d in kz)
    W, H = int(round((X1 - X0) / 30)), int(round((Y1 - Y0) / 30))
    from rasterio.transform import from_origin
    cm = dict(crs=kz[0]["meta"]["crs"], transform=from_origin(X0, Y1, 30, 30), res=30.0, width=W, height=H, bounds=(X0, Y0, X1, Y1), x0=X0, y1=Y1, epsg=kz[0]["epsg"])
    prods = {"cop_elevation_m": "cop", "nasadem_elevation_m": "nas", "cop_slope_deg": "cop_slope", "nasadem_slope_deg": "nas_slope"}
    count = np.zeros((H, W), "uint8")
    mos = {k: np.full((H, W), np.nan, "float32") for k in prods}
    max_overlap_diff = {k: 0.0 for k in prods}
    ov_n = {k: 0 for k in prods}
    ov_big = {k: 0 for k in prods}
    ov_sum = {k: 0.0 for k in prods}
    for d in kz:
        c0 = int(round((d["x0"] - X0) / 30))
        r0 = int(round((Y1 - d["y1"]) / 30))
        h, w = d["meta"]["height"], d["meta"]["width"]
        valid = np.isfinite(d["cop"])
        count[r0:r0 + h, c0:c0 + w] += valid.astype("uint8")
        for pk, attr in prods.items():
            src = d[attr].astype("float32")
            dst = mos[pk][r0:r0 + h, c0:c0 + w]
            both = np.isfinite(dst) & np.isfinite(src)
            if both.any():
                dd_ = np.abs(dst[both] - src[both])
                max_overlap_diff[pk] = max(max_overlap_diff[pk], float(dd_.max()))
                ov_n[pk] += int(both.sum())
                ov_sum[pk] += float(dd_.sum())
                ov_big[pk] += int((dd_ > (0.5 if "elev" in pk else 0.1)).sum())
            fill = ~np.isfinite(dst) & np.isfinite(src)
            dst[fill] = src[fill]
    cd = out / "common_grid_kz"
    for pk, arr in mos.items():
        write_tif(cd / f"{pk}.tif", arr, cm, nodata=np.nan, dtype="float32", descr=f"aligned KZ common grid, {pk}")
        ctx.man.add(cd / f"{pk}.tif", "aligned common analysis grid (mosaic)", "first-valid mosaic of the four Kazakhstan 30 m windows (identical lattice, no resampling)",
                    datum=DEM_META["cop-dem-glo-30"]["datum"] if pk.startswith("cop") else DEM_META["nasadem"]["datum"],
                    licence=DEM_META["cop-dem-glo-30" if pk.startswith("cop") else "nasadem"]["licence"], res="30", crs=cm["crs"],
                    dates=prov_of(ctx, "medeu", "cop-dem-glo-30" if pk.startswith("cop") else "nasadem")[1])
        nd = (~np.isfinite(arr)).astype("uint8")
        write_tif(cd / f"{pk}_nodata_mask.tif", nd, cm, dtype="uint8", descr="1 = nodata / outside all four windows")
        ctx.man.add(cd / f"{pk}_nodata_mask.tif", "separate nodata mask (common grid)", f"derived from {pk}.tif", licence=LICENCE["own"], res="30", crs=cm["crs"])
    write_tif(cd / "window_coverage_count.tif", count, cm, dtype="uint8", descr="number of study windows covering each cell with valid elevation")
    ctx.man.add(cd / "window_coverage_count.tif", "aligned common analysis grid (coverage)", "derived", licence=LICENCE["own"], res="30", crs=cm["crs"])
    C.write_csv(ctx.out / "tables" / "common_grid_coverage.csv",
                [dict(product=k, max_abs_difference_in_overlap=v, overlap_cells_compared=ov_n[k], overlap_cells_differing=ov_big[k],
                      differing_threshold=("0.5 m" if "elev" in k else "0.1 deg"), pct_overlap_cells_differing=(100.0 * ov_big[k] / ov_n[k] if ov_n[k] else float("nan")), mean_abs_difference_in_overlap=(ov_sum[k] / ov_n[k] if ov_n[k] else float("nan")), unit="m" if "elev" in k else "deg",
                      grid_crs=cm["crs"], x0=X0, y1=Y1, width=W, height=H, cell_m=30) for k, v in max_overlap_diff.items()])
    ctx.man.add(ctx.out / "tables" / "common_grid_coverage.csv", "table", "derived: overlap consistency of the aligned grid", licence=LICENCE["own"])
    ctx.common = dict(meta=cm, cop=mos["cop_elevation_m"], hs=L.hillshade(mos["cop_elevation_m"], 30), count=count, extent=extent_of(cm))
    if max(max_overlap_diff.values()) > 1e-3:
        exc("WARN", "common grid", "overlapping windows differ slightly in the overlap; first-valid pixel used. Likely cause (not tested): each window was warped separately from the geographic source grid, "
            "so sub-pixel coordinate approximation differs between windows; this is a property of the reused r40-results rasters, not of this package",
            {k: f"max {max_overlap_diff[k]:.3f}, mean {ov_sum[k] / max(ov_n[k], 1):.3f}; {100.0 * ov_big[k] / max(ov_n[k], 1):.2f}% of {ov_n[k]} overlap cells differ" for k in prods})


def vectors(ctx):
    import geopandas as gpd
    from shapely.geometry import Point, box, LineString
    from pyproj import Transformer
    rows, wins, cents = [], [], []
    for key, d in ctx.sites.items():
        b = d["bnd"]
        grp = "Kazakhstan study site" if d["group"] == "kazakhstan" else "validation site (lidar DTM)"
        variant = {"kok_zhailau": "KZ-V1 configured centre (provisional, author's working record)",
                   "kok_zhailau_osm": "KZ-V2 centre from OSM-named Kok-Zhailau objects"}.get(key, "single configuration")

        def area(g):
            return round(project(g, d["epsg"]).area / 1e6, 4) if g is not None else None
        if b["territory"] is not None:
            ch = b.get("chosen") or {}
            rows.append(dict(site=key, group=grp, study_variant=variant, feature="territory_polygon_osm", geometry_origin="OSM_named_polygon",
                             status="exploratory (OSM-mapped feature, not an official resort boundary)", source=f"OpenStreetMap {ch.get('osm', '')} ODbL; tags {ch.get('tags', '')}",
                             osm_name=ch.get("name", ""), area_km2_utm=area(b["territory"]), geometry=b["territory"]))
        if b["footprint"] is not None:
            rows.append(dict(site=key, group=grp, study_variant=variant, feature="functional_footprint_derived", geometry_origin="derived_from_OSM_mapped_features",
                             status="derived/exploratory - NOT an official boundary", source="OSM aerialway/piste/tourism/leisure features within footprint_radius_km of the configured centre, buffered 250 m then eroded 200 m (src/boundaries.py)",
                             osm_name="", area_km2_utm=area(b["footprint"]), geometry=b["footprint"]))
        if b["territory"] is None and b["footprint"] is None:
            exc("WARN", "vectors", f"no OSM polygon or footprint available for {key}")
        ext = d["extent"]
        wpoly = project(box(ext[0], ext[2], ext[1], ext[3]), d["epsg"], inverse=True)
        rows.append(dict(site=key, group=grp, study_variant=variant, feature="processing_window", geometry_origin="processing_window_rectangle",
                         status="analysis extent only; makes NO territory claim", source=f"{d['window']['grid']['crs']} grid x0={d['window']['grid']['x0']}, y1={d['window']['grid']['y1']}, {d['window']['grid']['width']}x{d['window']['grid']['height']} @30 m",
                         osm_name="", area_km2_utm=round((ext[1] - ext[0]) * (ext[3] - ext[2]) / 1e6, 4), geometry=wpoly))
        if b["territory"] is not None:
            pass
        cents.append(dict(site=key, study_variant=variant, geometry_origin=("author_working_record_provisional" if key == "kok_zhailau" else
                          "centroid of OSM objects named Kok-Zhailau (camp_site/attraction)" if key == "kok_zhailau_osm" else "configured_centre"),
                          note=ctx.cfg["kazakhstan" if d["group"] == "kazakhstan" else "validation"][key].get("role", ""), geometry=Point(*d["center"])))
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=4326)
    gc = gpd.GeoDataFrame(cents, geometry="geometry", crs=4326)
    vd = ctx.out / "derived" / "vector"
    vd.mkdir(parents=True, exist_ok=True)
    gdf.to_file(vd / "study_polygons.geojson", driver="GeoJSON")
    gc.to_file(vd / "study_centres.geojson", driver="GeoJSON")
    gpkg = vd / "r40_cartography_vectors.gpkg"
    if gpkg.exists():
        gpkg.unlink()
    gdf.to_file(gpkg, layer="study_polygons", driver="GPKG")
    gc.to_file(gpkg, layer="study_centres", driver="GPKG")
    if ctx.common:
        cm = ctx.common["meta"]
        b = cm["bounds"]
        ce = gpd.GeoDataFrame([dict(name="KZ_aligned_common_grid_extent", crs=cm["crs"], cell_m=30, width=cm["width"], height=cm["height"],
                                    geometry_origin="union of the four Kazakhstan window grids (identical 30 m lattice)",
                                    geometry=project(box(b[0], b[1], b[2], b[3]), cm["epsg"], inverse=True))], geometry="geometry", crs=4326)
        ce.to_file(vd / "common_grid_extent.geojson", driver="GeoJSON")
        ce.to_file(gpkg, layer="common_grid_extent", driver="GPKG")
    for p, role, src in ((vd / "study_polygons.geojson", "study polygons (both Kok-Zhailau candidates; field geometry_origin)", "inputs/boundaries/*.geojson (OSM Overpass, run r40-results) + window extents"),
                         (vd / "study_centres.geojson", "study centre points", "config.json centres; Kok-Zhailau origins documented in field geometry_origin"),
                         (vd / "common_grid_extent.geojson", "aligned common analysis grid extent", "derived from the four window grids"),
                         (gpkg, "GeoPackage with all study layers", "see individual layers")):
        ctx.man.add(p, role, src, licence=LICENCE["osm"] + "; processing windows/centres: " + LICENCE["own"], res="vector", crs="EPSG:4326")
    return gdf, gc


def profile_geometry(d, kind, half=1500.0, step=None):
    cx, cy = (d["cxy"])
    step = step or 30.0
    t = np.arange(-half, half + 1e-6, step)
    if kind == "WE":
        return cx + t, np.full_like(t, cy), t
    return np.full_like(t, cx), cy + t, t


def add_site_centres(ctx):
    from pyproj import Transformer
    for key, d in ctx.sites.items():
        tr = Transformer.from_crs(4326, d["epsg"], always_xy=True)
        d["cxy"] = tr.transform(*d["center"])


def atl08_layers(ctx):
    """ATL08 segments with quality flags (points) and per-track lines. Counts table for Figure E."""
    import geopandas as gpd
    from shapely.geometry import LineString
    from pyproj import Transformer
    from . import icesat2 as I
    frames, lines, cnt = [], [], []
    pts_by_site = {}
    for site, f in ATL08_FILE.items():
        p = ctx.inp / "atl08" / f
        if not p.exists():
            exc("ERROR", "ATL08", f"missing {f}; Figure E panel omitted")
            continue
        pts = I.load_points(p)
        epsg = 32643 if site == "kz_all" else ctx.sites[site]["epsg"]
        tr = Transformer.from_crs(4326, epsg, always_xy=True)
        x, y = tr.transform(pts["lon"], pts["lat"])
        x, y = np.asarray(x), np.asarray(y)
        common = I.quality_mask(pts, unc_max=1e9)
        lenient = I.quality_mask(pts, unc_max=15.0)
        strict = I.quality_mask(pts, unc_max=5.0)
        a, b, dd = I.track_pairs(pts, x, y)
        pair_mem = np.zeros(len(x), bool)
        pair_strict_n = int((strict[a] & strict[b]).sum())
        pair_len_n = int((lenient[a] & lenient[b]).sum())
        pair_mem[a] = True
        pair_mem[b] = True
        import re as _re
        dts = sorted({m.group(1) for g_ in set(pts["granule"]) for m in [_re.search(r"ATL08_(\d{8})", str(g_))] if m})
        ctx.atl_dates[site] = (f"{dts[0][:4]}-{dts[0][4:6]}-{dts[0][6:]}" if dts else "unknown", f"{dts[-1][:4]}-{dts[-1][4:6]}-{dts[-1][6:]}" if dts else "unknown", len(dts))
        pts_by_site[site] = dict(x=x, y=y, lon=pts["lon"], lat=pts["lat"], common=common, lenient=lenient, strict=strict, epsg=epsg)
        cnt.append(dict(site=site, n_segments_in_bbox=int(len(x)), n_pass_common_filters=int(common.sum()), n_lenient_unc_lt_15m=int(lenient.sum()),
                        n_strict_unc_lt_5m=int(strict.sum()), pct_strict=float(100 * strict.sum() / max(len(x), 1)), n_adjacent_pairs_80_120m=int(len(a)),
                        n_pairs_both_lenient=pair_len_n, n_pairs_both_strict=pair_strict_n,
                        filter_definition="common: h_te valid, n_te_photons>=30, cloud_flag_atm<=2 (src/icesat2.py quality_mask); lenient: h_te_uncertainty<15 m; strict: <5 m"))
        flag = np.where(strict, "strict", np.where(lenient, "lenient", np.where(common, "common_only", "rejected")))
        frames.append(gpd.GeoDataFrame(dict(site=site, granule=pts["granule"], beam=pts["beam"], h_te_unc_m=pts["h_te_unc"], n_te_photons=pts["n_te_ph"],
                                            cloud_flag=pts["cloud"], night_flag=pts["night"], quality_flag=flag, in_adjacent_pair=pair_mem,
                                            geometry=gpd.points_from_xy(pts["lon"], pts["lat"])), geometry="geometry", crs=4326))
        # track lines
        order = np.lexsort((pts["dt"], pts["beam"], pts["granule"]))
        gr, bm = pts["granule"][order], pts["beam"][order]
        brk = np.where((gr[1:] != gr[:-1]) | (bm[1:] != bm[:-1]) | (np.hypot(np.diff(x[order]), np.diff(y[order])) > 150))[0] + 1
        for seg in np.split(np.arange(len(order)), brk):
            if len(seg) < 2:
                continue
            ii = order[seg]
            q = strict[ii].sum(), lenient[ii].sum()
            lines.append(dict(site=site, granule=str(pts["granule"][ii[0]]), beam=str(pts["beam"][ii[0]]), n_segments=int(len(ii)), n_strict=int(q[0]), n_lenient=int(q[1]),
                              quality_flag="contains_strict" if q[0] else ("contains_lenient" if q[1] else "no_usable_segment"),
                              geometry=LineString(np.c_[pts["lon"][ii], pts["lat"][ii]])))
    if not frames:
        return None, None, pts_by_site
    import pandas as pd
    pg = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), geometry="geometry", crs=4326)
    lg = gpd.GeoDataFrame(lines, geometry="geometry", crs=4326)
    vd = ctx.out / "derived" / "vector"
    gpkg = vd / "atl08_segments_and_tracks.gpkg"
    if gpkg.exists():
        gpkg.unlink()
    pg.to_file(gpkg, layer="atl08_segments", driver="GPKG")
    lg.to_file(gpkg, layer="atl08_tracks", driver="GPKG")
    lg.to_file(vd / "atl08_tracks.geojson", driver="GeoJSON")
    pg[(pg.site == "kz_all") & pg.quality_flag.isin(["strict", "lenient"])].to_file(vd / "atl08_kz_usable_segments.geojson", driver="GeoJSON")
    src = "NASA ICESat-2 ATL08 v007 via NSIDC (segments copied from branch r40-icesat2; extraction by src/icesat2.py)"
    for p, role in ((gpkg, "ATL08 segment points (quality flags) and track lines"), (vd / "atl08_tracks.geojson", "ATL08 track lines with quality flag"),
                    (vd / "atl08_kz_usable_segments.geojson", "ATL08 usable (strict/lenient) segments, Kazakhstan")):
        ctx.man.add(p, role, src, datum="ellipsoidal heights (no geoid applied)", dates=("granule dates " + "; ".join(f"{k}: {v[0]}..{v[1]} ({v[2]} dates)" for k, v in ctx.atl_dates.items())),
                    licence=LICENCE["atl08"], notes="track samples only; NOT full-map validation", crs="EPSG:4326", res="vector (100 m along-track segments)")
    C.write_csv(ctx.out / "tables" / "atl08_filter_counts.csv", cnt)
    ctx.man.add(ctx.out / "tables" / "atl08_filter_counts.csv", "table", "derived from inputs/atl08/*.csv", licence=LICENCE["atl08"])
    kzc = [c for c in cnt if c["site"] == "kz_all"]
    if kzc:
        exc("INFO", "ATL08", "documented strict-filter counts vs recomputed",
            f"docs: 1,484 strict segments / 897-902 pairs (see repository notes); recomputed Kazakhstan strict={kzc[0]['n_strict_unc_lt_5m']}, pairs_both_strict={kzc[0]['n_pairs_both_strict']}; "
            f"sum over all five areas strict={sum(c['n_strict_unc_lt_5m'] for c in cnt)}")
    return pg, lg, pts_by_site


# ======================================================================================================== tables
def figure_b_tables(ctx):
    """Per-map summaries and verification against decisions_by_site.csv."""
    import pandas as pd
    ref = pd.read_csv(ctx.inp / "tables" / "decisions_by_site.csv")
    ref = ref[(ref.method == "combined") & (ref.group == "kazakhstan")]
    rows, ver = [], []
    for key in KZ:
        d = ctx.sites.get(key)
        if d is None:
            continue
        for t in THRESH:
            dec = d["dec"][t]
            for mn, m in d["masks"].items():
                sh = L.class_shares(dec, m)
                dis, ncomm = L.class_disagreement(np.where(m, d["cop_slope"], np.nan), np.where(m, d["nas_slope"], np.nan), t)
                n_mask = int(m.sum())
                row = dict(figure=("B" if t == 15 else "B-supp"), site=key, variant=LABEL[key], threshold_deg=t, mask=mn, contour_id=contour_id(d, mn),
                           crs=d["meta"]["crs"], cell_size_m=d["res"], pixel_area_m2=d["res"] ** 2, n_px_in_mask=n_mask, n_px_valid_decision=sh["n_px"],
                           n_px_nodata_in_mask=n_mask - sh["n_px"], area_km2_valid_plane_utm=sh["n_px"] * d["res"] ** 2 / 1e6,
                           BELOW_pct=sh["BELOW_pct"], ABOVE_pct=sh["ABOVE_pct"], ABSTAIN_pct=sh["ABSTAIN_pct"],
                           class_disagreement_cop_vs_nasadem_pct=dis, n_common_slope_px_for_disagreement=ncomm,
                           method_shown="combined (decision_combined_t*_risk2.tif; target training risk 0.02)")
                rows.append(row)
                r = ref[(ref["site"] == key) & (ref["mask"] == mn) & (np.isclose(ref.threshold_deg.astype(float), t))]
                if len(r) != 1:
                    ver.append(dict(site=key, mask=mn, threshold_deg=t, status="NO_TABLE_ROW" if len(r) == 0 else "AMBIGUOUS_TABLE_ROWS", n_rows=len(r)))
                    exc("WARN", "verification", "no unique decisions_by_site row for map", f"{key}/{mn}/{t}")
                    continue
                r = r.iloc[0]
                status, worst, ndiff = L.compare_shares(sh, r, tol_pp=0.05)
                ver.append(dict(site=key, mask=mn, threshold_deg=t, n_px_map=sh["n_px"], n_px_table=int(r.n_px), n_px_diff=ndiff,
                                BELOW_map=sh["BELOW_pct"], BELOW_table=float(r.BELOW_pct), ABOVE_map=sh["ABOVE_pct"], ABOVE_table=float(r.ABOVE_pct),
                                ABSTAIN_map=sh["ABSTAIN_pct"], ABSTAIN_table=float(r.ABSTAIN_pct), max_abs_diff_pp=worst, tolerance_pp=0.05, status=status))
                if status != "OK":
                    exc("ERROR", "verification", "Figure B summary differs from tables/decisions_by_site.csv (NOT adjusted)", f"{key}/{mn}/{t}: max diff {worst:.4f} pp, n_px diff {ndiff}")
    C.write_csv(ctx.out / "tables" / "map_summary_figB.csv", rows)
    C.write_csv(ctx.out / "tables" / "verification_figB_vs_decisions_by_site.csv", ver)
    for n in ("map_summary_figB.csv", "verification_figB_vs_decisions_by_site.csv"):
        ctx.man.add(ctx.out / "tables" / n, "table", "derived from decision rasters + inputs/tables/decisions_by_site.csv", licence=LICENCE["own"])
    ctx.summary_rows = rows
    ctx.verif_rows = ver
    for r_ in rows:
        ctx.inventory.append(dict(figure=r_["figure"], panel=SHORT[r_["site"]], site=r_["site"], quantity=f"decision shares ({r_['mask']})", crs=r_["crs"], cell_size_m=r_["cell_size_m"],
                                  n_valid_px=r_["n_px_valid_decision"], area_km2=r_["area_km2_valid_plane_utm"], contour_id=r_["contour_id"], threshold_deg=r_["threshold_deg"],
                                  BELOW_pct=r_["BELOW_pct"], ABOVE_pct=r_["ABOVE_pct"], ABSTAIN_pct=r_["ABSTAIN_pct"], class_disagreement_cop_vs_nasadem_pct=r_["class_disagreement_cop_vs_nasadem_pct"]))
    nbad = sum(1 for v in ver if v.get("status") not in ("OK",))
    C.log("verify", "figB", "DONE", f"{len(ver)} comparisons, {nbad} flagged")
    return rows, ver


def inter_dem_table(ctx):
    rows = []
    for key, d in ctx.sites.items():
        pairs = [("nasadem_minus_cop", d["nas_slope"], d["cop_slope"])]
        if d["group"] == "validation":
            pairs += [("cop_minus_lidar_ref", d["cop_slope"], d["ref_slope"]), ("nasadem_minus_lidar_ref", d["nas_slope"], d["ref_slope"])]
        for name, a, b in pairs:
            st = L.slope_diff_stats(a, b)
            row = dict(site=key, group=d["group"], pair=name, crs=d["meta"]["crs"], cell_size_m=d["res"], contour_id=contour_id(d, "context"),
                       area_km2_common_plane_utm=st.get("common_px", 0) * d["res"] ** 2 / 1e6, **st)
            for t in THRESH:
                dis, n = L.class_disagreement(a, b, t)
                row[f"class_disagreement_t{t}_pct"] = dis
            rows.append(row)
    C.write_csv(ctx.out / "tables" / "inter_dem_slope_difference_summary.csv", rows)
    ctx.man.add(ctx.out / "tables" / "inter_dem_slope_difference_summary.csv", "table", "derived from packaged slope rasters (common valid mask per pair)", licence=LICENCE["own"])


# ======================================================================================================== figures
def save_fig(ctx, fig, name, caption):
    d = ctx.out / "figures"
    d.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        p = d / f"{name}.{ext}"
        kw = dict(dpi=300) if ext == "png" else {}
        fig.savefig(p, **kw)
        ctx.man.add(p, f"figure {name}", "generated by src/cartography.py from packaged rasters/vectors (no generative imagery)", licence=LICENCE["own"] + "; base data licences as in caption",
                    notes="300 dpi" if ext == "png" else "vector + embedded raster", crs="n/a")
    ctx.captions.append(f"### {name}\n\n{caption}\n")
    ctx.figures.append(name)
    import matplotlib.pyplot as plt
    plt.close(fig)


def dem_source_line(ctx, key="medeu"):
    s, dates = prov_of(ctx, key, "cop-dem-glo-30")
    return f"Copernicus GLO-30 DSM (ESA/Copernicus; EGM2008; item dates {dates}) reprojected bilinearly to the 30 m UTM grid"


def site_base(ax, d, extent=None, alpha=1.0):
    ext = extent or d["extent"]
    ax.imshow(d["hs"], extent=d["extent"], cmap=L.gray_hillshade_cmap(), vmin=0.0, vmax=1.0, interpolation="nearest", zorder=1, alpha=alpha)
    L.style_map_axes(ax, ext)


def map_furniture(ax, d_or_epsg, extent, center_lonlat, small=False):
    epsg = d_or_epsg if isinstance(d_or_epsg, int) else d_or_epsg["epsg"]
    L.graticule_utm(ax, epsg, extent, n_max=3.2 if small else 4.5, fs=4.2 if small else 4.8)
    L.scale_bar(ax, extent, f"EPSG:{epsg}", fs=4.6 if small else 5.5)
    gamma = L.meridian_convergence_deg(center_lonlat[0], center_lonlat[1], L.utm_central_meridian(epsg))
    L.north_arrow(ax, extent, gamma, fs=3.8 if small else 4.3)


def draw_polys(ax, d, lw=1.0):
    L.plot_geom(ax, d["terr_utm"], color="#00205B", lw=lw + 0.3, ls="-", zorder=6)
    L.plot_geom(ax, d["foot_utm"], color="#E0218A", lw=lw + 0.2, ls=(0, (4, 2)), zorder=6)


def legend_decisions(fig, y=0.1):
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    h = [Patch(fc=L.to_rgba_list(L.COL_BELOW, .78), ec="k", lw=.4, label="BELOW threshold"), Patch(fc=L.to_rgba_list(L.COL_ABOVE, .78), ec="k", lw=.4, label="ABOVE threshold"),
         Patch(fc=L.to_rgba_list(L.COL_ABSTAIN, .78), ec="k", lw=.4, label="ABSTAIN"), Patch(fc=L.COL_NODATA, ec="k", lw=.4, label="No data / no decision (255)"),
         Line2D([], [], color="#00205B", lw=1.3, label="OSM named polygon (exploratory, not an official border)"),
         Line2D([], [], color="#E0218A", lw=1.2, ls=(0, (4, 2)), label="Derived functional footprint (not an official border)")]
    fig.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, y), ncol=3, fontsize=6, frameon=True)


def fig_B(ctx, t):
    plt = L_plt()
    keys = [k for k in KZ if k in ctx.sites]
    if not keys:
        return
    nm = {7.5: "FigB_supp_t7.5", 15: "FigB_decisions_t15", 25: "FigB_supp_t25"}[t]
    cap = (f"Figure B{'' if t == 15 else ' (supplement)'}. Threshold decisions at {t:g}° slope for the Kazakhstan study windows, exactly as classified in the packaged rasters "
           f"decision_combined_t{t:g}_risk2.tif (codes 0 BELOW, 1 ABOVE, 2 ABSTAIN, 255 no decision) produced by the combined (ridge-logistic) abstention rule with the training-risk target 0.02; "
           "the rule was trained on lidar-validated sites in Switzerland and the USA and is TRANSFERRED here, so error is not measured at these sites. "
           f"Background: hillshade of {dem_source_line(ctx)}. Panels (c) and (d) are two alternative Kok-Zhailau study windows (provisional configured centre vs centre taken from OSM-named objects), "
           "kept separate on purpose. Class colours are drawn at 78 % opacity over the hillshade; grey = no decision (nodata). Outlines: dark-blue = OSM-mapped named polygon (exploratory), "
           "pink dashed = functional footprint derived from mapped aerialways/pistes/tourism/leisure features (NOT an official boundary); no outline is shown where none exists. "
           "Maps are drawn in the metric UTM 43N CRS (EPSG:32643); scale bars are exact lengths in that projection; graticule from pyproj; the arrow points to true north (grid convergence printed). "
           "Pixel-to-polygon assignment: pixel centre inside polygon (rasterio rasterize, all_touched=False), masks packaged as mask_*.tif. "
           "Per-mask counts, areas, cell size, shares and contour identifiers: tables/map_summary_figB.csv; check against tables/decisions_by_site.csv: tables/verification_figB_vs_decisions_by_site.csv.")
    fh = 7.9
    bot = L.bottom_frac(cap, fh, 0.42)
    fig = plt.figure(figsize=(7.5, fh))
    gs = fig.add_gridspec(2, 2, left=0.05, right=0.985, top=0.925, bottom=bot + 0.02, hspace=0.26, wspace=0.12)
    for i, key in enumerate(keys):
        d = ctx.sites[key]
        ax = fig.add_subplot(gs[i // 2, i % 2])
        site_base(ax, d)
        ax.imshow(L.decision_rgba(d["dec"][t]), extent=d["extent"], interpolation="nearest", zorder=3)
        draw_polys(ax, d)
        map_furniture(ax, d, d["extent"], d["center"])
        sh = L.class_shares(d["dec"][t])
        ax.set_title(f"({chr(97 + i)}) {SHORT[key]} - {t:g}°\nn={sh['n_px']:,} px, 30 m; BELOW {sh['BELOW_pct']:.1f} | ABOVE {sh['ABOVE_pct']:.1f} | ABSTAIN {sh['ABSTAIN_pct']:.1f} %", fontsize=6.5)
    legend_decisions(fig, y=(L.cap_height_in(cap) + 0.05) / fh)
    L.place_caption(fig, cap)
    save_fig(ctx, fig, nm, cap)


def _adm(g):
    return g["ADMIN"] if "ADMIN" in g.columns else g["NAME"]


def L_plt():
    return L.apply_style()


def fig_A(ctx):
    import geopandas as gpd
    from pyproj import Transformer, CRS
    plt = L_plt()
    ne_missing = False
    ne110 = ne50 = None
    try:
        ne110 = gpd.read_file(ctx.inp / "natural_earth" / "ne_110m_admin_0_countries.zip")
        ne50 = gpd.read_file(ctx.inp / "natural_earth" / "ne_50m_admin_0_countries.zip")
    except Exception as e:  # noqa: BLE001
        ne_missing = True
        exc("ERROR", "Figure A", "Natural Earth base layers unreadable: country outlines are NOT drawn (not replaced by invented geometry)", repr(e))
    cap = ("Figure A. Location of the study and validation regions. (a) World overview; (b) Central Asia with the enlarged Kazakhstan window; (c) enlarged window 76.85-77.20°E, 43.05-43.25°N in "
           f"UTM zone 43N (EPSG:32643). Base layers (a, b): Natural Earth 1:110m / 1:50m admin-0 countries (public domain). Relief in (c): hillshade (azimuth 315°, altitude 45°) of {dem_source_line(ctx)}; "
           "grey = outside the packaged 30 m windows (no data), no relief is simulated there. Coloured rectangles are PROCESSING WINDOWS (analysis extents), not resort territories; solid lines are named OSM polygons "
           "where one exists (Medeu: a 0.043 km² sports-centre polygon; Shymbulak: a winter-sports polygon); dashed lines are footprints derived from mapped aerialways/pistes/tourism/leisure features within 2.5-3.5 km of the configured centre "
           "(buffer 250 m, erosion 200 m); they are exploratory and are NOT official borders. Kok-Zhailau is shown as two alternative windows: V1 (configured centre, provisional) and V2 (centre from OSM-named objects, ~5.9 km west). "
           "Panels a-b have no scale bar because distances are distorted at those scales; panel c has an exact metric scale bar, pyproj graticule and a true-north arrow rotated by the UTM grid convergence.")
    fh = 5.9
    bot = L.bottom_frac(cap, fh, 0.55)
    fig = plt.figure(figsize=(7.5, fh))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.5, 1], left=0.04, right=0.985, top=0.93, bottom=bot + 0.02, hspace=0.14, wspace=0.08)
    axC, axA, axB = fig.add_subplot(gs[:, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, 1])
    pts = {"KZ": ("Kazakhstan: Medeu, Shymbulak, Kok-Zhailau", 77.05, 43.13, "*", "#D55E00", (6, 4)), "CH": ("Switzerland: Davos, Zermatt", 8.8, 46.4, "^", "#0072B2", (-4, -11)),
           "US": ("USA: Alta-Snowbird, Park City", -111.6, 40.62, "^", "#0072B2", (-4, -11))}
    rob = CRS.from_proj4("+proj=robin +lon_0=0 +datum=WGS84")
    tr = Transformer.from_crs(4326, rob, always_xy=True)
    if ne110 is not None:
        g = ne110.to_crs(rob)
        g.plot(ax=axA, color="#EDEDED", edgecolor="0.55", linewidth=0.2)
        g[_adm(g).isin(["Kazakhstan"])].plot(ax=axA, color="#F4C7A6", edgecolor="0.4", linewidth=0.25)
        g[_adm(g).isin(["Switzerland", "United States of America"])].plot(ax=axA, color="#BBD7EA", edgecolor="0.4", linewidth=0.25)
    for lo in range(-180, 181, 60):
        axA.plot(*zip(*[tr.transform(lo, la) for la in np.linspace(-85, 85, 60)]), color="0.5", lw=0.3, ls=(0, (1, 2)))
    for la in range(-60, 61, 30):
        axA.plot(*zip(*[tr.transform(lo, la) for lo in np.linspace(-180, 180, 120)]), color="0.5", lw=0.3, ls=(0, (1, 2)))
    for k, (nm, lo, la, mk, col, off) in pts.items():
        x, y = tr.transform(lo, la)
        axA.plot(x, y, mk, ms=7 if mk == "*" else 5, color=col, mec="k", mew=0.4, zorder=5)
        axA.annotate(k, (x, y), xytext=off, textcoords="offset points", fontsize=5.5, fontweight="bold")
    axA.set_aspect("equal")
    axA.set_xticks([]); axA.set_yticks([]); axA.set_xlabel(""); axA.set_ylabel("")
    axA.set_title("(a) Study and validation regions", fontsize=7)
    axA.text(0.02, 0.02, "Robinson (lon_0=0°); no scale bar (distance distorted)", transform=axA.transAxes, fontsize=4.5)
    if ne_missing:
        axA.text(0.5, 0.5, "BASE MAP NOT AVAILABLE\n(Natural Earth download failed)", transform=axA.transAxes, ha="center", fontsize=6, color="darkred")
    laea = CRS.from_proj4("+proj=laea +lat_0=45 +lon_0=70 +datum=WGS84")
    tl = Transformer.from_crs(4326, laea, always_xy=True)
    if ne50 is not None:
        g5 = ne50.to_crs(laea)
        g5.plot(ax=axB, color="#EDEDED", edgecolor="0.55", linewidth=0.3)
        g5[_adm(g5).isin(["Kazakhstan"])].plot(ax=axB, color="#F4C7A6", edgecolor="0.3", linewidth=0.4)
    cc = [tl.transform(x, y) for x in np.linspace(46, 94, 25) for y in np.linspace(37, 56, 25)]
    axB.set_xlim(min(c[0] for c in cc), max(c[0] for c in cc))
    axB.set_ylim(min(c[1] for c in cc), max(c[1] for c in cc))
    ring = [tl.transform(x, y) for x, y in [(KZ_BBOX[0], KZ_BBOX[1]), (KZ_BBOX[2], KZ_BBOX[1]), (KZ_BBOX[2], KZ_BBOX[3]), (KZ_BBOX[0], KZ_BBOX[3]), (KZ_BBOX[0], KZ_BBOX[1])]]
    axB.plot(*zip(*ring), color="#D55E00", lw=1.2)
    rx, ry = tl.transform(77.025, 43.15)
    axB.plot(rx, ry, "o", ms=11, mfc="none", mec="#D55E00", mew=1.2, zorder=6)
    ax_, ay_ = tl.transform(76.9454, 43.2380)
    axB.plot(ax_, ay_, "o", ms=3, color="k"); axB.annotate("Almaty (city centre)", (ax_, ay_), xytext=(-62, 8), textcoords="offset points", fontsize=5.5)
    for lo in range(45, 100, 10):
        axB.plot(*zip(*[tl.transform(lo, la) for la in np.linspace(34, 58, 40)]), color="0.5", lw=0.3, ls=(0, (1, 2)))
    for la in range(36, 58, 5):
        axB.plot(*zip(*[tl.transform(lo, la) for lo in np.linspace(40, 100, 60)]), color="0.5", lw=0.3, ls=(0, (1, 2)))
    axB.set_aspect("equal"); axB.set_xticks([]); axB.set_yticks([]); axB.set_xlabel(""); axB.set_ylabel("")
    axB.set_title("(b) Central Asia; enlarged window in red", fontsize=7)
    axB.text(0.02, 0.02, "Lambert azimuthal equal-area (lat_0=45°N, lon_0=70°E); no scale bar", transform=axB.transAxes, fontsize=4.5)
    if ne_missing:
        axB.text(0.5, 0.5, "BASE MAP NOT AVAILABLE", transform=axB.transAxes, ha="center", fontsize=6, color="darkred")
    epsg = 32643
    t43 = Transformer.from_crs(4326, epsg, always_xy=True)
    corners = [t43.transform(x, y) for x, y in [(KZ_BBOX[0], KZ_BBOX[1]), (KZ_BBOX[2], KZ_BBOX[1]), (KZ_BBOX[2], KZ_BBOX[3]), (KZ_BBOX[0], KZ_BBOX[3])]]
    ext = (min(c[0] for c in corners), max(c[0] for c in corners), min(c[1] for c in corners), max(c[1] for c in corners))
    if ctx.common:
        axC.imshow(ctx.common["hs"], extent=ctx.common["extent"], cmap=L.gray_hillshade_cmap(), vmin=0, vmax=1, interpolation="nearest", zorder=1)
    L.style_map_axes(axC, ext)
    axC.set_facecolor(L.COL_NODATA)
    cols = {"medeu": "#009E73", "shymbulak": "#0072B2", "kok_zhailau": "#E69F00", "kok_zhailau_osm": "#CC79A7"}
    for key in KZ:
        d = ctx.sites.get(key)
        if d is None:
            continue
        e = d["extent"]
        axC.plot([e[0], e[1], e[1], e[0], e[0]], [e[2], e[2], e[3], e[3], e[2]], color=cols[key], lw=1.2, zorder=5)
        L.plot_geom(axC, d["terr_utm"], color=cols[key], lw=1.4, zorder=6)
        L.plot_geom(axC, d["foot_utm"], color=cols[key], lw=0.8, ls=(0, (4, 2)), zorder=6)
        cx, cy = d["cxy"]
        axC.plot(cx, cy, "o" if key != "kok_zhailau" else "D", ms=3.5, color=cols[key], mec="k", mew=0.5, zorder=7)
        axC.text(e[0] + 120, e[3] - 120, SHORT[key], fontsize=6, color="k", va="top", zorder=8, bbox=dict(fc="white", ec=cols[key], lw=0.6, alpha=0.85, pad=1.2))
        ctx.inventory.append(dict(figure="A", panel="c", site=key, quantity="processing window", crs=d["meta"]["crs"], cell_size_m=d["res"], n_valid_px=int(np.isfinite(d["cop"]).sum()),
                                  area_km2=(e[1] - e[0]) * (e[3] - e[2]) / 1e6, contour_id=contour_id(d, "context"), threshold_deg=""))
    bx = [t43.transform(x, y) for x, y in [(KZ_BBOX[0], KZ_BBOX[1]), (KZ_BBOX[2], KZ_BBOX[1]), (KZ_BBOX[2], KZ_BBOX[3]), (KZ_BBOX[0], KZ_BBOX[3]), (KZ_BBOX[0], KZ_BBOX[1])]]
    axC.plot(*zip(*bx), color="#D55E00", lw=1.0, zorder=7)
    ctx.inventory.append(dict(figure="A", panel="c", site="kz_inset_bbox", quantity="enlarged inset frame 76.85-77.20E, 43.05-43.25N", crs="EPSG:32643", cell_size_m=30,
                              n_valid_px=int(np.isfinite(ctx.common["cop"]).sum()) if ctx.common else 0, area_km2=Polygon_area(bx), contour_id="BBOX:76.85,43.05,77.20,43.25", threshold_deg=""))
    map_furniture(axC, epsg, ext, (77.02, 43.15))
    axC.set_title("(c) Kazakhstan study windows (76.85-77.20°E, 43.05-43.25°N)", fontsize=7)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color="#D55E00", marker="*", ls="", ms=7, mec="k", mew=.4, label="Kazakhstan study sites (a)"), Line2D([], [], color="#0072B2", marker="^", ls="", ms=5, mec="k", mew=.4, label="Lidar validation regions (a)"),
         Line2D([], [], color="0.2", lw=1.2, label="Processing window (extent only, rectangle)"), Line2D([], [], color="0.2", lw=1.4, label="OSM named polygon (exploratory)"),
         Line2D([], [], color="0.2", lw=.8, ls=(0, (4, 2)), label="Derived footprint (not an official border)"), Line2D([], [], color="0.4", marker="o", ls="", ms=3.5, label="Configured/OSM centre (diamond = provisional V1)")]
    fig.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, (L.cap_height_in(cap) + 0.05) / fh), ncol=3, fontsize=5.8)
    L.place_caption(fig, cap)
    save_fig(ctx, fig, "FigA_location_maps", cap)
    # A-supplement: validation sites
    cap2 = ("Figure A (supplement). Lidar-DTM validation sites used to train and validate the abstention rule: Davos-Parsenn and Zermatt-Gornergrat (Switzerland, swissALTI3D 2 m, LN02) and Alta-Snowbird and Park City (USA, USGS 3DEP 10 m, NAVD88). "
            "Background: hillshade of Copernicus GLO-30 DSM at 30 m (EGM2008). Green dot = configured site centre; dark-blue = OSM named polygon where found; pink dashed = derived footprint (exploratory, not an official border). "
            "Each panel is drawn in its own local UTM zone with an exact metric scale bar, pyproj graticule and a true-north arrow rotated by the grid convergence.")
    fh = 7.2
    bot = L.bottom_frac(cap2, fh, 0.1)
    fig = plt.figure(figsize=(7.5, fh))
    gs = fig.add_gridspec(2, 2, left=0.05, right=0.985, top=0.935, bottom=bot + 0.02, hspace=0.26, wspace=0.12)
    for i, key in enumerate(VAL):
        d = ctx.sites.get(key)
        if d is None:
            continue
        ax = fig.add_subplot(gs[i // 2, i % 2])
        site_base(ax, d)
        L.plot_geom(ax, d["foot_utm"], color="#E0218A", lw=1.0, ls=(0, (4, 2)), zorder=6)
        L.plot_geom(ax, d["terr_utm"], color="#00205B", lw=1.2, zorder=6)
        ax.plot(*d["cxy"], "o", ms=3.5, color="#009E73", mec="k", mew=0.5, zorder=7)
        map_furniture(ax, d, d["extent"], d["center"])
        ax.set_title(f"({chr(97 + i)}) {LABEL[key]}  (EPSG:{d['epsg']})", fontsize=6.8)
        e = d["extent"]
        ctx.inventory.append(dict(figure="A-supp", panel=chr(97 + i), site=key, quantity="processing window", crs=d["meta"]["crs"], cell_size_m=d["res"], n_valid_px=int(np.isfinite(d["cop"]).sum()),
                                  area_km2=(e[1] - e[0]) * (e[3] - e[2]) / 1e6, contour_id=contour_id(d, "context"), threshold_deg=""))
    L.place_caption(fig, cap2)
    save_fig(ctx, fig, "FigA_supp_validation_sites", cap2)


def Polygon_area(xy):
    a = 0.0
    for (x0, y0), (x1, y1) in zip(xy[:-1], xy[1:]):
        a += x0 * y1 - x1 * y0
    return abs(a) / 2 / 1e6


def fig_C(ctx):
    plt = L_plt()
    cmap = plt.get_cmap("RdBu_r").copy()
    cmap.set_bad(L.COL_NODATA)
    vm = 10.0

    def panel(ax, d, a, b, title, fig_id, pname, small=False):
        diff = np.where(np.isfinite(a) & np.isfinite(b), a - b, np.nan)
        ax.imshow(diff, extent=d["extent"], cmap=cmap, vmin=-vm, vmax=vm, interpolation="nearest")
        L.style_map_axes(ax, d["extent"])
        L.plot_geom(ax, d["foot_utm"], color="k", lw=0.5, ls=(0, (3, 2)))
        map_furniture(ax, d, d["extent"], d["center"], small=small)
        st = L.slope_diff_stats(a, b)
        ax.set_title(f"{title}\nn={st.get('common_px', 0):,} common px; mean {st.get('mean_diff_deg', float('nan')):+.2f}°, MAE {st.get('mae_deg', float('nan')):.2f}°", fontsize=5.8 if small else 6)
        ctx.inventory.append(dict(figure=fig_id, panel=pname, site=d["key"], quantity=title, crs=d["meta"]["crs"], cell_size_m=d["res"], n_valid_px=st.get("common_px", 0),
                                  area_km2=st.get("common_px", 0) * d["res"] ** 2 / 1e6, contour_id=contour_id(d, "context"), threshold_deg=""))
    keys = [k for k in KZ if k in ctx.sites]
    if keys:
        cap = ("Figure C1. Inter-DEM slope differences (NASADEM minus Copernicus GLO-30) on the common valid mask (pixels with a complete 3x3 neighbourhood in BOTH DEMs) for the four Kazakhstan windows. "
               "Both DEMs are DSMs resampled bilinearly to the same 30 m UTM 43N grid; slopes by the Horn (1981) 3x3 method. Differences show MODEL DISAGREEMENT between DEMs, not accuracy: no lidar reference exists for Kazakhstan. "
               "ALOS AW3D30 and FABDEM are not mapped because their rasters are not redistributed in this package (licence terms; see exceptions report). Statistics (common pixels, mean, SD, MAE, RMSE, 95th percentile, class disagreement at 7.5/15/25°): "
               "tables/inter_dem_slope_difference_summary.csv. Dashed black outline = derived functional footprint (exploratory). Metric scale bar, pyproj graticule and true-north arrow as in Figure B.")
        fh = 7.4
        bot = L.bottom_frac(cap, fh, 0.62)
        fig = plt.figure(figsize=(7.5, fh))
        gs = fig.add_gridspec(2, 2, left=0.05, right=0.985, top=0.925, bottom=bot + 0.02, hspace=0.26, wspace=0.12)
        for i, k in enumerate(keys):
            d = ctx.sites[k]
            panel(fig.add_subplot(gs[i // 2, i % 2]), d, d["nas_slope"], d["cop_slope"], f"({chr(97 + i)}) {SHORT[k]}: NASADEM minus Copernicus slope", "C1", chr(97 + i))
        sm = plt.cm.ScalarMappable(norm=plt.Normalize(-vm, vm), cmap=cmap)
        cb = fig.colorbar(sm, cax=fig.add_axes([0.25, (L.cap_height_in(cap) + 0.3) / fh, 0.5, 0.011]), orientation="horizontal")
        cb.set_label("slope difference, degrees (Horn, 30 m); grey = no data in either DEM", fontsize=6)
        L.place_caption(fig, cap)
        save_fig(ctx, fig, "FigC1_kazakhstan_inter_dem_slope_difference", cap)
    vk = [k for k in VAL if k in ctx.sites]
    if vk:
        cap = ("Figure C2. Slope differences at the lidar validation sites on the common valid mask of each pair: global DEM minus lidar-DTM reference (support-matched: the swissALTI3D 2 m / USGS 3DEP 10 m DTM is block-averaged to the 30 m grid "
               "before the slope is computed) and NASADEM minus Copernicus. Rows: Davos-Parsenn, Zermatt-Gornergrat (Switzerland), Alta-Snowbird, Park City (USA). Zermatt includes glaciers whose surface changed between the lidar epoch and the DSMs. "
               "Global DEMs are DSMs (canopy/buildings included), the reference is a bare-earth DTM; no co-registration was applied. Statistics: tables/inter_dem_slope_difference_summary.csv. "
               "Each panel is drawn in its own local UTM zone with an exact metric scale bar, graticule and true-north arrow; dashed outline = derived footprint (exploratory).")
        fh = 9.4
        bot = L.bottom_frac(cap, fh, 0.5)
        fig = plt.figure(figsize=(7.5, fh))
        gs = fig.add_gridspec(len(vk), 3, left=0.045, right=0.985, top=0.945, bottom=bot + 0.02, hspace=0.42, wspace=0.14)
        for r, k in enumerate(vk):
            d = ctx.sites[k]
            panel(fig.add_subplot(gs[r, 0]), d, d["cop_slope"], d["ref_slope"], f"{SHORT[k]}: Copernicus - lidar", "C2", f"{r + 1}a", small=True)
            panel(fig.add_subplot(gs[r, 1]), d, d["nas_slope"], d["ref_slope"], f"{SHORT[k]}: NASADEM - lidar", "C2", f"{r + 1}b", small=True)
            panel(fig.add_subplot(gs[r, 2]), d, d["nas_slope"], d["cop_slope"], f"{SHORT[k]}: NASADEM - Copernicus", "C2", f"{r + 1}c", small=True)
        sm = plt.cm.ScalarMappable(norm=plt.Normalize(-vm, vm), cmap=cmap)
        cb = fig.colorbar(sm, cax=fig.add_axes([0.25, (L.cap_height_in(cap) + 0.22) / fh, 0.5, 0.008]), orientation="horizontal")
        cb.set_label("slope difference, degrees (Horn, 30 m); grey = no data", fontsize=6)
        L.place_caption(fig, cap)
        save_fig(ctx, fig, "FigC2_validation_dem_vs_lidar_slope_difference", cap)


def ref_epoch(ctx, key):
    import re as _re
    try:
        j = json.loads((ctx.inp / "provenance" / f"{key}_reference_native_provenance.json").read_text(encoding="utf-8"))
        ids = j.get("items", [])
        yrs = sorted({m.group(1) for i_ in ids for m in [_re.search(r"_(20\d\d|19\d\d)_", str(i_))] if m})
        if yrs:
            return f"swissALTI3D release year(s) {', '.join(yrs)} ({len(ids)} tiles)"
        return f"{len(ids)} USGS 3DEP item(s); per-item dates in inputs/provenance/{key}_reference_native_provenance.json (3DEP seamless is a mosaic of lidar projects of different years)"
    except Exception:  # noqa: BLE001
        return "acquisition epoch: see provenance json (not recorded)"


def fig_D(ctx):
    plt = L_plt()
    rows_s, rows_sum = [], []
    for key in VAL:
        d = ctx.sites.get(key)
        if d is None:
            continue
        rf = float(ctx.cfg["validation"][key]["ref_res_m"])
        p = ctx.raster_path(key, f"reference_native_{int(rf)}m_m.tif")
        native = None
        if p.exists():
            native, nm = read_raster(p)
        else:
            exc("ERROR", "Figure D", f"native lidar window missing for {key}; profile is drawn from the 30 m block-mean reference only", p.name)
        ref_name = "swissALTI3D (LN02, 2 m; swisstopo OGD)" if ctx.cfg["validation"][key]["reference"] == "swissalti3d" else "USGS 3DEP 1/3 arc-second (NAVD88, ~10 m)"
        cap = (f"Figure D ({SHORT[key]}). Measured terrain profiles along two grid-aligned 3 km transects through the site centre (rule-based, not selected for agreement; defined in derived/vector/profile_lines.geojson). "
               f"Reference: {ref_name}, a bare-earth lidar DTM, shown at native resolution (black) and block-averaged to the 30 m cell (grey) - the SUPPORT-MATCHED reference used in the validation; candidate DEMs: "
               f"Copernicus GLO-30 DSM (EGM2008) and NASADEM DSM (EGM96), 30 m, bilinearly sampled along the line. Vertical datums are not harmonised, so absolute heights differ by a geoid offset of a few metres; "
               "the lower panels remove the median offset along each transect. DSMs include canopy/buildings while the reference is bare earth. No co-registration was applied. "
               f"Reference epoch: {ref_epoch(ctx, key)}; Copernicus GLO-30 item date {prov_of(ctx, key, 'cop-dem-glo-30')[1]}; NASADEM item date {prov_of(ctx, key, 'nasadem')[1]}. "
               "Profile values: tables/profile_samples.csv; statistics: tables/profile_summary.csv. Map: exact metric scale bar, pyproj graticule, true-north arrow (grid convergence printed).")
        fh = 7.9
        bot = L.bottom_frac(cap, fh, 0.15)
        fig = plt.figure(figsize=(7.5, fh))
        gs = fig.add_gridspec(4, 2, width_ratios=[1, 1.5], height_ratios=[3, 1.2, 3, 1.2], left=0.045, right=0.985, top=0.945, bottom=bot + 0.03, hspace=0.62, wspace=0.30)
        axm = fig.add_subplot(gs[:, 0])
        axm.set_anchor("N")
        if native is not None:
            hsn = L.hillshade(native, nm["res"])
            axm.imshow(hsn, extent=extent_of(nm), cmap=L.gray_hillshade_cmap(), vmin=0, vmax=1, interpolation="nearest")
            mext = extent_of(nm)
        else:
            axm.imshow(d["hs"], extent=d["extent"], cmap=L.gray_hillshade_cmap(), vmin=0, vmax=1)
            mext = (d["cxy"][0] - 1700, d["cxy"][0] + 1700, d["cxy"][1] - 1700, d["cxy"][1] + 1700)
        L.style_map_axes(axm, mext)
        cols = {"WE": "#D55E00", "SN": "#0072B2"}
        for kind in ("WE", "SN"):
            xs, ys, t = profile_geometry(d, kind, 1500.0, 30.0)
            axm.plot([xs[0], xs[-1]], [ys[0], ys[-1]], color=cols[kind], lw=1.4, zorder=6)
            axm.text(xs[-1], ys[-1], kind, color=cols[kind], fontsize=7, fontweight="bold", zorder=7, ha="left" if kind == "WE" else "center", va="center" if kind == "WE" else "bottom",
                     bbox=dict(fc="white", ec="none", alpha=0.75, pad=0.6))
        axm.plot(*d["cxy"], "o", ms=3, color="k", zorder=7)
        map_furniture(axm, d, mext, d["center"], small=True)
        axm.set_title(f"{LABEL[key]}\nhillshade of {'native lidar DTM' if native is not None else '30 m block-mean DTM'}", fontsize=6.5)
        for r, kind in enumerate(("WE", "SN")):
            step = rf if native is not None else 30.0
            xs, ys, t = profile_geometry(d, kind, 1500.0, step)
            z_nat = L.sample_bilinear(native, nm["x0"], nm["y1"], nm["res"], xs, ys) if native is not None else np.full_like(t, np.nan)
            sm = lambda a: L.sample_bilinear(a, d["x0"], d["y1"], 30.0, xs, ys)  # noqa: E731
            z30, zc, zn = sm(d["ref30"]), sm(d["cop"]), sm(d["nas"])
            ax = fig.add_subplot(gs[2 * r, 1])
            if native is not None:
                ax.plot(t, z_nat, color="k", lw=0.7, label=f"lidar DTM, native {rf:g} m")
            ax.plot(t, z30, color="0.45", lw=1.1, label="lidar DTM, 30 m block-mean (support-matched)")
            ax.plot(t, zc, color="#D55E00", lw=0.9, label="Copernicus GLO-30 DSM, 30 m")
            ax.plot(t, zn, color="#0072B2", lw=0.9, label="NASADEM DSM, 30 m")
            ax.set_ylabel("elevation, m (datums differ)")
            ax.set_title(f"({'ab'[r]}) transect {kind} through the site centre (grid {'W-E' if kind == 'WE' else 'S-N'}, 3 km)", fontsize=6.5)
            ax.grid(color="0.85", lw=0.4)
            if r == 0:
                ax.legend(loc="best", fontsize=5.0)
            axd = fig.add_subplot(gs[2 * r + 1, 1], sharex=ax)
            ok = np.isfinite(z30)
            for nm_, zz, col in (("Copernicus", zc, "#D55E00"), ("NASADEM", zn, "#0072B2")):
                dd = zz - z30
                dd = dd - np.nanmedian(dd)
                axd.plot(t, dd, color=col, lw=0.8)
                v = np.isfinite(dd)
                rows_sum.append(dict(site=key, transect=kind, dem=nm_, n_points=int(v.sum()), rmse_debiased_m=float(np.sqrt(np.nanmean(dd[v] ** 2))) if v.any() else float("nan"),
                                     median_offset_m=float(np.nanmedian(zz - z30)) if v.any() else float("nan"), relief_ref30_m=float(np.nanmax(z30) - np.nanmin(z30)) if ok.any() else float("nan"),
                                     reference_native=("yes" if native is not None else "NOT AVAILABLE"), step_m=step, contour_id=f"PROFILE:{key}:{kind}:3000m"))
            axd.axhline(0, color="k", lw=0.4)
            axd.set_ylabel("DEM - ref30,\nmedian removed, m", fontsize=6)
            axd.set_xlabel("distance along transect from site centre, m")
            axd.grid(color="0.85", lw=0.4)
            for j in range(len(t)):
                rows_s.append(dict(site=key, transect=kind, distance_m=float(t[j]), x_utm=float(xs[j]), y_utm=float(ys[j]), lidar_native_m=float(z_nat[j]), lidar_30m_blockmean_m=float(z30[j]),
                                   cop_glo30_m=float(zc[j]), nasadem_m=float(zn[j])))
            ctx.inventory.append(dict(figure="D", panel=f"{key}:{kind}", site=key, quantity="elevation profile 3 km", crs=d["meta"]["crs"], cell_size_m=rf if native is not None else 30.0,
                                      n_valid_px=int(np.isfinite(z_nat).sum() if native is not None else ok.sum()), area_km2="", contour_id=f"PROFILE:{key}:{kind}:3000m", threshold_deg=""))
        axs = fig.add_subplot(gs[2:, 0])
        axs.axis("off")
        sub = [r_ for r_ in rows_sum if r_["site"] == key]
        txt = ["Profile statistics (DEM minus 30 m lidar reference,", "median offset removed along each 3 km transect)", "", f"{'transect':<9}{'DEM':<12}{'n':>5}{'RMSE, m':>9}{'offset, m':>10}"]
        for r_ in sub:
            txt.append(f"{r_['transect']:<9}{r_['dem']:<12}{r_['n_points']:>5}{r_['rmse_debiased_m']:>9.2f}{r_['median_offset_m']:>10.2f}")
        txt += ["", "offset = median of (DEM - ref30): geoid/datum shift", "plus any real vertical bias (not separable here)."]
        axs.text(0.0, 0.95, "\n".join(txt), family="DejaVu Sans Mono", fontsize=4.9, va="top", ha="left", transform=axs.transAxes)
        L.place_caption(fig, cap)
        save_fig(ctx, fig, f"FigD_profile_{key}", cap)
    if rows_s:
        C.write_csv(ctx.out / "tables" / "profile_samples.csv", rows_s)
        C.write_csv(ctx.out / "tables" / "profile_summary.csv", rows_sum)
        for n in ("profile_samples.csv", "profile_summary.csv"):
            ctx.man.add(ctx.out / "tables" / n, "table", "sampled from packaged rasters (native lidar window + 30 m rasters)", licence=LICENCE["swiss"] + "; " + LICENCE["3dep"])


def profile_vectors(ctx):
    import geopandas as gpd
    from shapely.geometry import LineString
    rows = []
    for key in VAL:
        d = ctx.sites.get(key)
        if d is None:
            continue
        rf = float(ctx.cfg["validation"][key]["ref_res_m"])
        for kind in ("WE", "SN"):
            xs, ys, t = profile_geometry(d, kind, 1500.0, 30.0)
            g = project(LineString(list(zip(xs, ys))), d["epsg"], inverse=True)
            rows.append(dict(site=key, transect=kind, length_m=3000.0, azimuth_grid_deg=90 if kind == "WE" else 0, crs_native=f"EPSG:{d['epsg']}",
                             rule="straight grid-aligned line of 3 km centred on the configured site centre (not chosen from the data)",
                             reference_product=("swissALTI3D 2 m" if ctx.cfg["validation"][key]["reference"] == "swissalti3d" else "USGS 3DEP 1/3 arc-second ~10 m"),
                             reference_native_tif=f"inputs/rasters/{key}/reference_native_{int(rf)}m_m.tif", geometry=g))
    if not rows:
        return
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=4326)
    vd = ctx.out / "derived" / "vector"
    gdf.to_file(vd / "profile_lines.geojson", driver="GeoJSON")
    gp = vd / "r40_cartography_vectors.gpkg"
    gdf.to_file(gp, layer="profile_lines", driver="GPKG")
    ctx.man.add(vd / "profile_lines.geojson", "reference lines for selected elevation profiles", "rule-based transects (see field 'rule')", licence=LICENCE["own"], crs="EPSG:4326", res="vector")


def fig_E(ctx, pts_by_site):
    plt = L_plt()
    sites = [s_ for s_ in ("kz_all",) + tuple(VAL) if s_ in pts_by_site]
    if not sites:
        return
    cap = ("Figure E. Real ICESat-2 ATL08 v007 terrain segments (100 m along-track; points are the true segment locations) used as a PARTIAL independent reference. Filters fixed before inspecting DEM errors: common = terrain height valid, "
           ">= 30 terrain photons, ATM cloud flag <= 2; lenient = height uncertainty < 15 m; strict = < 5 m. Points exist only along the satellite ground tracks (point samples), so they must NOT be read as full-map validation of any slope map. "
           "The strict subset is 1-4 % of all segments in every area (table in panel f). Counts in panel titles refer to the displayed extent; full-bbox counts are in tables/atl08_filter_counts.csv. Heights are ellipsoidal and were not geoid-corrected here. "
           "Background: hillshade of Copernicus GLO-30 (30 m; grey = outside the packaged windows). Panel (a) covers 76.85-77.20°E, 43.05-43.25°N (UTM 43N); other panels are the lidar validation windows (own local UTM). "
           "Exact metric scale bars, graticule, true-north arrows. Vector layers with quality flags: derived/vector/atl08_segments_and_tracks.gpkg. "
           + "Granule acquisition dates (from granule names): " + "; ".join(f"{('Kazakhstan' if k == 'kz_all' else SHORT[k])} {v[0]} to {v[1]} ({v[2]} dates)" for k, v in ctx.atl_dates.items()) + ".")
    fh = 7.3
    bot = L.bottom_frac(cap, fh, 0.45)
    fig = plt.figure(figsize=(7.5, fh))
    gs = fig.add_gridspec(2, 3, left=0.04, right=0.985, top=0.925, bottom=bot + 0.02, hspace=0.30, wspace=0.12)
    for i, s_ in enumerate(sites):
        ax = fig.add_subplot(gs[i // 3, i % 3])
        P = pts_by_site[s_]
        if s_ == "kz_all":
            from pyproj import Transformer
            t43 = Transformer.from_crs(4326, 32643, always_xy=True)
            cs = [t43.transform(x, y) for x, y in [(KZ_BBOX[0], KZ_BBOX[1]), (KZ_BBOX[2], KZ_BBOX[1]), (KZ_BBOX[2], KZ_BBOX[3]), (KZ_BBOX[0], KZ_BBOX[3])]]
            ext = (min(c[0] for c in cs), max(c[0] for c in cs), min(c[1] for c in cs), max(c[1] for c in cs))
            if ctx.common:
                ax.imshow(ctx.common["hs"], extent=ctx.common["extent"], cmap=L.gray_hillshade_cmap(), vmin=0, vmax=1, zorder=1)
            ax.set_facecolor(L.COL_NODATA)
            epsg, center, ttl, cid = 32643, (77.02, 43.15), "Kazakhstan (ICESat-2 window)", "BBOX:76.85,43.05,77.20,43.25"
            cell = 30.0
        else:
            d = ctx.sites[s_]
            ax.imshow(d["hs"], extent=d["extent"], cmap=L.gray_hillshade_cmap(), vmin=0, vmax=1, zorder=1)
            ext, epsg, center, ttl, cid, cell = d["extent"], d["epsg"], d["center"], SHORT[s_], contour_id(d, "context"), d["res"]
        L.style_map_axes(ax, ext)
        x, y, rej = P["x"], P["y"], ~P["common"]
        inx = (x >= ext[0]) & (x <= ext[1]) & (y >= ext[2]) & (y <= ext[3])
        c_only = P["common"] & ~P["lenient"] & inx
        len_only = P["lenient"] & ~P["strict"] & inx
        stt = P["strict"] & inx
        ax.scatter(x[rej & inx], y[rej & inx], s=0.25, c="#6E6E6E", lw=0, alpha=0.5, zorder=3, rasterized=True)
        ax.scatter(x[c_only], y[c_only], s=0.5, c="#D9D9D9", lw=0, zorder=3, rasterized=True)
        ax.scatter(x[len_only], y[len_only], s=2.2, c="#E69F00", lw=0, zorder=4, rasterized=True)
        ax.scatter(x[stt], y[stt], s=3.4, c="#B2182B", lw=0.15, edgecolors="k", zorder=5, rasterized=True)
        map_furniture(ax, epsg, ext, center, small=True)
        ax.set_title(f"({chr(97 + i)}) {ttl}\nin view {int(inx.sum()):,}; lenient {int((P['lenient'] & inx).sum()):,}; strict {int(stt.sum()):,}", fontsize=5.8)
        ctx.inventory.append(dict(figure="E", panel=chr(97 + i), site=s_, quantity="ATL08 segments in view", crs=f"EPSG:{epsg}", cell_size_m=cell, n_valid_px=int(inx.sum()),
                                  area_km2=(ext[1] - ext[0]) * (ext[3] - ext[2]) / 1e6, contour_id=cid, threshold_deg=""))
    # panel f: counts table
    axt = fig.add_subplot(gs[1, 2])
    axt.axis("off")
    try:
        import csv as _csv
        rows = list(_csv.DictReader(open(ctx.out / "tables" / "atl08_filter_counts.csv", encoding="utf-8")))
        lines = ["(f) Segments per area (full bbox)", "", f"{'area':<18}{'all':>7}{'common':>8}{'lenient':>8}{'strict':>7}{'pairs*':>7}"]
        for r_ in rows:
            lines.append(f"{('Kazakhstan' if r_['site'] == 'kz_all' else SHORT[r_['site']])[:17]:<18}{int(r_['n_segments_in_bbox']):>7,}{int(r_['n_pass_common_filters']):>8,}{int(r_['n_lenient_unc_lt_15m']):>8,}{int(r_['n_strict_unc_lt_5m']):>7,}{int(r_['n_pairs_both_strict']):>7,}")
        lines += ["", "*adjacent segment pairs (80-120 m),", " both strict (unc. < 5 m)"]
        axt.text(0.0, 0.98, "\n".join(lines), family="DejaVu Sans Mono", fontsize=4.9, va="top", ha="left", transform=axt.transAxes)
    except Exception as e:  # noqa: BLE001
        exc("WARN", "Figure E", "counts panel not drawn", repr(e))
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker="o", ls="", ms=3, color="#B2182B", mec="k", mew=.2, label="strict: unc. < 5 m"), Line2D([], [], marker="o", ls="", ms=3, color="#E69F00", label="lenient only: 5 - 15 m"),
         Line2D([], [], marker="o", ls="", ms=3, color="#D9D9D9", mec="0.5", mew=.2, label="passes common filters, unc. >= 15 m"), Line2D([], [], marker="o", ls="", ms=3, color="#6E6E6E", label="rejected by common filters")]
    fig.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, (L.cap_height_in(cap) + 0.05) / fh), ncol=4, fontsize=5.8)
    L.place_caption(fig, cap)
    save_fig(ctx, fig, "FigE_atl08_track_samples", cap)


# ======================================================================================================== docs + driver
def write_docs(ctx, commit, run_id):
    (ctx.out / "figures").mkdir(parents=True, exist_ok=True)
    (ctx.out / "figures" / "CAPTIONS.md").write_text("# Figure captions (full text)\n\n" + "\n".join(ctx.captions), encoding="utf-8")
    ctx.man.add(ctx.out / "figures" / "CAPTIONS.md", "captions", "generated with the figures", licence=LICENCE["own"])
    sc = ctx.out / "scripts"
    (sc / "src").mkdir(parents=True, exist_ok=True)
    for f in ("__init__.py", "common.py", "cartography.py", "carto_lib.py", "carto.mplstyle", "icesat2.py", "sources.py"):
        shutil.copy2(CODE_ROOT / "src" / f, sc / "src" / f)
    for f in ("requirements.txt", "requirements-carto.txt"):
        if (CODE_ROOT / f).exists():
            shutil.copy2(CODE_ROOT / f, sc / f)
    (sc / "rebuild_all.sh").write_text(
        "#!/usr/bin/env bash\n# Rebuild every derived raster, vector, figure and table from the packaged inputs (offline, no network).\nset -euo pipefail\n"
        "cd \"$(dirname \"$0\")\"\npython -m pip install -r requirements.txt -r requirements-carto.txt\n"
        "python -m src.cartography build --package .. --out ../rebuild_check\n"
        "echo 'Compare: diff -r ../tables ../rebuild_check/tables'\n", encoding="utf-8")
    for p in sc.rglob("*"):
        if p.is_file():
            ctx.man.add(p, "script", "repository code at generation commit", licence="repository code licence (see repository)")
    ver = ctx.verif_rows
    nbad = sum(1 for v in ver if v.get("status") != "OK")
    readme = f"""# R40_CARTOGRAPHY_SOURCE_PACKAGE

Reproducible scientific GIS figures and source layers for R40 "Support-aware terrain threshold decisions" (Kazakhstan: Medeu, Shymbulak, two Kok-Zhailau variants;
validation: Davos-Parsenn, Zermatt-Gornergrat (CH), Alta-Snowbird, Park City (US)).

Generated: {C.now()}  |  code commit: {commit}  |  workflow run: {run_id}

Reused result branches (commit hashes): {json.dumps({k: v for k, v in ctx.asset_commits.items() if k.startswith('r40')})}

## Contents
* `inputs/` - assets REUSED from earlier verified runs (branch r40-results, r40-icesat2; SHA-256 re-checked against the original run in `inputs/provenance/reuse_integrity_check.csv`), plus freshly fetched native lidar-DTM windows and Natural Earth layers.
* `derived/rasters/` - separate nodata masks (1 = nodata), pixel-to-polygon masks (`mask_*.tif`), the aligned Kazakhstan common 30 m grid (`common_grid_kz/`).
* `derived/vector/` - `r40_cartography_vectors.gpkg` and GeoJSON: study polygons (both Kok-Zhailau candidates; field `geometry_origin`), study centres, common-grid extent, profile lines, ATL08 segments/tracks with quality flags.
* `figures/` - FigA (location, + supplement), FigB (15 deg decisions; supplements 7.5 and 25 deg), FigC1/C2 (inter-DEM and DEM-vs-lidar slope differences), FigD (profiles, four sites), FigE (ATL08 samples); PNG 300 dpi, PDF, SVG; full captions in `figures/CAPTIONS.md`.
* `tables/` - per-map summaries, verification against `decisions_by_site.csv`, inter-DEM statistics, ATL08 filter counts, profile samples and statistics.
* `manifest.csv` - every file with source, resolution, CRS, vertical datum, extent, acquisition dates, licence, SHA-256, generation commit and run id.
* `exceptions_report.md/.csv` - everything missing, flagged or deliberately excluded.
* `scripts/` - code + `rebuild_all.sh` (offline rebuild of all derived products from `inputs/`).

## Rules followed
* No generative AI for geography or raster values; no simulated landscape; missing data are marked, not replaced.
* Boundaries are OSM-mapped features or footprints derived from mapped objects and are labelled exploratory; NO official resort border is claimed.
* Maps use true coordinate transforms: local metric UTM CRS; scale bars are exact lengths in that CRS; graticules from pyproj; north arrows account for grid convergence.
* Figure B shows exactly the classes in the packaged `decision_combined_t*_risk2.tif`; its summaries were checked against `tables/decisions_by_site.csv` (tolerance 0.05 percentage points, identical pixel counts): {len(ver) - nbad} of {len(ver)} comparisons OK, {nbad} flagged. Flagged items are listed in the exceptions report and are NOT adjusted.
* Not included: KazEOSat pixels (no licence), tokens, private imagery, ALOS AW3D30 and FABDEM rasters (licence/redistribution), the user's private location details.

## Exact sources
* Copernicus GLO-30 and NASADEM: Microsoft Planetary Computer STAC API https://planetarycomputer.microsoft.com/api/stac/v1 (collections `cop-dem-glo-30`, `nasadem`; item ids and dates in `inputs/provenance/*_sources_provenance.json`, retrieved by run r40-results 38058021115).
* Lidar DTMs: swisstopo STAC https://data.geo.admin.ch/api/stac/v0.9 (collection ch.swisstopo.swissalti3d, 2 m); USGS 3DEP via Planetary Computer (`3dep-seamless`, 10 m).
* OSM polygons: Overpass API (endpoint, query and time in `inputs/boundaries/*_boundary_provenance.json`).
* ICESat-2 ATL08 v007: NASA NSIDC DAAC (segments extracted in branch r40-icesat2).
* Natural Earth admin-0 countries: naciscdn.org/naturalearth (1:110m, 1:50m).

## Licences / attribution
Copernicus GLO-30 (ESA/Copernicus, "Contains modified Copernicus data"); NASADEM (NASA/USGS, public domain); OpenStreetMap contributors (ODbL); Natural Earth (public domain);
swissALTI3D (swisstopo OGD); USGS 3DEP (public domain); NASA ICESat-2 ATL08 v007 (NSIDC DAAC).

## Rebuild
`bash scripts/rebuild_all.sh` (Python >= 3.10; numpy, scipy, rasterio, pyproj, shapely, geopandas, pyogrio, matplotlib). Network is not needed.
"""
    (ctx.out / "README.md").write_text(readme, encoding="utf-8")
    ctx.man.add(ctx.out / "README.md", "readme", "generated", licence=LICENCE["own"])


def write_exceptions(ctx):
    C.write_csv(ctx.out / "exceptions_report.csv", EXC, ["severity", "area", "message", "detail"])
    lines = ["# Exceptions report", "", f"Generated {C.now()}. Severity: ERROR = product missing/failed or discrepancy; WARN = limitation; INFO = note.", ""]
    for sev in ("ERROR", "WARN", "INFO"):
        rows = [e for e in EXC if e["severity"] == sev]
        if rows:
            lines += [f"## {sev} ({len(rows)})", ""]
            lines += [f"- **{e['area']}** - {e['message']}" + (f" `{e['detail']}`" if e["detail"] else "") for e in rows] + [""]
    (ctx.out / "exceptions_report.md").write_text("\n".join(lines), encoding="utf-8")
    ctx.man.add(ctx.out / "exceptions_report.md", "exceptions report", "generated", licence=LICENCE["own"])
    ctx.man.add(ctx.out / "exceptions_report.csv", "exceptions report", "generated", licence=LICENCE["own"])


STANDING_EXCEPTIONS = [
    ("INFO", "scope", "ALOS AW3D30 not mapped/packaged", "not redistributed here (JAXA terms require citation/registration; raster use previously limited to statistics in the main run). Figures C use Copernicus GLO-30 and NASADEM only."),
    ("INFO", "scope", "FABDEM not mapped/packaged", "CC BY-NC-SA 4.0 (non-commercial, share-alike) - raster not redistributed; the main run used it for statistics only. In the OSM-centred Kok-Zhailau window ~45 % of FABDEM pixels are nodata."),
    ("WARN", "data", "No lidar/DTM reference exists for Kazakhstan", "Kazakhstan maps show transferred decisions; error is NOT measured there. ICESat-2 gives point samples along tracks only."),
    ("WARN", "data", "Distance-only decision rasters were never published", "Figure B shows the combined rule (the rasters in r40-results). The distance-only shares exist only as table rows in decisions_by_site.csv."),
    ("WARN", "boundaries", "Official resort boundaries are not available", "Medeu territory = a 0.043 km2 OSM sports-centre polygon (not the resort); Kok-Zhailau has no named OSM polygon; footprints are derived. None is an official border."),
    ("WARN", "data", "KazEOSat imagery not used", "No public catalogue and no licence; proprietary pixels are not distributed."),
    ("WARN", "vertical datum", "Heights are not datum-harmonised in profile figures", "EGM2008/EGM96/LN02/NAVD88 differ by metres; profile difference panels remove the median offset."),
]


def build(pkg, out, only_figs=None):
    pkg, out = Path(pkg), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    commit = os.environ.get("GITHUB_SHA", git_head(CODE_ROOT.parent.parent))
    try:
        ac = json.loads((pkg / "inputs" / "provenance" / "asset_commits.json").read_text(encoding="utf-8"))
        commit = ac.get("code_commit") or commit
    except Exception:  # noqa: BLE001
        ac = {}
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    ctx = Ctx(pkg, out)
    ctx.asset_commits = ac
    for s in STANDING_EXCEPTIONS:
        exc(*s)
    for key in KZ + VAL:
        try:
            ctx.sites[key] = load_site(ctx, key)
        except Exception as e:  # noqa: BLE001
            exc_tb("load", f"site {key} could not be loaded; all products for it are skipped", e)
    add_site_centres(ctx)
    # register inputs
    for p in sorted((pkg / "inputs").rglob("*")) if out == pkg else []:
        if p.is_file():
            rel = p.relative_to(pkg / "inputs")
            top = rel.parts[0]
            if top == "rasters":
                site, name = rel.parts[1], rel.parts[-1]
                dem = "cop-dem-glo-30" if name.startswith("cop") else "nasadem" if name.startswith("nasadem") else None
                if dem:
                    src, dates = prov_of(ctx, site, dem)
                    ctx.man.add(p, f"input raster ({DEM_META[dem]['label']})", src, datum=DEM_META[dem]["datum"], dates=dates, licence=DEM_META[dem]["licence"],
                                notes="reused from branch r40-results (hash re-verified)")
                elif name.startswith("reference_native"):
                    sw = "swiss" if "davos" in site or "zermatt" in site else "3dep"
                    ctx.man.add(p, "input raster (lidar DTM, native resolution window)", ("swisstopo STAC ch.swisstopo.swissalti3d" if sw == "swiss" else "Planetary Computer 3dep-seamless 10 m"),
                                datum="LN02" if sw == "swiss" else "NAVD88", dates="see inputs/provenance/*_reference_native_provenance.json", licence=LICENCE[sw])
                elif name.startswith("reference"):
                    ctx.man.add(p, "input raster (lidar-DTM reference, 30 m block-mean / slope)", "swissALTI3D or USGS 3DEP via run r40-results", datum="LN02 / NAVD88", licence=LICENCE["swiss"] + "; " + LICENCE["3dep"],
                                dates="see sources_provenance json", notes="reused from branch r40-results")
                elif name.startswith("decision") or name.startswith("p_error"):
                    ctx.man.add(p, "input raster (decision / predicted error)", "run r40-results (combined abstention rule, transferred); codes 0/1/2, 255 nodata", licence=LICENCE["own"] + "; " + DEM_META["cop-dem-glo-30"]["licence"],
                                notes="reused from branch r40-results")
            elif top == "boundaries":
                ctx.man.add(p, "input vector/provenance (OSM Overpass, run r40-results)", "OpenStreetMap via Overpass API (see provenance json for query and time)", licence=LICENCE["osm"])
            elif top == "atl08":
                ctx.man.add(p, "input table (ATL08 segments)", "NASA ICESat-2 ATL08 v007 via NSIDC (branch r40-icesat2)", datum="ellipsoidal", licence=LICENCE["atl08"])
            elif top == "natural_earth":
                ctx.man.add(p, "input base layer", "Natural Earth (naciscdn.org / naturalearth S3), see .source.txt", licence=LICENCE["ne"])
            else:
                ctx.man.add(p, "input table/provenance", "repository run artefacts", licence=LICENCE["own"])
    steps = [("derived rasters", lambda: derived_rasters(ctx)), ("vectors", lambda: vectors(ctx)), ("profile vectors", lambda: profile_vectors(ctx)),
             ("tables B", lambda: figure_b_tables(ctx)), ("tables inter-DEM", lambda: inter_dem_table(ctx))]
    pts = {}
    def _atl():
        nonlocal pts
        _, _, pts = atl08_layers(ctx)
    steps.append(("ATL08 layers", _atl))
    steps += [("Figure A", lambda: fig_A(ctx)), ("Figure B t15", lambda: fig_B(ctx, 15)), ("Figure B t7.5", lambda: fig_B(ctx, 7.5)), ("Figure B t25", lambda: fig_B(ctx, 25)),
              ("Figure C", lambda: fig_C(ctx)), ("Figure D", lambda: fig_D(ctx)), ("Figure E", lambda: fig_E(ctx, pts))]
    for name, fn in steps:
        if only_figs and not any(f in name for f in only_figs):
            continue
        try:
            fn()
            C.log("cartography", name, "OK", "")
        except Exception as e:  # noqa: BLE001
            exc_tb(name, "step failed", e)
    if ctx.inventory:
        C.write_csv(ctx.out / "tables" / "map_inventory.csv", ctx.inventory)
        ctx.man.add(ctx.out / "tables" / "map_inventory.csv", "table", "one row per map panel/quantity: area, valid px, cell size, CRS, threshold, shares, contour id", licence=LICENCE["own"])
    write_docs(ctx, commit, run_id)
    write_exceptions(ctx)
    ctx.man.finalize(commit, run_id)
    C.log("cartography", "build", "DONE", f"{len(ctx.figures)} figures; {len(EXC)} exceptions")
    return ctx


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("acquire")
    a.add_argument("--assets", required=True)
    a.add_argument("--package", required=True)
    a.add_argument("--no-native", action="store_true")
    a.add_argument("--no-ne", action="store_true")
    b = sub.add_parser("build")
    b.add_argument("--package", required=True)
    b.add_argument("--out")
    b.add_argument("--only", nargs="*")
    c = sub.add_parser("all")
    c.add_argument("--assets", required=True)
    c.add_argument("--package", required=True)
    args = ap.parse_args()
    if args.cmd in ("acquire", "all"):
        acquire(args.assets, args.package, native=not getattr(args, "no_native", False), ne=not getattr(args, "no_ne", False))
    if args.cmd in ("build", "all"):
        build(args.package, getattr(args, "out", None) or args.package, only_figs=getattr(args, "only", None))
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
