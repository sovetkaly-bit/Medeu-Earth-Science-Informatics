"""R40 journal edition of the cartography: figures A-E redrawn for A4 print from the SAME packaged data.

Nothing scientific is recomputed or changed: rasters, polygons, classes, CRS and numbers come from the package produced by
`python -m src.cartography` (workflow run 38078170104). The prepare step re-derives the tables with the unchanged code and
compares them with the package tables (tables/consistency_vs_source_package.csv). Differences from the first edition are
presentation only: figure width 180 mm, every text >= 7 pt (audited), captions moved out of the image, one light legend per figure,
hypsometric tint + multi-directional hillshade on bicubic-resampled DEM (display only, declared in every caption).
The one new data input is the Copernicus GLO-30 DSM for the full overview window (same product, same pipeline), fetched so the
overview map has no grey gaps. No generative imagery is used anywhere.

Usage (from research/R40_KZ):
  python -m src.cartography_journal all --package PKG --out OUT --parts PARTS
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, os, shutil, textwrap, zipfile, zlib
from pathlib import Path
import numpy as np
from . import common as C
from . import carto_lib as L
from . import carto_journal_lib as J
from . import cartography as K

CODE_ROOT = K.CODE_ROOT
OVERVIEW_KEY = "overview_kz"
WCOL = {"medeu": "#009E73", "shymbulak": "#0072B2", "kok_zhailau": "#E69F00", "kok_zhailau_osm": "#CC79A7"}
LIM_SOFT, LIM_HARD = 19_000_000, 20_000_000   # bytes per zip part (user limit: 20 MB)
DEC_FIG_ALPHA = 0.72


def apply_style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.style.use(str(Path(__file__).with_name("carto_journal.mplstyle")))
    return plt


def utm_label(epsg):
    zone = int(str(epsg)[-2:])
    return f"UTM {zone}{'N' if str(epsg).startswith('326') else 'S'}"


# ======================================================================================================== state
class JX:
    def __init__(self, ctx, out):
        self.ctx, self.out = ctx, Path(out)
        self.man = K.Manifest(self.out)
        self.captions: list[tuple] = []     # name, short, technical, width_in, height_in
        self.fonts: list[dict] = []
        self.furn: list[dict] = []
        self.shares: list[dict] = []
        self.prof: list[dict] = []
        self.rel: dict = {}
        self.ov: dict | None = None
        self.checks: list[dict] = []

    def fur(self, figure, panel, site, rec):
        for r in rec:
            self.furn.append(dict(figure=figure, panel=panel, site=site, **r))


def site_relief(jx, key, kind="gray", k=3):
    ck = (key, kind, k)
    if ck not in jx.rel:
        d = jx.ctx.sites[key]
        jx.rel[ck] = J.relief(d["cop"], d["res"], k=k, kind=kind)
    return jx.rel[ck][0]


def load_overview(jx):
    """Full-window Copernicus GLO-30 DSM (fetched by acquire_overview); falls back to the four-window mosaic and flags it."""
    p = jx.ctx.raster_path(OVERVIEW_KEY, "cop-dem-glo-30_elevation_m.tif")
    if p.exists():
        z, meta = K.read_raster(p)
        jx.ov = dict(z=z, meta=meta, extent=K.extent_of(meta), res=meta["res"], source="full-window Copernicus GLO-30 (inputs/rasters/overview_kz)", complete=True)
    elif jx.ctx.common:
        c = jx.ctx.common
        jx.ov = dict(z=c["cop"], meta=c["meta"], extent=c["extent"], res=30.0, source="mosaic of the four study windows (overview raster missing)", complete=False)
        K.exc("ERROR", "overview", "full-window DEM missing: overview and Figure E(a) use the four-window mosaic; grey = no data", str(p))
    else:
        K.exc("ERROR", "overview", "no DEM available for the overview map")


def ov_relief(jx, kind="color", k=2):
    ck = ("overview", kind, k)
    if ck not in jx.rel:
        jx.rel[ck] = J.relief(jx.ov["z"], jx.ov["res"], k=k, kind=kind)
    return jx.rel[ck][0]


def kz_extent():
    from pyproj import Transformer
    t43 = Transformer.from_crs(4326, 32643, always_xy=True)
    w, s, e, n = K.KZ_BBOX
    cs = [t43.transform(x, y) for x, y in [(w, s), (e, s), (e, n), (w, n)]]
    return (min(c[0] for c in cs), max(c[0] for c in cs), min(c[1] for c in cs), max(c[1] for c in cs))


# ======================================================================================================== acquire (one small, new, real raster)
def acquire_overview(pkg):
    """Copernicus GLO-30 for the full 76.85-77.20E x 43.05-43.25N window on the same 30 m lattice as the study windows."""
    pkg = Path(pkg)
    d = pkg / "inputs" / "rasters" / OVERVIEW_KEY
    tif = d / "cop-dem-glo-30_elevation_m.tif"
    if tif.exists():
        return True
    try:
        from . import sources as S
        client = S.pc_client()
        pad = 0.012
        bbox = (K.KZ_BBOX[0] - pad, K.KZ_BBOX[1] - pad, K.KZ_BBOX[2] + pad, K.KZ_BBOX[3] + pad)
        grid = S.make_grid(bbox, 32643, res=30.0, multiple=6, max_side_km=60.0)
        out, prov = S.fetch_pc_dems(client, OVERVIEW_KEY, bbox, grid, which=["cop-dem-glo-30"])
        d.mkdir(parents=True, exist_ok=True)
        (pkg / "inputs" / "provenance").mkdir(parents=True, exist_ok=True)
        C.write_json(pkg / "inputs" / "provenance" / f"{OVERVIEW_KEY}_sources_provenance.json", prov)
        C.write_json(pkg / "inputs" / "provenance" / f"{OVERVIEW_KEY}_window.json", dict(grid=grid.to_dict(), bbox_wgs84_padded=bbox))
        if "cop-dem-glo-30" not in out:
            K.exc("ERROR", "overview", "Copernicus GLO-30 fetch for the overview window failed", json.dumps(prov)[:600])
            return False
        S.save_tif(tif, out["cop-dem-glo-30"], grid, descr="Copernicus GLO-30 DSM (EGM2008), bilinear to the 30 m UTM 43N lattice (overview window)")
        return True
    except Exception as e:  # noqa: BLE001
        K.exc_tb("overview", "overview DEM could not be acquired", e)
        return False


# ======================================================================================================== prepare (same code as the first edition) + consistency check
def compare_csv(a, b, tol=1e-9):
    import pandas as pd
    if not (Path(a).exists() and Path(b).exists()):
        return "MISSING_FILE", "", ""
    x, y = pd.read_csv(a), pd.read_csv(b)
    if list(x.columns) != list(y.columns) or len(x) != len(y):
        return "DIFFERENT_SHAPE", f"{len(x)}x{len(x.columns)} vs {len(y)}x{len(y.columns)}", ""
    nd, mx = 0, 0.0
    for c in x.columns:
        if pd.api.types.is_numeric_dtype(x[c]) and pd.api.types.is_numeric_dtype(y[c]):
            dd = np.abs(x[c].to_numpy(float) - y[c].to_numpy(float))
            dd = np.where(np.isnan(dd), 0.0, dd)
            nd += int((dd > tol).sum())
            mx = max(mx, float(dd.max()) if len(dd) else 0.0)
        else:
            nd += int((x[c].astype(str) != y[c].astype(str)).sum())
    return ("IDENTICAL" if nd == 0 else "DIFFERENT_VALUES"), nd, mx


def prepare(pkg, scratch):
    ctx = K.Ctx(pkg, scratch)
    for s in K.STANDING_EXCEPTIONS:
        K.exc(*s)
    for key in K.KZ + K.VAL:
        try:
            ctx.sites[key] = K.load_site(ctx, key)
        except Exception as e:  # noqa: BLE001
            K.exc_tb("load", f"site {key} could not be loaded; all its products are skipped", e)
    K.add_site_centres(ctx)
    K.derived_rasters(ctx)
    K.vectors(ctx)
    K.figure_b_tables(ctx)
    K.inter_dem_table(ctx)
    _, _, pts = K.atl08_layers(ctx)
    return ctx, pts


def consistency(jx, pkg, scratch):
    rows = []
    for n in ("map_summary_figB.csv", "verification_figB_vs_decisions_by_site.csv", "atl08_filter_counts.csv", "inter_dem_slope_difference_summary.csv", "common_grid_coverage.csv"):
        st, nd, mx = compare_csv(Path(scratch) / "tables" / n, Path(pkg) / "tables" / n)
        rows.append(dict(table=n, status=st, n_differing_cells=nd, max_abs_numeric_difference=mx,
                         meaning="recomputed by this edition (unchanged code) vs the table shipped in the first package"))
        if st != "IDENTICAL":
            K.exc("ERROR", "consistency", f"{n} differs from the first package ({st})", f"{nd} cells, max diff {mx}")
    C.write_csv(jx.out / "tables" / "consistency_vs_source_package.csv", rows)
    jx.man.add(jx.out / "tables" / "consistency_vs_source_package.csv", "table", "this edition vs first package", licence=K.LICENCE["own"])
    jx.checks += rows


# ======================================================================================================== output helpers
def save(jx, fig, name, short, tech):
    plt = apply_style()
    d = jx.out / "figures"
    d.mkdir(parents=True, exist_ok=True)
    jx.fonts += J.font_audit(fig, name)
    for ext in ("png", "pdf", "svg"):
        p = d / f"{name}.{ext}"
        fig.savefig(p, dpi=300) if ext == "png" else fig.savefig(p)
        jx.man.add(p, f"journal figure {name}", "generated by src/cartography_journal.py from packaged rasters/vectors (no generative imagery)",
                   licence=K.LICENCE["own"] + "; base data licences as in caption", crs="n/a",
                   notes={"png": "300 dpi, 180 mm wide", "pdf": "vector text (TrueType), embedded relief raster", "svg": "editable: text kept as text, embedded relief raster"}[ext])
    w, h = fig.get_size_inches()
    jx.captions.append((name, short, tech, w, h))
    plt.close(fig)


def grid_layout(plt, aspects, cols=2, lm=0.5, rm=0.15, gap=0.55, title_h=0.55, bottom_h=0.3, extra_bottom=0.55, top=0.12, w=J.FIG_W):
    pw = (w - lm - rm - gap * (cols - 1)) / cols
    rows = [aspects[i:i + cols] for i in range(0, len(aspects), cols)]
    row_h = [pw * max(r) for r in rows]
    H = top + sum(title_h + rh + bottom_h for rh in row_h) + extra_bottom
    pg = J.Page(plt, w, H)
    rects, y = [], top
    for ri, r in enumerate(rows):
        for ci, ar in enumerate(r):
            rects.append((lm + ci * (pw + gap), y + title_h, pw, pw * ar))
        y += title_h + row_h[ri] + bottom_h
    return pg, rects, pw


def decision_handles():
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    a = DEC_FIG_ALPHA
    return [Patch(fc=L.to_rgba_list(L.COL_BELOW, a), ec="k", lw=0.5, label="BELOW"), Patch(fc=L.to_rgba_list(L.COL_ABOVE, a), ec="k", lw=0.5, label="ABOVE"),
            Patch(fc=L.to_rgba_list(L.COL_ABSTAIN, a), ec="k", lw=0.5, label="ABSTAIN"), Patch(fc=L.COL_NODATA, ec="k", lw=0.5, label="No decision"),
            Line2D([], [], color="k", lw=1.4, label="OSM polygon"), Line2D([], [], color="k", lw=1.2, ls=(0, (4, 2)), label="Derived footprint")]


def relief_note(jx, k=3, kind="gray"):
    return (f"Relief: Copernicus GLO-30 DSM, bicubic-resampled {k}x for display only (cell {30 / k:g} m), multi-directional hillshade "
            f"(azimuths {', '.join(f'{a:g}' for a in J.HS_AZ)} deg, altitude {J.HS_ALT:g} deg, weights {', '.join(f'{w:g}' for w in J.HS_W)})"
            f"{', hypsometric tint (colour bar)' if kind == 'color' else ', grey scale'}; analysis values stay on the packaged 30 m grid.")


# ======================================================================================================== Figure A
def fig_A(jx):
    import geopandas as gpd
    from pyproj import Transformer, CRS
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    plt = apply_style()
    ctx = jx.ctx
    ne110 = ne50 = None
    try:
        ne110 = gpd.read_file(ctx.inp / "natural_earth" / "ne_110m_admin_0_countries.zip")
        ne50 = gpd.read_file(ctx.inp / "natural_earth" / "ne_50m_admin_0_countries.zip")
    except Exception as e:  # noqa: BLE001
        K.exc("ERROR", "Figure A", "Natural Earth base layers unreadable: country outlines are NOT drawn (not replaced by invented geometry)", repr(e))
    ext = kz_extent()
    W = J.FIG_W
    wc = W - 0.5 - 0.95
    hc = wc * J.aspect(ext)
    top_h = 1.6
    H = 0.1 + 0.3 + top_h + 0.5 + hc + 0.32 + 0.6
    pg = J.Page(plt, W, H)
    wa = (W - 0.12 - 0.12 - 0.3) / 2
    axA = pg.axes(0.12, 0.4, wa, top_h)
    axB = pg.axes(0.12 + wa + 0.3, 0.4, wa, top_h)
    adm = lambda g: g["ADMIN"] if "ADMIN" in g.columns else g["NAME"]  # noqa: E731
    rob = CRS.from_proj4("+proj=robin +lon_0=0 +datum=WGS84")
    tr = Transformer.from_crs(4326, rob, always_xy=True)
    if ne110 is not None:
        g = ne110.to_crs(rob)
        g.plot(ax=axA, color="#EDEDED", edgecolor="0.55", linewidth=0.25)
        g[adm(g).isin(["Kazakhstan"])].plot(ax=axA, color="#F4C7A6", edgecolor="0.35", linewidth=0.3)
        g[adm(g).isin(["Switzerland", "United States of America"])].plot(ax=axA, color="#BBD7EA", edgecolor="0.35", linewidth=0.3)
    else:
        axA.text(0.5, 0.5, "BASE MAP NOT AVAILABLE", transform=axA.transAxes, ha="center", color="darkred")
    for lo in range(-180, 181, 60):
        axA.plot(*zip(*[tr.transform(lo, la) for la in np.linspace(-85, 85, 60)]), color="0.45", lw=0.35, ls=(0, (1, 2)))
    for la in range(-60, 61, 30):
        axA.plot(*zip(*[tr.transform(lo, la) for lo in np.linspace(-180, 180, 120)]), color="0.45", lw=0.35, ls=(0, (1, 2)))
    for lab, lo, la, mk, col, off in (("KZ", 77.05, 43.13, "*", "#D55E00", (7, 3)), ("CH", 8.8, 46.4, "^", "#0072B2", (-3, 8)), ("US", -111.6, 40.62, "^", "#0072B2", (-3, -13))):
        x, y = tr.transform(lo, la)
        axA.plot(x, y, mk, ms=10 if mk == "*" else 6.5, color=col, mec="k", mew=0.5, zorder=5)
        J.halo(axA.annotate(lab, (x, y), xytext=off, textcoords="offset points", fontsize=8.5, fontweight="bold", zorder=6), lw=2.2)
    axA.set_aspect("equal"); axA.set_xticks([]); axA.set_yticks([]); axA.set_xlabel(""); axA.set_ylabel("")
    for s in axA.spines.values():
        s.set_linewidth(0.8)
    J.panel_title(axA, "a", "World", right="Robinson")
    laea = CRS.from_proj4("+proj=laea +lat_0=45 +lon_0=70 +datum=WGS84")
    tl = Transformer.from_crs(4326, laea, always_xy=True)
    if ne50 is not None:
        g5 = ne50.to_crs(laea)
        g5.plot(ax=axB, color="#EDEDED", edgecolor="0.55", linewidth=0.3)
        g5[adm(g5).isin(["Kazakhstan"])].plot(ax=axB, color="#F4C7A6", edgecolor="0.3", linewidth=0.45)
    else:
        axB.text(0.5, 0.5, "BASE MAP NOT AVAILABLE", transform=axB.transAxes, ha="center", color="darkred")
    cc = [tl.transform(x, y) for x in np.linspace(46, 94, 25) for y in np.linspace(37, 56, 25)]
    axB.set_xlim(min(c[0] for c in cc), max(c[0] for c in cc)); axB.set_ylim(min(c[1] for c in cc), max(c[1] for c in cc))
    for lo in range(45, 100, 10):
        axB.plot(*zip(*[tl.transform(lo, la) for la in np.linspace(34, 58, 40)]), color="0.45", lw=0.35, ls=(0, (1, 2)))
    for la in range(36, 58, 5):
        axB.plot(*zip(*[tl.transform(lo, la) for lo in np.linspace(40, 100, 60)]), color="0.45", lw=0.35, ls=(0, (1, 2)))
    rx, ry = tl.transform(77.025, 43.15)
    axB.plot(rx, ry, "o", ms=12, mfc="none", mec="#D55E00", mew=1.6, zorder=6)
    ax_, ay_ = tl.transform(76.9454, 43.2380)
    axB.plot(ax_, ay_, "o", ms=3.5, color="k", zorder=7)
    J.halo(axB.annotate("Almaty", (ax_, ay_), xytext=(-9, 8), textcoords="offset points", fontsize=8, ha="right", zorder=7), lw=2.2)
    kx, ky = tl.transform(66.5, 48.2)
    J.halo(axB.text(kx, ky, "KAZAKHSTAN", fontsize=8, color="0.25", ha="center", style="italic"), lw=2.0)
    axB.set_aspect("equal"); axB.set_xticks([]); axB.set_yticks([]); axB.set_xlabel(""); axB.set_ylabel("")
    for s in axB.spines.values():
        s.set_linewidth(0.8)
    J.panel_title(axB, "b", "Central Asia", right="Lambert azimuthal")
    # ---- (c) hero map
    y_c = 0.1 + 0.3 + top_h + 0.5
    axC = pg.axes(0.5, y_c, wc, hc)
    if jx.ov is not None:
        axC.imshow(ov_relief(jx, "color", 2), extent=jx.ov["extent"], interpolation="nearest", zorder=1)
    J.style_axes(axC, ext)
    axC.set_facecolor(L.COL_NODATA)
    lbl = {"medeu": ("tl", "Medeu"), "shymbulak": ("tr", "Shymbulak"), "kok_zhailau": ("br", "Kok-Zhailau V1"), "kok_zhailau_osm": ("bl", "Kok-Zhailau V2")}
    for key in K.KZ:
        d = ctx.sites.get(key)
        if d is None:
            continue
        e = d["extent"]
        col = WCOL[key]
        axC.plot([e[0], e[1], e[1], e[0], e[0]], [e[2], e[2], e[3], e[3], e[2]], color="white", lw=3.6, zorder=5, alpha=0.9)
        axC.plot([e[0], e[1], e[1], e[0], e[0]], [e[2], e[2], e[3], e[3], e[2]], color=col, lw=1.9, zorder=5.5)
        J.plot_outline(axC, d["terr_utm"], color=col, lw=1.8, zorder=6, halo_lw=1.6)
        J.plot_outline(axC, d["foot_utm"], color=col, lw=1.3, ls=(0, (4, 2)), zorder=6, halo_lw=1.6)
        cx, cy = d["cxy"]
        axC.plot(cx, cy, "D" if key == "kok_zhailau" else "o", ms=6, color=col, mec="k", mew=0.8, zorder=8)
        pos, txt = lbl[key]
        dx, dy = 0.012 * (ext[1] - ext[0]), 0.016 * (ext[3] - ext[2])
        x = e[0] + dx if pos[1] == "l" else e[1] - dx
        y = e[3] - dy if pos[0] == "t" else e[2] + dy
        J.halo(axC.text(x, y, txt, fontsize=9, fontweight="bold", ha="left" if pos[1] == "l" else "right", va="top" if pos[0] == "t" else "bottom", zorder=9), lw=3.0)
        jx.shares.append(dict(figure="A", panel="c", site=key, quantity="processing window", crs=d["meta"]["crs"], window_xmin=e[0], window_xmax=e[1], window_ymin=e[2], window_ymax=e[3]))
    rec = []
    J.furniture(axC, 32643, ext, (77.02, 43.15), n_max=3.2, bar_frac=0.22, rec=rec)
    jx.fur("A", "c", "overview", rec)
    J.panel_title(axC, "c", "Medeu, Shymbulak and Kok-Zhailau study windows", right=utm_label(32643))
    # vertical colour bar
    if jx.ov is not None:
        z = jx.ov["z"]
        zz = z[np.isfinite(z)]
        vmin, vmax = math.floor(float(np.percentile(zz, 0.2)) / 100) * 100, math.ceil(float(np.percentile(zz, 99.8)) / 100) * 100
        J.hypso_colorbar(pg.fig, [(0.5 + wc + 0.22) / W, 1 - (y_c + hc * 0.82) / H, 0.17 / W, hc * 0.64 / H], vmin, vmax, step=500,
                         label="Elevation, m (Copernicus GLO-30 DSM)", vertical=True)
    hs = [Patch(fc="none", ec="0.2", lw=1.8, label="Processing window"), Line2D([], [], color="0.2", lw=1.8, label="OSM polygon"),
          Line2D([], [], color="0.2", lw=1.3, ls=(0, (4, 2)), label="Derived footprint"), Line2D([], [], color="0.4", marker="o", ls="", ms=6, mec="k", label="Site centre")]
    pg.legend_row(hs, y_bottom=0.08)
    dsrc = K.dem_source_line(ctx)
    short = ("Study area. (a) Location of the Kazakhstan study sites (KZ) and of the Swiss (CH) and US lidar validation regions. (b) Central Asia with the enlarged window. "
             "(c) Medeu, Shymbulak and two alternative Kok-Zhailau study windows (V1, V2) on Copernicus GLO-30 relief, 76.85-77.20 deg E, 43.05-43.25 deg N, UTM zone 43N. "
             "Coloured rectangles are analysis windows, not administrative borders. Solid lines are OpenStreetMap polygons and dashed lines are footprints derived from mapped objects; neither is an official boundary.")
    tech = (f"Map (c): {dsrc}; window frame = bounding box of the 76.85-77.20E, 43.05-43.25N quadrilateral in EPSG:32643 (the quadrilateral is rotated by the grid convergence, so the frame is slightly larger). "
            f"{relief_note(jx, 2, 'color')} Scale bar: exact metres in EPSG:32643; graticule from pyproj; north arrow rotated by the meridian convergence (values in tables/map_furniture_parameters.csv). "
            "Panel (a): Natural Earth 1:110m admin-0 countries, Robinson projection; panel (b): Natural Earth 1:50m, Lambert azimuthal equal-area (lat0 45N, lon0 70E); no scale bars because scale varies across these maps. "
            "Medeu: the only OSM polygon is a 0.043 km2 sports-centre polygon (not the resort); Shymbulak: OSM winter-sports polygon; footprints are derived (buffer 250 m, erosion 200 m of mapped aerialways/pistes/tourism/leisure features within 2.5-3.5 km of the configured centre). "
            "Kok-Zhailau V1 = configured centre (provisional, diamond); V2 = centre from OSM-named objects, about 5.9 km west. All outlines are exploratory. "
            f"Overview raster: {jx.ov['source'] if jx.ov else 'n/a'}.")
    save(jx, pg.fig, "R40_Fig_A_study_area", short, tech)


def fig_A_supp(jx):
    plt = apply_style()
    ctx = jx.ctx
    keys = [k for k in K.VAL if k in ctx.sites]
    if not keys:
        return
    pg, rects, pw = grid_layout(plt, [J.aspect(ctx.sites[k]["extent"]) for k in keys], title_h=0.42, extra_bottom=0.5)
    for i, (k, (x, y, w, h)) in enumerate(zip(keys, rects)):
        d = ctx.sites[k]
        ax = pg.axes(x, y, w, h)
        ax.imshow(site_relief(jx, k, "gray", 3), extent=d["extent"], interpolation="nearest", zorder=1)
        J.plot_outline(ax, d["foot_utm"], ls=(0, (4, 2)), lw=1.0)
        J.plot_outline(ax, d["terr_utm"], lw=1.3)
        ax.plot(*d["cxy"], "o", ms=6, color="#009E73", mec="k", mew=0.8, zorder=8)
        J.style_axes(ax, d["extent"])
        rec = []
        J.furniture(ax, d["epsg"], d["extent"], d["center"], rec=rec)
        jx.fur("A-supp", chr(97 + i), k, rec)
        J.panel_title(ax, chr(97 + i), K.SHORT[k], right=utm_label(d["epsg"]))
    from matplotlib.lines import Line2D
    pg.legend_row([Line2D([], [], color="k", lw=1.4, label="OSM polygon"), Line2D([], [], color="k", lw=1.2, ls=(0, (4, 2)), label="Derived footprint"),
                   Line2D([], [], color="#009E73", marker="o", ls="", ms=6, mec="k", label="Site centre")], y_bottom=0.1)
    short = ("Lidar validation sites. Davos-Parsenn and Zermatt-Gornergrat (Switzerland) and Alta-Snowbird and Park City (USA), each in its own UTM zone. "
             "Solid lines are OpenStreetMap polygons where one was found and dashed lines are footprints derived from mapped objects; neither is an official boundary.")
    tech = (f"Reference lidar DTMs: swissALTI3D 2 m (swisstopo OGD; LN02) and USGS 3DEP 1/3 arc-second (NAVD88). {relief_note(jx)} "
            "Scale bars: exact metres in each local UTM CRS; graticule from pyproj; north arrows rotated by the meridian convergence (tables/map_furniture_parameters.csv). Site centre = configured centre.")
    save(jx, pg.fig, "R40_Fig_A_suppl_validation_sites", short, tech)


# ======================================================================================================== Figure B
def fig_B(jx, t):
    plt = apply_style()
    ctx = jx.ctx
    keys = [k for k in K.KZ if k in ctx.sites]
    if not keys:
        return
    nm = {7.5: "R40_Fig_B_suppl_decisions_7.5deg", 15: "R40_Fig_B_decisions_15deg", 25: "R40_Fig_B_suppl_decisions_25deg"}[t]
    pg, rects, pw = grid_layout(plt, [J.aspect(ctx.sites[k]["extent"]) for k in keys], title_h=0.58, extra_bottom=0.62)
    for i, (k, (x, y, w, h)) in enumerate(zip(keys, rects)):
        d = ctx.sites[k]
        ax = pg.axes(x, y, w, h)
        ax.imshow(site_relief(jx, k, "gray", 3), extent=d["extent"], interpolation="nearest", zorder=1)
        ax.imshow(L.decision_rgba(d["dec"][t], alpha=DEC_FIG_ALPHA), extent=d["extent"], interpolation="nearest", zorder=3)
        J.plot_outline(ax, d["foot_utm"], ls=(0, (4, 2)), lw=1.0)
        J.plot_outline(ax, d["terr_utm"], lw=1.3)
        J.style_axes(ax, d["extent"])
        rec = []
        J.furniture(ax, d["epsg"], d["extent"], d["center"], rec=rec)
        jx.fur(nm, chr(97 + i), k, rec)
        sh = L.class_shares(d["dec"][t])
        J.panel_title(ax, chr(97 + i), K.SHORT[k], right=utm_label(d["epsg"]),
                      stats=f"BELOW {sh['BELOW_pct']:.1f} · ABOVE {sh['ABOVE_pct']:.1f} · ABSTAIN {sh['ABSTAIN_pct']:.1f} %")
        jx.shares.append(dict(figure=nm, panel=chr(97 + i), site=k, threshold_deg=t, n_valid_px=sh["n_px"], cell_m=d["res"], BELOW_pct=sh["BELOW_pct"], ABOVE_pct=sh["ABOVE_pct"],
                              ABSTAIN_pct=sh["ABSTAIN_pct"], crs=d["meta"]["crs"], contour_id=K.contour_id(d, "context"),
                              source_raster=f"inputs/rasters/{k}/decision_combined_t{t}_risk2.tif"))
    pg.legend_row(decision_handles(), y_bottom=0.08, ncol=3)
    short = (f"Threshold decisions at {t:g} deg slope for the four Kazakhstan study windows (Medeu, Shymbulak, Kok-Zhailau V1 and V2). Colours show the classes of the combined abstention rule "
             "(BELOW, ABOVE, ABSTAIN); grey = no decision. The rule was trained on lidar-validated sites in Switzerland and the USA and is transferred here, so the error is not measured at these sites. "
             "Percentages are shares of valid 30 m pixels per window. Outlines are exploratory and not official boundaries.")
    tech = (f"Classes exactly as in decision_combined_t{t:g}_risk2.tif (codes 0 BELOW, 1 ABOVE, 2 ABSTAIN, 255 no decision; target training risk 0.02), 30 m cells, UTM 43N (EPSG:32643); "
            f"class colours at {int(DEC_FIG_ALPHA * 100)} % opacity over the relief. {relief_note(jx)} Source DEM: {K.dem_source_line(ctx)}. "
            "Outlines: solid = OSM-mapped named polygon (exploratory); dashed = footprint derived from mapped aerialways/pistes/tourism/leisure features (not an official boundary). "
            "Pixel-to-polygon masks: pixel centre inside the polygon (rasterio rasterize, all_touched=False). Per-mask counts, areas, shares and contour ids: tables/map_summary_figB.csv; "
            "check against decisions_by_site.csv: tables/verification_figB_vs_decisions_by_site.csv (30 of 30 comparisons OK in the first edition; this edition re-derives them: tables/consistency_vs_source_package.csv). "
            "Shares printed in the panel titles are recomputed from the drawn arrays (tables/journal_figure_shares_as_drawn.csv). Scale bar: exact metres in EPSG:32643; north arrow rotated by the meridian convergence (tables/map_furniture_parameters.csv).")
    save(jx, pg.fig, nm, short, tech)


# ======================================================================================================== Figure C
def _diff_panel(jx, ax, d, a, b, vm, cmap, fig_name, tag, lon_labels=True, lat_labels=True, with_stats_title=None):
    diff = np.where(np.isfinite(a) & np.isfinite(b), a - b, np.nan)
    ax.imshow(diff, extent=d["extent"], cmap=cmap, vmin=-vm, vmax=vm, interpolation="nearest", zorder=2)
    ax.set_facecolor(L.COL_NODATA)
    J.plot_outline(ax, d["foot_utm"], ls=(0, (4, 2)), lw=0.9, halo_lw=1.4)
    J.style_axes(ax, d["extent"])
    rec = []
    J.furniture(ax, d["epsg"], d["extent"], d["center"], lon_labels=lon_labels, lat_labels=lat_labels, rec=rec, n_max=2.6)
    jx.fur(fig_name, tag, d["key"], rec)
    st = L.slope_diff_stats(a, b)
    jx.shares.append(dict(figure=fig_name, panel=tag, site=d["key"], quantity="slope difference", n_common_px=st.get("common_px", 0), mean_diff_deg=st.get("mean_diff_deg"),
                          mae_deg=st.get("mae_deg"), rmse_deg=st.get("rmse_deg"), crs=d["meta"]["crs"]))
    return st


def fig_C(jx):
    plt = apply_style()
    ctx = jx.ctx
    cmap = plt.get_cmap("RdBu_r").copy()
    cmap.set_bad(L.COL_NODATA)
    vm = 10.0
    keys = [k for k in K.KZ if k in ctx.sites]
    if keys:
        nm = "R40_Fig_C1_kazakhstan_inter_dem_slope_difference"
        pg, rects, pw = grid_layout(plt, [J.aspect(ctx.sites[k]["extent"]) for k in keys], title_h=0.58, extra_bottom=0.95)
        for i, (k, (x, y, w, h)) in enumerate(zip(keys, rects)):
            d = ctx.sites[k]
            ax = pg.axes(x, y, w, h)
            st = _diff_panel(jx, ax, d, d["nas_slope"], d["cop_slope"], vm, cmap, nm, chr(97 + i))
            J.panel_title(ax, chr(97 + i), K.SHORT[k], right=utm_label(d["epsg"]),
                          stats=f"mean {st.get('mean_diff_deg', float('nan')):+.2f}° · MAE {st.get('mae_deg', float('nan')):.2f}°")
        sm = plt.cm.ScalarMappable(norm=plt.Normalize(-vm, vm), cmap=cmap)
        cb = pg.fig.colorbar(sm, cax=pg.fig.add_axes([0.25, 0.3 / pg.h, 0.5, 0.14 / pg.h]), orientation="horizontal")
        cb.set_label("Slope difference NASADEM − Copernicus GLO-30, degrees", fontsize=J.FS_BASE)
        cb.ax.tick_params(labelsize=J.FS_SMALL)
        from matplotlib.patches import Patch
        pg.fig.legend(handles=[Patch(fc=L.COL_NODATA, ec="k", lw=0.5, label="No data in either DEM")], loc="lower center", bbox_to_anchor=(0.5, 0.02 / pg.h), frameon=False, fontsize=J.FS_BASE)
        short = ("Slope differences between two global DEMs (NASADEM minus Copernicus GLO-30) in the four Kazakhstan windows, on the common valid mask. "
                 "The map shows disagreement between DEMs, not accuracy: no lidar reference exists for Kazakhstan. Dashed line = derived footprint (exploratory).")
        tech = (f"Both DEMs are DSMs resampled bilinearly to the same 30 m UTM 43N grid; slopes by the Horn (1981) 3x3 method; common valid mask = pixels with a complete 3x3 neighbourhood in both DEMs. "
                "ALOS AW3D30 and FABDEM are not mapped (licence/redistribution; see exceptions report). Statistics (common pixels, mean, SD, MAE, RMSE, 95th percentile, class disagreement at 7.5/15/25 deg): "
                "tables/inter_dem_slope_difference_summary.csv. Colour scale diverging, symmetric, saturating at ±10 deg. Grey = no data. Scale bar: exact metres in EPSG:32643.")
        save(jx, pg.fig, nm, short, tech)
    for grp, label, sites_ in (("ch", "Switzerland", ("davos_parsenn", "zermatt_gornergrat")), ("us", "USA", ("alta_snowbird", "park_city"))):
        vk = [k for k in sites_ if k in ctx.sites]
        if not vk:
            continue
        nm = f"R40_Fig_C2_{'switzerland' if grp == 'ch' else 'usa'}_dem_vs_lidar_slope_difference"
        lm, rm, gap, W = 0.82, 0.12, 0.32, J.FIG_W
        pw = (W - lm - rm - 2 * gap) / 3
        ars = [J.aspect(ctx.sites[k]["extent"]) for k in vk]
        rh = [pw * a for a in ars]
        H = 0.12 + 0.34 + sum(rh) + len(vk) * 0.3 + 1.0
        pg = J.Page(plt, W, H)
        heads = ["Copernicus − lidar", "NASADEM − lidar", "NASADEM − Copernicus"]
        y = 0.12 + 0.34
        for r, k in enumerate(vk):
            d = ctx.sites[k]
            pairs = [(d["cop_slope"], d["ref_slope"]), (d["nas_slope"], d["ref_slope"]), (d["nas_slope"], d["cop_slope"])]
            for c, (a, b) in enumerate(pairs):
                ax = pg.axes(lm + c * (pw + gap), y, pw, rh[r])
                st = _diff_panel(jx, ax, d, a, b, vm, cmap, nm, f"{r + 1}{'abc'[c]}", lon_labels=(r == len(vk) - 1), lat_labels=(c == 0))
                ax.text(0.035, 0.965, f"MAE {st.get('mae_deg', float('nan')):.1f}°", transform=ax.transAxes, ha="left", va="top", fontsize=J.FS_SMALL, zorder=12,
                        bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.5))
                if r == 0:
                    ax.set_title(heads[c], fontsize=J.FS_BASE + 0.5, fontweight="bold", pad=4)
            pg.fig.text(0.1 / W, 1 - (y + rh[r] / 2) / H, f"{K.SHORT[k]}\n{utm_label(d['epsg'])}", rotation=90, ha="left", va="center", fontsize=J.FS_BASE + 0.5, fontweight="bold", linespacing=1.3)
            y += rh[r] + 0.3
        sm = plt.cm.ScalarMappable(norm=plt.Normalize(-vm, vm), cmap=cmap)
        cb = pg.fig.colorbar(sm, cax=pg.fig.add_axes([0.25, 0.62 / H, 0.5, 0.14 / H]), orientation="horizontal")
        cb.set_label("Slope difference, degrees", fontsize=J.FS_BASE)
        cb.ax.tick_params(labelsize=J.FS_SMALL)
        from matplotlib.patches import Patch
        pg.fig.legend(handles=[Patch(fc=L.COL_NODATA, ec="k", lw=0.5, label="No data")], loc="lower center", bbox_to_anchor=(0.5, 0.05 / H), frameon=False, fontsize=J.FS_BASE)
        short = (f"Slope differences at the lidar validation sites in {label}: global DEM minus lidar-DTM reference and NASADEM minus Copernicus GLO-30, on the common valid mask of each pair. "
                 "The lidar DTM is block-averaged to the 30 m cell before the slope is computed (support-matched). MAE is the mean absolute difference.")
        tech = ("Global DEMs are DSMs (canopy and buildings included); the reference is a bare-earth DTM; no co-registration was applied. Slopes by the Horn (1981) 3x3 method on the 30 m grid. "
                "Zermatt includes glaciers whose surface changed between the lidar epoch and the DSMs. Statistics: tables/inter_dem_slope_difference_summary.csv. "
                "Each panel in its own local UTM CRS with an exact metric scale bar; graticule labels on the left column and the bottom row only; dashed line = derived footprint (exploratory); grey = no data.")
        save(jx, pg.fig, nm, short, tech)


# ======================================================================================================== Figure D
def fig_D(jx):
    plt = apply_style()
    ctx = jx.ctx
    from matplotlib.lines import Line2D
    for key in K.VAL:
        d = ctx.sites.get(key)
        if d is None:
            continue
        rf = float(ctx.cfg["validation"][key]["ref_res_m"])
        p = ctx.raster_path(key, f"reference_native_{int(rf)}m_m.tif")
        native = nm_ = None
        if p.exists():
            native, nm_ = K.read_raster(p)
        else:
            K.exc("ERROR", "Figure D", f"native lidar window missing for {key}; profile is drawn from the 30 m block-mean reference only", p.name)
        ref_name = "swissALTI3D (LN02, 2 m; swisstopo OGD)" if ctx.cfg["validation"][key]["reference"] == "swissalti3d" else "USGS 3DEP 1/3 arc-second (NAVD88, ~10 m)"
        W, H = J.FIG_W, 5.75
        pg = J.Page(plt, W, H)
        if native is not None:
            rgb, _ = J.relief(native, nm_["res"], k=1 if nm_["res"] <= 3 else 3, kind="gray")
            mext = K.extent_of(nm_)
        else:
            rgb, _ = J.relief(d["cop"], d["res"], k=3, kind="gray")
            mext = (d["cxy"][0] - 1700, d["cxy"][0] + 1700, d["cxy"][1] - 1700, d["cxy"][1] + 1700)
        mw = 2.55
        axm = pg.axes(0.62, 0.5, mw, mw * J.aspect(mext))
        axm.imshow(rgb, extent=(K.extent_of(nm_) if native is not None else d["extent"]), interpolation="nearest", zorder=1)
        J.style_axes(axm, mext)
        cols = {"WE": "#D55E00", "SN": "#0072B2"}
        for kind in ("WE", "SN"):
            xs, ys, t = K.profile_geometry(d, kind, 1500.0, 30.0)
            axm.plot([xs[0], xs[-1]], [ys[0], ys[-1]], color="white", lw=3.6, zorder=5, alpha=0.9)
            axm.plot([xs[0], xs[-1]], [ys[0], ys[-1]], color=cols[kind], lw=1.8, zorder=6)
            J.halo(axm.text(xs[-1], ys[-1], "E" if kind == "WE" else "N", color=cols[kind], fontsize=9, fontweight="bold", zorder=7, ha="left" if kind == "WE" else "center",
                            va="center" if kind == "WE" else "bottom"), lw=2.6)
            J.halo(axm.text(xs[0], ys[0], "W" if kind == "WE" else "S", color=cols[kind], fontsize=9, fontweight="bold", zorder=7, ha="right" if kind == "WE" else "center",
                            va="center" if kind == "WE" else "top"), lw=2.6)
        axm.plot(*d["cxy"], "o", ms=5, color="k", mec="white", mew=0.8, zorder=8)
        rec = []
        J.furniture(axm, d["epsg"], mext, d["center"], rec=rec, n_max=2.6)
        jx.fur(f"R40_Fig_D_profile_{key}", "map", key, rec)
        J.panel_title(axm, "a", K.SHORT[key], right=utm_label(d["epsg"]))
        gy = [0.55, 3.05]
        rows_here = []
        for r, kind in enumerate(("WE", "SN")):
            step = rf if native is not None else 30.0
            xs, ys, t = K.profile_geometry(d, kind, 1500.0, step)
            z_nat = L.sample_bilinear(native, nm_["x0"], nm_["y1"], nm_["res"], xs, ys) if native is not None else np.full_like(t, np.nan)
            smp = lambda a: L.sample_bilinear(a, d["x0"], d["y1"], 30.0, xs, ys)  # noqa: E731
            z30, zc, zn = smp(d["ref30"]), smp(d["cop"]), smp(d["nas"])
            ax = pg.axes(3.95, gy[r], 3.02, 1.3)
            if native is not None:
                ax.plot(t, z_nat, color="k", lw=0.7)
            ax.plot(t, z30, color="0.45", lw=1.6)
            ax.plot(t, zc, color="#D55E00", lw=1.2)
            ax.plot(t, zn, color="#0072B2", lw=1.2)
            ax.set_ylabel("Elevation, m")
            ax.grid(color="0.88", lw=0.5)
            ax.tick_params(labelbottom=False)
            ax.set_title(f"({'bc'[r]}) Transect {'W–E' if kind == 'WE' else 'S–N'}, 3 km", loc="left", fontsize=J.FS_TITLE, fontweight="bold", pad=4)
            axd = pg.axes(3.95, gy[r] + 1.42, 3.02, 0.72, sharex=ax)
            ok = np.isfinite(z30)
            note = []
            for nm2, zz, col in (("Copernicus", zc, "#D55E00"), ("NASADEM", zn, "#0072B2")):
                dd = zz - z30
                dd = dd - np.nanmedian(dd)
                axd.plot(t, dd, color=col, lw=1.0)
                v = np.isfinite(dd)
                row = dict(site=key, transect=kind, dem=nm2, n_points=int(v.sum()), rmse_debiased_m=float(np.sqrt(np.nanmean(dd[v] ** 2))) if v.any() else float("nan"),
                           median_offset_m=float(np.nanmedian(zz - z30)) if v.any() else float("nan"), relief_ref30_m=float(np.nanmax(z30) - np.nanmin(z30)) if ok.any() else float("nan"),
                           reference_native=("yes" if native is not None else "NOT AVAILABLE"), step_m=step, contour_id=f"PROFILE:{key}:{kind}:3000m")
                rows_here.append(row)
                jx.prof.append(row)
                note.append(f"{nm2[:3]} {row['rmse_debiased_m']:.1f}")
            axd.axhline(0, color="k", lw=0.6)
            axd.set_ylabel("ΔZ, m")
            axd.grid(color="0.88", lw=0.5)
            axd.text(0.985, 0.94, "RMSE, m: " + " · ".join(note), transform=axd.transAxes, ha="right", va="top", fontsize=J.FS_SMALL, bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.2))
            if r == 1:
                axd.set_xlabel("Distance from the site centre, m")
            else:
                axd.tick_params(labelbottom=False)
        hs = [Line2D([], [], color="k", lw=0.9, label=f"Lidar DTM, native {rf:g} m" if native is not None else "Lidar DTM native (not available)"),
              Line2D([], [], color="0.45", lw=2.0, label="Lidar DTM, 30 m block mean"), Line2D([], [], color="#D55E00", lw=1.6, label="Copernicus GLO-30"),
              Line2D([], [], color="#0072B2", lw=1.6, label="NASADEM"), Line2D([], [], color="#D55E00", lw=2.0, label="Transect W–E"), Line2D([], [], color="#0072B2", lw=2.0, label="Transect S–N")]
        # transect colours on the map reuse the DEM colours; keep the map key explicit instead
        hs = hs[:4]
        pg.fig.legend(handles=hs, loc="upper left", bbox_to_anchor=(0.1 / W, 1 - 3.6 / H), frameon=False, fontsize=J.FS_BASE, handlelength=2.2, ncol=1)
        txt = ["Profile map: orange W–E, blue S–N.", "Lower panels: DEM − 30 m lidar, median offset removed", "(RMSE in each panel, tables/profile_summary.csv)."]
        pg.fig.text(0.1 / W, 1 - 5.1 / H, "\n".join(txt), fontsize=J.FS_SMALL, va="top", ha="left", linespacing=1.35)
        short = (f"Measured terrain profiles at {K.SHORT[key]}: two 3 km grid-aligned transects through the site centre (W–E, S–N) from the lidar DTM at native resolution, the same DTM averaged to the 30 m cell "
                 "(support-matched reference) and the two global DSMs. Lower panels show DEM minus 30 m reference after removing the median offset.")
        tech = (f"Reference: {ref_name}; candidates Copernicus GLO-30 (EGM2008) and NASADEM (EGM96), 30 m, sampled bilinearly. Vertical datums are not harmonised (geoid offsets of metres); the lower panels remove the median offset along each transect. "
                f"DSMs include canopy/buildings, the reference is bare earth; no co-registration. Transects: rule-based (3 km, grid-aligned, through the configured site centre; derived/vector/profile_lines.geojson), not selected for agreement. "
                f"Reference epoch: {K.ref_epoch(ctx, key)}; Copernicus item date {K.prov_of(ctx, key, 'cop-dem-glo-30')[1]}; NASADEM item date {K.prov_of(ctx, key, 'nasadem')[1]}. "
                "Profile values: tables/profile_samples.csv; statistics: tables/profile_summary.csv. Map: hillshade of the lidar DTM (native resolution for 2 m data, 3x bicubic display resampling for the 10 m 3DEP window), multi-directional, grey; "
                "scale bar exact metres in the local UTM CRS; north arrow rotated by the meridian convergence.")
        save(jx, pg.fig, f"R40_Fig_D_profile_{key}", short, tech)


# ======================================================================================================== Figure E
def fig_E(jx, pts_by_site):
    plt = apply_style()
    ctx = jx.ctx
    from matplotlib.lines import Line2D
    sites = [s_ for s_ in ("kz_all",) + tuple(K.VAL) if s_ in pts_by_site]
    if not sites:
        return
    kz = kz_extent()
    exts = []
    for s_ in sites:
        exts.append(kz if s_ == "kz_all" else ctx.sites[s_]["extent"])
    ars = [J.aspect(e) for e in exts] + [1.0] * (6 - len(sites))
    pg, rects, pw = grid_layout(plt, ars[:6], cols=3, lm=0.5, rm=0.1, gap=0.42, title_h=0.55, bottom_h=0.3, extra_bottom=0.15)
    for i, s_ in enumerate(sites):
        x, y, w, h = rects[i]
        ax = pg.axes(x, y, w, h)
        P = pts_by_site[s_]
        if s_ == "kz_all":
            if jx.ov is not None:
                ax.imshow(ov_relief(jx, "gray", 2), extent=jx.ov["extent"], interpolation="nearest", zorder=1)
            ext, epsg, center, ttl = kz, 32643, (77.02, 43.15), "Kazakhstan"
        else:
            d = ctx.sites[s_]
            ax.imshow(site_relief(jx, s_, "gray", 3), extent=d["extent"], interpolation="nearest", zorder=1)
            ext, epsg, center, ttl = d["extent"], d["epsg"], d["center"], K.SHORT[s_]
        J.style_axes(ax, ext)
        ax.set_facecolor(L.COL_NODATA)
        xx, yy, rej = P["x"], P["y"], ~P["common"]
        inx = (xx >= ext[0]) & (xx <= ext[1]) & (yy >= ext[2]) & (yy <= ext[3])
        c_only, len_only, stt = P["common"] & ~P["lenient"] & inx, P["lenient"] & ~P["strict"] & inx, P["strict"] & inx
        ax.scatter(xx[rej & inx], yy[rej & inx], s=0.5, c="#555555", lw=0, alpha=0.4, zorder=3, rasterized=True)
        ax.scatter(xx[c_only], yy[c_only], s=1.0, c="#E6E6E6", lw=0, zorder=3, rasterized=True)
        ax.scatter(xx[len_only], yy[len_only], s=3.4, c="#E69F00", lw=0, zorder=4, rasterized=True)
        ax.scatter(xx[stt], yy[stt], s=6.5, c="#B2182B", lw=0.2, edgecolors="k", zorder=5, rasterized=True)
        rec = []
        J.furniture(ax, epsg, ext, center, rec=rec, n_max=2.4)
        jx.fur("R40_Fig_E_atl08_track_samples", chr(97 + i), s_, rec)
        J.panel_title(ax, chr(97 + i), ttl, right=utm_label(epsg), stats=f"strict {int(stt.sum()):,} · lenient {int((P['lenient'] & inx).sum()):,}", fs=J.FS_BASE + 0.5)
        jx.shares.append(dict(figure="E", panel=chr(97 + i), site=s_, quantity="ATL08 segments in view", n_in_view=int(inx.sum()), n_lenient=int((P["lenient"] & inx).sum()),
                              n_strict=int(stt.sum()), crs=f"EPSG:{epsg}"))
    # panel (f): legend + statement
    x, y, w, h = rects[5]
    axf = pg.axes(x, y, w, h)
    axf.axis("off")
    hs = [Line2D([], [], marker="o", ls="", ms=6, color="#B2182B", mec="k", mew=0.3, label="Strict (< 5 m)"),
          Line2D([], [], marker="o", ls="", ms=5, color="#E69F00", label="Lenient only (5–15 m)"),
          Line2D([], [], marker="o", ls="", ms=4, color="#E6E6E6", mec="0.5", mew=0.3, label="Other, passed filters"),
          Line2D([], [], marker="o", ls="", ms=4, color="#555555", alpha=0.6, label="Rejected by filters")]
    axf.legend(handles=hs, loc="upper left", bbox_to_anchor=(0.0, 1.02), frameon=False, fontsize=J.FS_BASE, handletextpad=0.5, labelspacing=0.7)
    axf.text(0.0, 0.34, "Track samples only:\na partial reference,\nnot validation of\nthe full maps.", transform=axf.transAxes, fontsize=J.FS_BASE, va="top", ha="left", linespacing=1.35,
             fontweight="bold")
    dts = "; ".join(f"{('Kazakhstan' if k == 'kz_all' else K.SHORT[k])} {v[0]} to {v[1]} ({v[2]} dates)" for k, v in ctx.atl_dates.items())
    short = ("Real ICESat-2 ATL08 terrain segments (100 m along-track) over the Kazakhstan window and the four lidar validation sites. Strict (uncertainty < 5 m) and lenient (< 15 m) subsets are shown on top of the other segments. "
             "Segments exist only along ground tracks; they are a partial independent reference and must not be read as validation of any full slope map.")
    tech = ("ATL08 v007; common filters fixed before inspecting DEM errors: terrain height valid, >= 30 terrain photons, ATM cloud flag <= 2; lenient = height uncertainty < 15 m; strict = < 5 m. "
            "The strict subset is 1-4 % of all segments in every area. Counts in panel titles refer to the displayed extent; full-bbox counts: tables/atl08_filter_counts.csv. Heights are ellipsoidal (no geoid correction). "
            f"Background: {('full-window ' if jx.ov and jx.ov['complete'] else '')}Copernicus GLO-30 hillshade, grey scale (display resampling as in Figure A for panel a; 3x for b-e). Panel (a): 76.85-77.20 deg E, 43.05-43.25 deg N (UTM 43N); (b)-(e): lidar validation windows, each in its own local UTM CRS. "
            f"Vector layers with quality flags: derived/vector/atl08_segments_and_tracks.gpkg. Granule acquisition dates (from granule names): {dts}.")
    save(jx, pg.fig, "R40_Fig_E_atl08_track_samples", short, tech)


# ======================================================================================================== basemaps, tables, proofs, docs
def write_basemaps(jx):
    import rasterio
    from rasterio.transform import from_origin
    ctx = jx.ctx
    out = jx.out / "basemaps"
    out.mkdir(parents=True, exist_ok=True)
    for key, d in ctx.sites.items():
        rgb, info = jx.rel.get((key, "gray", 3), J.relief(d["cop"], d["res"], k=3, kind="gray"))
        g = np.clip(np.round(rgb[..., 0] * 255), 1, 255).astype("uint8")
        g[info["bad"]] = 0
        k = info["k"]
        p = out / f"relief_gray_{key}_{d['res'] / k:g}m.tif"
        with rasterio.open(p, "w", driver="GTiff", height=g.shape[0], width=g.shape[1], count=1, dtype="uint8", crs=d["meta"]["crs"],
                           transform=from_origin(d["x0"], d["y1"], d["res"] / k, d["res"] / k), nodata=0, compress="deflate") as o:
            o.write(g, 1)
            o.set_band_description(1, "grey hillshade (multi-directional) of Copernicus GLO-30, display resampling; 0 = nodata")
        jx.man.add(p, "georeferenced relief basemap (grey hillshade, 8 bit)", K.dem_source_line(ctx, key) + "; bicubic x3 display resampling, multi-directional hillshade",
                   datum="n/a (shading)", dates=K.prov_of(ctx, key, "cop-dem-glo-30")[1], licence=K.DEM_META["cop-dem-glo-30"]["licence"], notes="for re-styling in GIS/DTP; not an analysis product")
    if jx.ov is not None:
        for kind, kk in (("color", 2),):
            rgb, info = jx.rel.get(("overview", kind, kk), J.relief(jx.ov["z"], jx.ov["res"], k=kk, kind=kind))
            a = J.to_uint8_rgba(rgb, info["bad"])
            m = jx.ov["meta"]
            p = out / f"relief_colour_overview_kz_{m['res'] / kk:g}m.tif"
            with rasterio.open(p, "w", driver="GTiff", height=a.shape[0], width=a.shape[1], count=4, dtype="uint8", crs=m["crs"], transform=from_origin(m["x0"], m["y1"], m["res"] / kk, m["res"] / kk),
                               compress="deflate", photometric="RGB", alpha="YES") as o:
                o.write(np.moveaxis(a, 2, 0))
            jx.man.add(p, "georeferenced colour relief basemap (RGBA, hypsometric tint x hillshade)", jx.ov["source"], dates=K.prov_of(ctx, OVERVIEW_KEY, "cop-dem-glo-30")[1],
                       licence=K.DEM_META["cop-dem-glo-30"]["licence"], notes="tint stops listed in src/carto_journal_lib.py HYPSO; for re-styling")
        for kind, kk, nm_ in (("gray", 2, "gray"),):
            rgb, info = jx.rel.get(("overview", kind, kk), J.relief(jx.ov["z"], jx.ov["res"], k=kk, kind=kind))
            g = np.clip(np.round(rgb[..., 0] * 255), 1, 255).astype("uint8")
            g[info["bad"]] = 0
            m = jx.ov["meta"]
            p = out / f"relief_gray_overview_kz_{m['res'] / kk:g}m.tif"
            with rasterio.open(p, "w", driver="GTiff", height=g.shape[0], width=g.shape[1], count=1, dtype="uint8", crs=m["crs"], transform=from_origin(m["x0"], m["y1"], m["res"] / kk, m["res"] / kk),
                               nodata=0, compress="deflate") as o:
                o.write(g, 1)
            jx.man.add(p, "georeferenced relief basemap (grey hillshade, 8 bit)", jx.ov["source"], dates=K.prov_of(ctx, OVERVIEW_KEY, "cop-dem-glo-30")[1], licence=K.DEM_META["cop-dem-glo-30"]["licence"])


def write_tables(jx):
    t = jx.out / "tables"
    t.mkdir(parents=True, exist_ok=True)
    if jx.furn:
        C.write_csv(t / "map_furniture_parameters.csv", jx.furn)
    if jx.shares:
        C.write_csv(t / "journal_figure_shares_as_drawn.csv", jx.shares)
    if jx.prof:
        C.write_csv(t / "profile_stats_as_drawn.csv", jx.prof)
        st, nd, mx = compare_csv(t / "profile_stats_as_drawn.csv", Path(jx.ctx.pkg) / "tables" / "profile_summary.csv")
        jx.checks.append(dict(table="profile_summary.csv", status=st, n_differing_cells=nd, max_abs_numeric_difference=mx, meaning="profile statistics as drawn vs first package"))
        if st != "IDENTICAL":
            K.exc("ERROR", "consistency", "profile statistics differ from the first package", f"{st}: {nd} cells, max {mx}")
        C.write_csv(t / "consistency_vs_source_package.csv", jx.checks)
    # B shares vs source package table (as drawn)
    try:
        import pandas as pd
        ms = pd.read_csv(Path(jx.ctx.pkg) / "tables" / "map_summary_figB.csv")
        ms = ms[ms["mask"] == "context"]
        bad = 0
        for r in jx.shares:
            if r.get("figure", "").startswith("R40_Fig_B"):
                q = ms[(ms.site == r["site"]) & np.isclose(ms.threshold_deg.astype(float), r["threshold_deg"])]
                if len(q) != 1 or abs(float(q.iloc[0].BELOW_pct) - r["BELOW_pct"]) > 0.05 or abs(float(q.iloc[0].ABOVE_pct) - r["ABOVE_pct"]) > 0.05 or int(q.iloc[0].n_px_valid_decision) != r["n_valid_px"]:
                    bad += 1
        jx.checks.append(dict(table="Figure B panel shares as drawn vs map_summary_figB.csv (context mask)", status="IDENTICAL" if bad == 0 else "DIFFERENT_VALUES", n_differing_cells=bad,
                              max_abs_numeric_difference="", meaning="tolerance 0.05 pp, identical pixel counts"))
        if bad:
            K.exc("ERROR", "consistency", "Figure B drawn shares differ from map_summary_figB.csv", bad)
        C.write_csv(t / "consistency_vs_source_package.csv", jx.checks)
    except Exception as e:  # noqa: BLE001
        K.exc_tb("consistency", "Figure B drawn-vs-table check failed", e)
    # font audit
    rows = jx.fonts
    C.write_csv(t / "font_audit_all_text.csv", rows)
    by = {}
    for r in rows:
        by.setdefault(r["figure"], []).append(r["fontsize_pt"])
    summ = []
    for name, short, tech, w, h in jx.captions:
        v = by.get(name, [])
        mn = min(v) if v else float("nan")
        summ.append(dict(figure=name, width_mm=round(w * 25.4, 1), height_mm=round(h * 25.4, 1), n_text_objects=len(v), min_font_pt=mn, max_font_pt=max(v) if v else float("nan"),
                         min_font_ok_ge_7pt="YES" if v and mn >= J.MIN_FS - 1e-9 else "NO", fits_A4_text_block_with_caption=("YES" if h <= 8.6 else "NO"),
                         width_ok_180mm="YES" if abs(w - J.FIG_W) < 0.02 else "NO"))
        if v and mn < J.MIN_FS - 1e-9:
            K.exc("ERROR", "A4 readability", f"{name}: smallest text {mn} pt < 7 pt")
        if h > 8.6:
            K.exc("WARN", "A4 readability", f"{name}: height {h * 25.4:.0f} mm leaves little room for the caption on an A4 page")
    C.write_csv(t / "a4_readability_audit.csv", summ)
    for n in ("map_furniture_parameters.csv", "journal_figure_shares_as_drawn.csv", "profile_stats_as_drawn.csv", "font_audit_all_text.csv", "a4_readability_audit.csv"):
        if (t / n).exists():
            jx.man.add(t / n, "table", "generated by src/cartography_journal.py", licence=K.LICENCE["own"])
    return summ


def write_captions(jx):
    lines = ["# R40 journal figures: captions", "",
             "Each figure has a SHORT caption (paste into the manuscript) and TECHNICAL notes (methods/supplement). Figures are 180 mm wide, all text >= 7 pt, 300 dpi PNG + PDF + SVG.", ""]
    for name, short, tech, w, h in jx.captions:
        lines += [f"## {name}", "", f"**Caption.** {short}", "", f"**Technical notes.** {tech}", "", f"_Size: {w * 25.4:.0f} x {h * 25.4:.0f} mm._", ""]
    p = jx.out / "captions_journal.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    jx.man.add(p, "captions", "generated with the figures", licence=K.LICENCE["own"])


def a4_proofs(jx):
    from PIL import Image, ImageDraw, ImageFont
    import matplotlib.font_manager as fm
    Image.MAX_IMAGE_PIXELS = None
    font = ImageFont.truetype(fm.findfont("DejaVu Sans"), 38)       # 9 pt at 300 dpi
    fontb = ImageFont.truetype(fm.findfont(fm.FontProperties(family="DejaVu Sans", weight="bold")), 38)
    fonts = ImageFont.truetype(fm.findfont("DejaVu Sans"), 29)      # 7 pt
    pages = []
    for name, short, tech, w, h in jx.captions:
        im = Image.open(jx.out / "figures" / f"{name}.png").convert("RGB")
        page = Image.new("RGB", (2480, 3508), "white")
        page.paste(im, ((2480 - im.width) // 2, 177))
        dr = ImageDraw.Draw(page)
        y = 177 + im.height + 70
        words, line, lines_ = (f"{name.replace('R40_', '').replace('_', ' ')}. " + short).split(), "", []
        for wd in words:
            t = (line + " " + wd).strip()
            if dr.textlength(t, font=font) > 2480 - 2 * 177:
                lines_.append(line)
                line = wd
            else:
                line = t
        lines_.append(line)
        for ln in lines_:
            dr.text((177, y), ln, fill="black", font=font)
            y += 50
        if y > 3508 - 177:
            K.exc("WARN", "A4 proof", f"{name}: figure + caption do not fit one A4 page at 100 %", f"{y} px of 3331")
        dr.text((177, 3508 - 120), f"A4 proof at 100 %: figure width {w * 25.4:.0f} mm, 300 dpi; smallest text in the figure >= 7 pt. Page = 210 x 297 mm.", fill="0.4", font=fonts)
        pages.append(page)
    p = jx.out / "A4_proof_pages_100pct.pdf"
    pages[0].save(p, "PDF", resolution=300.0, save_all=True, append_images=pages[1:], quality=92)
    jx.man.add(p, "A4 proof (raster, one figure + caption per page, 100 % scale)", "generated from the PNG figures", licence=K.LICENCE["own"])


def write_docs(jx, commit, run_id, summ):
    sc = jx.out / "scripts"
    (sc / "src").mkdir(parents=True, exist_ok=True)
    for f in ("__init__.py", "common.py", "cartography.py", "carto_lib.py", "carto.mplstyle", "carto_journal.mplstyle", "carto_journal_lib.py", "cartography_journal.py", "icesat2.py", "sources.py"):
        shutil.copy2(CODE_ROOT / "src" / f, sc / "src" / f)
    for f in ("requirements.txt", "requirements-carto.txt"):
        if (CODE_ROOT / f).exists():
            shutil.copy2(CODE_ROOT / f, sc / f)
    (sc / "rebuild_journal.sh").write_text("#!/usr/bin/env bash\n# Rebuild the journal figures from the first-edition package (offline if inputs/rasters/overview_kz is present).\nset -euo pipefail\n"
                                           "cd \"$(dirname \"$0\")\"\npython -m pip install -r requirements.txt -r requirements-carto.txt\n"
                                           "python -m src.cartography_journal build --package ../R40_CARTOGRAPHY_SOURCE_PACKAGE --out ../journal_rebuild\n", encoding="utf-8")
    for p in sc.rglob("*"):
        if p.is_file():
            jx.man.add(p, "script", "repository code at generation commit", licence="repository code licence (see repository)")
    for n in ("overview_kz",):
        for sub in ("rasters", "provenance"):
            pass
    mins = [r["min_font_pt"] for r in summ if r["min_font_pt"] == r["min_font_pt"]]
    ok = sum(1 for r in summ if r["min_font_ok_ge_7pt"] == "YES")
    readme = f"""# R40 journal figures and editable cartographic sources

Generated {C.now()} | code commit {commit} | workflow run {run_id}
Based on the first package R40_CARTOGRAPHY_SOURCE_PACKAGE (workflow run 38078170104, artifact 11679378949). Scientific content is unchanged.

## What changed (presentation only)
* Figure width 180 mm (full-width journal figure); every text object >= 7 pt: smallest text over all figures = {min(mins) if mins else 'n/a'} pt ({ok} of {len(summ)} figures pass; tables/a4_readability_audit.csv, tables/font_audit_all_text.csv).
* Captions are NOT inside the images any more: captions_journal.md has a short caption and technical notes per figure.
* One light legend per figure; polygon definitions, windows and CRS are in the captions. Panel titles carry the UTM zone; grid convergence and scale-bar lengths are in tables/map_furniture_parameters.csv.
* Relief: Copernicus GLO-30 DSM, bicubic-resampled (2x overview, 3x windows) FOR DISPLAY ONLY, multi-directional hillshade (azimuth {', '.join(f'{a:g}' for a in J.HS_AZ)} deg, altitude {J.HS_ALT:g} deg), hypsometric tint on the overview. Analysis values stay on the packaged 30 m grid.
* One new real input: Copernicus GLO-30 for the whole 76.85-77.20E, 43.05-43.25N window (inputs_extra/overview_kz; same product and pipeline as the study windows) so the overview has no grey gaps.
* Class colours (Okabe-Ito), class definitions, outlines, numbers: unchanged. tables/consistency_vs_source_package.csv compares the re-derived tables with the first package.

## Folders
* figures/ - R40_Fig_A ... E as PNG (300 dpi), PDF (TrueType text), SVG (text kept as text, relief embedded). A4_proof_pages_100pct.pdf - each figure + caption on an A4 page at 100 %.
* basemaps/ - georeferenced relief rasters (grey hillshade per site, colour RGBA overview) for re-styling in QGIS/Illustrator.
* tables/ - consistency checks, A4 audit, furniture parameters, shares as drawn.
* inputs_extra/ - the new overview DEM and its provenance. scripts/ - code; manifest_journal.csv - every file with source, CRS, licence, SHA-256.

## Editing
* SVG: open in Inkscape/Illustrator; install DejaVu Sans (or replace the font consistently). Text is live text; relief is an embedded image; outlines/graticule/scale bar are paths.
* Georeferenced re-styling: load basemaps/*.tif and derived/vector/*.gpkg (package part with the first edition's vector layers) in QGIS; the decision rasters are in the first package (inputs/rasters/*/decision_combined_t*_risk2.tif).

## Licences
Copernicus GLO-30 ("Contains modified Copernicus data"), NASADEM (public domain), OpenStreetMap contributors (ODbL), Natural Earth (public domain), swissALTI3D (swisstopo OGD), USGS 3DEP (public domain), NASA ICESat-2 ATL08 v007. Not included: ALOS AW3D30, FABDEM (licence), KazEOSat, tokens, private location details.
"""
    (jx.out / "README_JOURNAL.md").write_text(readme, encoding="utf-8")
    jx.man.add(jx.out / "README_JOURNAL.md", "readme", "generated", licence=K.LICENCE["own"])


def write_exceptions(jx):
    rows = K.EXC
    C.write_csv(jx.out / "journal_exceptions_report.csv", rows, ["severity", "area", "message", "detail"])
    lines = ["# Exceptions report (journal edition)", "", f"Generated {C.now()}. ERROR = product missing/failed or discrepancy; WARN = limitation; INFO = note.", ""]
    for sev in ("ERROR", "WARN", "INFO"):
        rr = [e for e in rows if e["severity"] == sev]
        if rr:
            lines += [f"## {sev} ({len(rr)})", ""] + [f"- **{e['area']}** - {e['message']}" + (f" `{e['detail']}`" if e["detail"] else "") for e in rr] + [""]
    (jx.out / "journal_exceptions_report.md").write_text("\n".join(lines), encoding="utf-8")
    for n in ("journal_exceptions_report.md", "journal_exceptions_report.csv"):
        jx.man.add(jx.out / n, "exceptions report", "generated", licence=K.LICENCE["own"])


# ======================================================================================================== zip parts
def _csize(p):
    c = zlib.compressobj(6)
    n = 0
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            n += len(c.compress(b))
    return n + len(c.flush())


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def pack_parts(files, out_dir, prefix, extra_first=None):
    """files: list of (arcname, Path). Greedy packing in the given order into zips <= 20 MB each. Returns list of paths."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    items = [(a, Path(p), _csize(p)) for a, p in files]
    parts, cur, size = [], [], 0
    for it in items:
        if cur and size + it[2] > LIM_SOFT - 60_000:
            parts.append(cur)
            cur, size = [], 0
        cur.append(it)
        size += it[2]
    if cur:
        parts.append(cur)
    n = len(parts)
    paths, i = [], 0
    while i < len(parts):
        n = len(parts)
        p = out_dir / f"{prefix}_part{i + 1:02d}_of_{n:02d}.zip"
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            lines = ["path,bytes,sha256"]
            for a, src, cs in parts[i]:
                z.write(src, a)
                lines.append(f"{a},{src.stat().st_size},{_sha(src)}")
            z.writestr(f"PART_CONTENTS_{i + 1:02d}_of_{n:02d}.csv", "\n".join(lines) + "\n")
            z.writestr(f"README_PARTS.txt", f"{prefix}: part {i + 1} of {n}. Parts are independent zips (no split archive); unzip all into one folder. Each part lists its files with SHA-256 in PART_CONTENTS_*.csv.\n")
            if i == 0 and extra_first:
                for a, src in extra_first:
                    z.write(src, a)
        if p.stat().st_size > LIM_HARD and len(parts[i]) > 1:
            moved = parts[i].pop()
            if i + 1 < len(parts):
                parts[i + 1].insert(0, moved)
            else:
                parts.append([moved])
            p.unlink()
            continue
        if p.stat().st_size > LIM_HARD:
            K.exc("ERROR", "zip parts", f"{p.name} is {p.stat().st_size} bytes (> 20 MB): a single file is larger than the limit", parts[i][0][0])
        paths.append(p)
        i += 1
    # part count may have changed after moves: rename to the final count
    n = len(paths)
    final = []
    for j, p in enumerate(paths):
        q = out_dir / f"{prefix}_part{j + 1:02d}_of_{n:02d}.zip"
        if q != p:
            if q.exists():
                q.unlink()
            p.rename(q)
        final.append(q)
    return final


def collect_files(jx, pkg):
    pkg, out = Path(pkg), jx.out
    fig_files = []
    for p in sorted((out / "figures").glob("*")):
        fig_files.append((f"R40_JOURNAL_FIGURES/figures/{p.name}", p))
    for n in ("captions_journal.md", "A4_proof_pages_100pct.pdf", "README_JOURNAL.md", "journal_exceptions_report.md", "journal_exceptions_report.csv", "manifest_journal.csv"):
        if (out / n).exists():
            fig_files.append((f"R40_JOURNAL_FIGURES/{n}", out / n))
    for p in sorted((out / "tables").glob("*.csv")):
        fig_files.append((f"R40_JOURNAL_FIGURES/tables/{p.name}", p))
    src_files = []
    for top in ("inputs", "derived", "tables", "scripts"):
        for p in sorted((pkg / top).rglob("*")):
            if p.is_file():
                src_files.append((f"R40_SOURCE_GEODATA/original_package/{p.relative_to(pkg).as_posix()}", p))
    for n in ("manifest.csv", "README.md", "exceptions_report.md", "exceptions_report.csv"):
        if (pkg / n).exists():
            src_files.append((f"R40_SOURCE_GEODATA/original_package/{n}", pkg / n))
    for top in ("basemaps", "tables", "scripts"):
        for p in sorted((out / top).rglob("*")):
            if p.is_file():
                src_files.append((f"R40_SOURCE_GEODATA/journal_edition/{p.relative_to(out).as_posix()}", p))
    for n in ("manifest_journal.csv", "README_JOURNAL.md", "captions_journal.md", "journal_exceptions_report.md", "journal_exceptions_report.csv"):
        if (out / n).exists():
            src_files.append((f"R40_SOURCE_GEODATA/journal_edition/{n}", out / n))
    return fig_files, src_files


# ======================================================================================================== driver
def build(pkg, out, scratch=None, parts=None, only=None):
    pkg, out = Path(pkg), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    scratch = Path(scratch or (out.parent / "_scratch_prepare"))
    commit = K.git_head(CODE_ROOT.parent.parent)
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    ctx, pts = prepare(pkg, scratch)
    jx = JX(ctx, out)
    load_overview(jx)
    (out / "tables").mkdir(exist_ok=True)
    consistency(jx, pkg, scratch)
    steps = [("A", lambda: fig_A(jx)), ("A_supp", lambda: fig_A_supp(jx)), ("B15", lambda: fig_B(jx, 15)), ("B7.5", lambda: fig_B(jx, 7.5)), ("B25", lambda: fig_B(jx, 25)),
             ("C", lambda: fig_C(jx)), ("D", lambda: fig_D(jx)), ("E", lambda: fig_E(jx, pts))]
    for name, fn in steps:
        if only and name not in only:
            continue
        try:
            fn()
            C.log("journal", f"Figure {name}", "OK", "")
        except Exception as e:  # noqa: BLE001
            K.exc_tb(f"Figure {name}", "step failed", e)
    try:
        write_basemaps(jx)
    except Exception as e:  # noqa: BLE001
        K.exc_tb("basemaps", "georeferenced relief rasters failed", e)
    summ = write_tables(jx)
    write_captions(jx)
    try:
        a4_proofs(jx)
    except Exception as e:  # noqa: BLE001
        K.exc_tb("A4 proof", "proof pages failed", e)
    # extra inputs (new overview DEM) travel with the journal edition
    for rel in (f"rasters/{OVERVIEW_KEY}/cop-dem-glo-30_elevation_m.tif", f"provenance/{OVERVIEW_KEY}_sources_provenance.json", f"provenance/{OVERVIEW_KEY}_window.json"):
        s = pkg / "inputs" / rel
        if s.exists():
            dst = out / "inputs_extra" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, dst)
            jx.man.add(dst, "input (overview DEM / provenance)", "Microsoft Planetary Computer STAC collection cop-dem-glo-30 (see provenance json)", datum="EGM2008 orthometric",
                       dates=K.prov_of(ctx, OVERVIEW_KEY, "cop-dem-glo-30")[1] if "provenance" not in rel else "", licence=K.DEM_META["cop-dem-glo-30"]["licence"])
    write_docs(jx, commit, run_id, summ)
    write_exceptions(jx)
    K_rows = jx.man.finalize(commit, run_id)
    (out / "manifest.csv").replace(out / "manifest_journal.csv")
    if parts:
        fig_files, src_files = collect_files(jx, pkg)
        fz = pack_parts(fig_files, Path(parts), "R40_JOURNAL_FIGURES")
        sz = pack_parts(src_files, Path(parts), "R40_SOURCE_GEODATA")
        C.write_csv(Path(parts) / "PARTS_INDEX.csv", [dict(file=p.name, bytes=p.stat().st_size, sha256=_sha(p)) for p in fz + sz])
        C.log("journal", "zip parts", "DONE", f"{len(fz)} figure parts, {len(sz)} geodata parts")
    C.log("journal", "build", "DONE", f"{len(jx.captions)} figures; {len(K.EXC)} exceptions")
    return jx


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("acquire")
    a.add_argument("--package", required=True)
    for nm in ("build", "all"):
        b = sub.add_parser(nm)
        b.add_argument("--package", required=True)
        b.add_argument("--out", required=True)
        b.add_argument("--parts")
        b.add_argument("--scratch")
        b.add_argument("--only", nargs="*")
    args = ap.parse_args()
    if args.cmd in ("acquire", "all"):
        acquire_overview(args.package)
    if args.cmd in ("build", "all"):
        build(args.package, args.out, scratch=args.scratch, parts=args.parts, only=args.only)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
