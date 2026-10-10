"""Pure helpers for R40 cartography (numpy only at import time; matplotlib/pyproj/shapely are imported lazily).

Everything here works on true coordinate transforms: maps are drawn in the local metric UTM CRS, so scale bars are
exact lengths in that projection; graticules come from pyproj; the north arrow is rotated by the meridian
convergence computed for the map centre. No generative image tools are involved anywhere.
"""
from __future__ import annotations
import math
import textwrap
import numpy as np

# Okabe-Ito colour-blind-safe palette
COL_BELOW = "#0072B2"
COL_ABOVE = "#D55E00"
COL_ABSTAIN = "#F0E442"
COL_NODATA = "#BFBFBF"
DEC_NAMES = {0: "BELOW", 1: "ABOVE", 2: "ABSTAIN"}
DEC_COLORS = {0: COL_BELOW, 1: COL_ABOVE, 2: COL_ABSTAIN}
NODATA_DEC = 255


# ----------------------------------------------------------------------------------------------- numerics
def hillshade(z, res, az_deg=315.0, alt_deg=45.0):
    """Analytical hillshade (Esri formulation) on a north-up grid; NaN where any neighbour is NaN."""
    z = np.asarray(z, dtype="float64")
    gy, gx = np.gradient(z, res)          # gy: d/d(row, southwards); gx: d/d(col, eastwards)
    dzdx, dzdy = gx, -gy                  # dzdy northwards
    slope = np.arctan(np.hypot(dzdx, dzdy))
    aspect = np.arctan2(-dzdy, -dzdx)   # math angle of the DOWNSLOPE direction
    zen = np.radians(90.0 - alt_deg)
    azm = np.radians((360.0 - az_deg + 90.0) % 360.0)
    hs = np.cos(zen) * np.cos(slope) + np.sin(zen) * np.sin(slope) * np.cos(azm - aspect)
    hs = np.clip(hs, 0.0, 1.0)
    hs[~np.isfinite(z)] = np.nan
    return hs


def meridian_convergence_deg(lon, lat, lon0):
    """Grid convergence of a transverse-Mercator/UTM grid (spherical approximation, error << 0.01 deg here)."""
    d = math.radians(lon - lon0)
    return math.degrees(math.atan(math.tan(d) * math.sin(math.radians(lat))))


def utm_central_meridian(epsg):
    zone = int(str(epsg)[-2:])
    return -183.0 + 6.0 * zone


def nice_length(width_m, fraction=0.2):
    """Largest 1-2-5 x 10^n length not exceeding fraction*width."""
    target = max(width_m * fraction, 1e-9)
    e = 10 ** math.floor(math.log10(target))
    best = e
    for m in (1, 2, 5, 10):
        if m * e <= target:
            best = m * e
    return best


def length_label(m):
    return f"{m / 1000:g} km" if m >= 1000 else f"{m:g} m"


def class_shares(dec, mask=None):
    """Counts and percentages of codes 0/1/2 among valid (!=255) pixels, optionally inside a boolean mask."""
    dec = np.asarray(dec)
    valid = dec != NODATA_DEC
    if mask is not None:
        valid = valid & mask
    n = int(valid.sum())
    out = {"n_px": n}
    for code, name in DEC_NAMES.items():
        out[f"{name}_pct"] = float(100.0 * np.mean(dec[valid] == code)) if n else float("nan")
    return out


def compare_shares(mine, ref, tol_pp=0.05):
    """Compare recomputed shares with a table row. Returns (status, max_abs_diff_pp, n_diff)."""
    d = [abs(mine[f"{k}_pct"] - float(ref[f"{k}_pct"])) for k in DEC_NAMES.values()]
    n_diff = abs(int(mine["n_px"]) - int(float(ref["n_px"])))
    worst = max(d) if d else float("nan")
    ok = (worst <= tol_pp) and n_diff == 0
    return ("OK" if ok else "FLAG_DISCREPANCY"), worst, n_diff


def slope_diff_stats(a, b):
    """Statistics of a-b on the common valid mask."""
    m = np.isfinite(a) & np.isfinite(b)
    n = int(m.sum())
    if n == 0:
        return {"common_px": 0}
    d = (a[m] - b[m]).astype("float64")
    return {"common_px": n, "mean_diff_deg": float(d.mean()), "sd_diff_deg": float(d.std()), "mae_deg": float(np.abs(d).mean()),
            "rmse_deg": float(np.sqrt((d ** 2).mean())), "p95_abs_deg": float(np.percentile(np.abs(d), 95))}


def class_disagreement(a, b, t):
    m = np.isfinite(a) & np.isfinite(b)
    n = int(m.sum())
    if n == 0:
        return float("nan"), 0
    return float(100.0 * np.mean((a[m] >= t) != (b[m] >= t))), n


def sample_bilinear(arr, x0, y1, res, xs, ys):
    """Bilinear sampling at projected coordinates (cell centres convention); NaN outside / next to NaN."""
    from scipy import ndimage as ndi
    col = (np.asarray(xs) - x0) / res - 0.5
    row = (y1 - np.asarray(ys)) / res - 0.5
    H, W = arr.shape
    out = np.full(col.shape, np.nan)
    inside = (col >= 0) & (row >= 0) & (col <= W - 1) & (row <= H - 1)
    if inside.any():
        out[inside] = ndi.map_coordinates(arr, [row[inside], col[inside]], order=1, mode="nearest", cval=np.nan)
    return out


# ----------------------------------------------------------------------------------------------- drawing
def apply_style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from pathlib import Path
    plt.style.use(str(Path(__file__).with_name("carto.mplstyle")))
    return plt


def to_rgba_list(color, alpha=1.0):
    from matplotlib.colors import to_rgba
    return to_rgba(color, alpha)


def decision_rgba(dec, alpha=0.78):
    rgba = np.zeros(dec.shape + (4,), dtype="float32")
    for code, col in DEC_COLORS.items():
        rgba[dec == code] = to_rgba_list(col, alpha)
    rgba[dec == NODATA_DEC] = to_rgba_list(COL_NODATA, 1.0)
    return rgba


def gray_hillshade_cmap():
    import matplotlib.pyplot as plt
    cm = plt.get_cmap("gray").copy()
    cm.set_bad(COL_NODATA)
    return cm


def style_map_axes(ax, extent):
    xmin, xmax, ymin, ymax = extent
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_linewidth(0.7)


def scale_bar(ax, extent, epsg_label, length_m=None):
    from matplotlib.patches import Rectangle
    xmin, xmax, ymin, ymax = extent
    W, H = xmax - xmin, ymax - ymin
    L = length_m or nice_length(W)
    x0, y0 = xmin + 0.04 * W, ymin + 0.045 * H
    h = 0.012 * H
    ax.add_patch(Rectangle((x0 - 0.01 * W, y0 - 0.02 * H), L + 0.02 * W, 0.075 * H + h, fc="white", ec="none", alpha=0.85, zorder=8))
    for i, c in enumerate(("black", "white")):
        ax.add_patch(Rectangle((x0 + i * L / 2, y0), L / 2, h, fc=c, ec="black", lw=0.5, zorder=9))
    ax.text(x0, y0 + 1.6 * h, "0", fontsize=5.5, ha="center", va="bottom", zorder=9)
    ax.text(x0 + L, y0 + 1.6 * h, length_label(L), fontsize=5.5, ha="center", va="bottom", zorder=9)
    ax.text(x0 + L / 2, y0 - 0.6 * h, f"metric, {epsg_label}", fontsize=4.5, ha="center", va="top", zorder=9)
    return L


def north_arrow(ax, extent, gamma_deg):
    """Arrow pointing to TRUE north; grid north is vertical, so true north is rotated by -gamma."""
    xmin, xmax, ymin, ymax = extent
    W, H = xmax - xmin, ymax - ymin
    cx, cy = xmax - 0.07 * W, ymax - 0.16 * H
    ln = 0.10 * H
    ang = math.radians(-gamma_deg)
    dx, dy = ln * math.sin(ang), ln * math.cos(ang)
    ax.annotate("", xy=(cx + dx, cy + dy), xytext=(cx, cy), arrowprops=dict(arrowstyle="-|>", color="black", lw=1.0, mutation_scale=7), zorder=9)
    ax.text(cx + dx * 1.18, cy + dy * 1.18, "N", ha="center", va="bottom", fontsize=7, fontweight="bold", zorder=9,
            bbox=dict(fc="white", ec="none", alpha=0.7, pad=0.6))
    ax.text(cx, cy - 0.02 * H, f"true N; grid conv. {gamma_deg:+.2f}°", fontsize=4.3, ha="center", va="top", zorder=9,
            bbox=dict(fc="white", ec="none", alpha=0.7, pad=0.4))


def _nice_deg_step(span_deg):
    for s in (0.005, 0.01, 0.02, 0.025, 0.05, 0.1, 0.2, 0.25, 0.5, 1, 2, 5, 10, 15, 30):
        if span_deg / s <= 4.5:
            return s
    return 30


def _trim(v):
    return f"{abs(v):.3f}".rstrip("0").rstrip(".")


def fmt_lon(v):
    return f"{_trim(v)}°{'E' if v >= 0 else 'W'}"


def fmt_lat(v):
    return f"{_trim(v)}°{'N' if v >= 0 else 'S'}"


def graticule_utm(ax, epsg, extent):
    """Meridians/parallels from pyproj, clipped to the map frame, labelled where they leave the frame."""
    from pyproj import Transformer
    from shapely.geometry import LineString, box
    xmin, xmax, ymin, ymax = extent
    to_ll = Transformer.from_crs(epsg, 4326, always_xy=True)
    to_xy = Transformer.from_crs(4326, epsg, always_xy=True)
    px = np.linspace(xmin, xmax, 25)
    py = np.linspace(ymin, ymax, 25)
    perim = [(x, ymin) for x in px] + [(x, ymax) for x in px] + [(xmin, y) for y in py] + [(xmax, y) for y in py]
    lons, lats = zip(*[to_ll.transform(x, y) for x, y in perim])
    lo0, lo1, la0, la1 = min(lons), max(lons), min(lats), max(lats)
    step_lon, step_lat = _nice_deg_step(lo1 - lo0), _nice_deg_step(la1 - la0)
    frame = box(xmin, ymin, xmax, ymax)
    bottom = LineString([(xmin, ymin), (xmax, ymin)])
    left = LineString([(xmin, ymin), (xmin, ymax)])
    for lon in np.arange(math.ceil(lo0 / step_lon) * step_lon, lo1 + 1e-9, step_lon):
        pts = [to_xy.transform(lon, la) for la in np.linspace(la0 - 0.02, la1 + 0.02, 60)]
        ln = LineString(pts).intersection(frame)
        if ln.is_empty:
            continue
        for part in (ln.geoms if hasattr(ln, "geoms") else [ln]):
            if part.geom_type == "LineString":
                ax.plot(*part.xy, color="0.25", lw=0.35, ls=(0, (1, 2)), zorder=7)
        hit = LineString(pts).intersection(bottom)
        if not hit.is_empty and hit.geom_type == "Point":
            ax.text(hit.x, ymin, fmt_lon(lon), fontsize=4.8, ha="center", va="top", rotation=0, clip_on=False, color="0.15")
    for lat in np.arange(math.ceil(la0 / step_lat) * step_lat, la1 + 1e-9, step_lat):
        pts = [to_xy.transform(lo, lat) for lo in np.linspace(lo0 - 0.02, lo1 + 0.02, 60)]
        ln = LineString(pts).intersection(frame)
        if ln.is_empty:
            continue
        for part in (ln.geoms if hasattr(ln, "geoms") else [ln]):
            if part.geom_type == "LineString":
                ax.plot(*part.xy, color="0.25", lw=0.35, ls=(0, (1, 2)), zorder=7)
        hit = LineString(pts).intersection(left)
        if not hit.is_empty and hit.geom_type == "Point":
            ax.text(xmin, hit.y, fmt_lat(lat), fontsize=4.8, ha="right", va="center", rotation=90, clip_on=False, color="0.15")


def plot_geom(ax, g, **kw):
    """Draw polygon outlines (exterior and holes) or lines/points of a shapely geometry in axes coordinates."""
    if g is None or g.is_empty:
        return
    t = g.geom_type
    if t in ("Polygon",):
        ax.plot(*g.exterior.xy, **kw)
        for r in g.interiors:
            ax.plot(*r.xy, **kw)
    elif t.startswith("Multi") or t == "GeometryCollection":
        for p in g.geoms:
            plot_geom(ax, p, **kw)
    elif t in ("LineString", "LinearRing"):
        ax.plot(*g.xy, **kw)
    elif t == "Point":
        ax.plot([g.x], [g.y], **{k: v for k, v in kw.items() if k not in ("ls", "linestyle")}, marker=kw.get("marker", "o"))


def wrap_caption(text, width=150):
    return "\n".join(textwrap.fill(p, width=width) for p in text.split("\n"))
