"""Journal-style cartographic helpers for R40 (A4 print: figure width 180 mm, every text >= 7 pt).

Pure display logic. Nothing here changes a data value: relief is rendered from the packaged DEM rasters
(bicubic resampling and hillshade are DISPLAY operations and are declared in every caption); classes, polygons, CRS,
scale bars (exact metres in the local UTM CRS) and graticules (pyproj) are unchanged. No generative imagery.
numpy/scipy are needed at import; matplotlib, pyproj and shapely are imported lazily.
"""
from __future__ import annotations
import math
import numpy as np
from . import carto_lib as L

FIG_W = 7.09                      # 180 mm, the usual full-width figure of Springer/Elsevier journals
FS_TITLE, FS_BASE, FS_SMALL = 9.0, 8.0, 7.5
MIN_FS = 7.0
HS_AZ = (225.0, 270.0, 315.0, 360.0)
HS_W = (0.15, 0.25, 0.35, 0.25)
HS_ALT = 40.0
HS_FLAT = math.sin(math.radians(HS_ALT))
# hypsometric tint stops (metres above sea level) -> colour; muted, print-safe, monotonic in lightness-ish steps
HYPSO = [(500, "#C5D8A4"), (800, "#D8E3B0"), (1200, "#E7E3AB"), (1700, "#E4D194"), (2300, "#D3B07C"),
         (2900, "#BC9073"), (3400, "#B5A5A1"), (3900, "#E2DEDC"), (4400, "#FFFFFF")]


# ----------------------------------------------------------------------------------------------- relief
def fill_nearest(z):
    from scipy import ndimage
    z = np.asarray(z, dtype="float64")
    bad = ~np.isfinite(z)
    if not bad.any():
        return z, bad
    if bad.all():
        return np.zeros_like(z), bad
    idx = ndimage.distance_transform_edt(bad, return_distances=False, return_indices=True)
    return z[tuple(idx)], bad


def upsample_surface(z, k):
    """Bicubic upsampling by an integer factor k, pixel EDGES aligned (grid_mode), nodata mask kept (nearest)."""
    from scipy import ndimage
    zf, bad = fill_nearest(z)
    if k == 1:
        return zf, bad
    zu = ndimage.zoom(zf, k, order=3, mode="nearest", grid_mode=True)
    bu = np.repeat(np.repeat(bad, k, axis=0), k, axis=1)
    return zu, bu


def hillshade_multi(z, res):
    """Multi-directional hillshade (azimuths 225/270/315/360 deg, altitude 40 deg, weights 0.15/0.25/0.35/0.25); flat ground = sin(alt)."""
    acc = np.zeros_like(z, dtype="float64")
    for az, w in zip(HS_AZ, HS_W):
        acc += w * L.hillshade(z, res, az_deg=az, alt_deg=HS_ALT)
    return acc


def tint(z):
    from matplotlib.colors import to_rgb
    zs = np.array([s[0] for s in HYPSO], dtype="float64")
    cols = np.array([to_rgb(s[1]) for s in HYPSO])
    return np.stack([np.interp(z, zs, cols[:, i]) for i in range(3)], axis=-1)


def relief(z, res, k=3, kind="gray"):
    """Return (rgb float32 [h*k, w*k, 3], info). kind 'gray' = light grey hillshade (decision/diff maps), 'color' = hypsometric tint x hillshade."""
    from matplotlib.colors import to_rgb
    zu, bad = upsample_surface(z, k)
    hs = hillshade_multi(zu, res / k)
    if kind == "gray":
        v = np.clip(0.80 + 0.95 * (hs - HS_FLAT), 0.25, 1.0)
        rgb = np.dstack([v, v, v])
    else:
        sh = np.clip(1.0 + 1.35 * (hs - HS_FLAT), 0.45, 1.18)
        rgb = np.clip(tint(zu) * sh[..., None], 0.0, 1.0)
    rgb[bad] = to_rgb(L.COL_NODATA)
    return rgb.astype("float32"), dict(k=k, res_display_m=res / k, nodata_px=int(bad.sum()), bad=bad)


def to_uint8_rgba(rgb, nodata_alpha_mask=None):
    a = np.full(rgb.shape[:2], 255, "uint8")
    if nodata_alpha_mask is not None:
        a[nodata_alpha_mask] = 0
    return np.dstack([np.round(rgb * 255).astype("uint8"), a])


def hypso_colorbar(fig, rect, vmin, vmax, step=500, label="", fs=FS_BASE, vertical=False):
    cax = fig.add_axes(rect)
    z = np.linspace(vmin, vmax, 512)
    ticks = np.arange(math.ceil(vmin / step) * step, vmax + 1e-6, step)
    if vertical:
        cax.imshow(tint(z)[::-1, None, :], extent=(0, 1, vmin, vmax), aspect="auto", interpolation="bilinear")
        cax.set_xticks([])
        cax.yaxis.tick_right()
        cax.yaxis.set_label_position("right")
        cax.set_yticks(ticks)
        cax.set_ylabel(label, fontsize=fs)
    else:
        cax.imshow(tint(z)[None, :, :], extent=(vmin, vmax, 0, 1), aspect="auto", interpolation="bilinear")
        cax.set_yticks([])
        cax.set_xticks(ticks)
        cax.set_xlabel(label, fontsize=fs)
    cax.tick_params(labelsize=FS_SMALL, length=3)
    for sp in cax.spines.values():
        sp.set_linewidth(0.6)
    return cax


# ----------------------------------------------------------------------------------------------- text helpers
def halo(artist, lw=2.4, fg="white", alpha=0.92):
    import matplotlib.patheffects as pe
    artist.set_path_effects([pe.withStroke(linewidth=lw, foreground=fg, alpha=alpha)])
    return artist


def panel_title(ax, tag, name, right=None, stats=None, fs=FS_TITLE):
    pad = 13 if stats else 4
    ax.set_title(f"({tag}) {name}", loc="left", fontsize=fs, fontweight="bold", pad=pad)
    if right:
        ax.set_title(right, loc="right", fontsize=FS_SMALL, color="0.35", pad=pad, fontweight="normal")
    if stats:
        ax.annotate(stats, xy=(0, 1), xycoords="axes fraction", xytext=(0, 2.5), textcoords="offset points", ha="left", va="bottom", fontsize=FS_SMALL, color="0.1",
                    annotation_clip=False)


# ----------------------------------------------------------------------------------------------- map furniture
def scale_bar(ax, extent, length_m=None, fs=FS_BASE, frac=0.25):
    from matplotlib.patches import Rectangle
    xmin, xmax, ymin, ymax = extent
    W, H = xmax - xmin, ymax - ymin
    Lm = length_m or L.nice_length(W, frac)
    x0, y0 = xmin + 0.045 * W, ymin + 0.05 * H
    h = 0.016 * H
    ax.add_patch(Rectangle((x0 - 0.012 * W, y0 - 0.012 * H), Lm + 0.06 * W + 0.02 * W, h + 0.075 * H, fc="white", ec="none", alpha=0.55, zorder=8))
    for i, c in enumerate(("black", "white")):
        ax.add_patch(Rectangle((x0 + i * Lm / 2, y0), Lm / 2, h, fc=c, ec="black", lw=0.7, zorder=9))
    t0 = ax.text(x0, y0 + 1.7 * h, "0", fontsize=fs, ha="center", va="bottom", zorder=10)
    t1 = ax.text(x0 + Lm, y0 + 1.7 * h, L.length_label(Lm), fontsize=fs, ha="center", va="bottom", zorder=10)
    return Lm


def north_arrow(ax, extent, gamma_deg, fs=FS_TITLE):
    """Arrow to TRUE north (grid north is vertical, so true north is rotated by -gamma). Only 'N' and the arrow; gamma goes to the caption table."""
    xmin, xmax, ymin, ymax = extent
    W, H = xmax - xmin, ymax - ymin
    cx, cy = xmax - 0.07 * W, ymax - 0.17 * H
    ln = 0.105 * H
    ang = math.radians(-gamma_deg)
    dx, dy = ln * math.sin(ang), ln * math.cos(ang)
    for lw, col, z in ((3.2, "white", 9), (1.3, "black", 10)):
        ax.annotate("", xy=(cx + dx, cy + dy), xytext=(cx, cy), arrowprops=dict(arrowstyle="-|>", color=col, lw=lw, mutation_scale=9 if col == "black" else 11,
                                                                                   shrinkA=0, shrinkB=0), zorder=z)
    halo(ax.text(cx + dx * 1.18, cy + dy * 1.18, "N", ha="center", va="bottom", fontsize=fs, fontweight="bold", zorder=11), lw=2.6)


def graticule(ax, epsg, extent, n_max=3.0, fs=FS_SMALL, lon_labels=True, lat_labels=True):
    """Meridians/parallels from pyproj (two-tone hairlines), labelled at the frame with constant point offsets."""
    from pyproj import Transformer
    from shapely.geometry import LineString, box
    xmin, xmax, ymin, ymax = extent
    to_ll = Transformer.from_crs(epsg, 4326, always_xy=True)
    to_xy = Transformer.from_crs(4326, epsg, always_xy=True)
    px, py = np.linspace(xmin, xmax, 25), np.linspace(ymin, ymax, 25)
    perim = [(x, ymin) for x in px] + [(x, ymax) for x in px] + [(xmin, y) for y in py] + [(xmax, y) for y in py]
    lons, lats = zip(*[to_ll.transform(x, y) for x, y in perim])
    lo0, lo1, la0, la1 = min(lons), max(lons), min(lats), max(lats)
    step_lon, step_lat = L._nice_deg_step(lo1 - lo0, n_max), L._nice_deg_step(la1 - la0, n_max)
    frame = box(xmin, ymin, xmax, ymax)
    bottom, left = LineString([(xmin, ymin), (xmax, ymin)]), LineString([(xmin, ymin), (xmin, ymax)])

    def _draw(ln):
        for part in (ln.geoms if hasattr(ln, "geoms") else [ln]):
            if part.geom_type == "LineString":
                ax.plot(*part.xy, color="white", lw=0.9, alpha=0.55, zorder=6.5)
                ax.plot(*part.xy, color="0.15", lw=0.45, ls=(0, (2, 2)), alpha=0.8, zorder=7)

    for lon in np.arange(math.ceil(lo0 / step_lon) * step_lon, lo1 + 1e-9, step_lon):
        pts = [to_xy.transform(lon, la) for la in np.linspace(la0 - 0.02, la1 + 0.02, 60)]
        ln = LineString(pts).intersection(frame)
        if ln.is_empty:
            continue
        _draw(ln)
        hit = LineString(pts).intersection(bottom)
        if lon_labels and not hit.is_empty and hit.geom_type == "Point":
            ax.annotate(L.fmt_lon(lon), xy=(hit.x, ymin), xytext=(0, -2.5), textcoords="offset points", ha="center", va="top", fontsize=fs, color="0.1", annotation_clip=False)
    for lat in np.arange(math.ceil(la0 / step_lat) * step_lat, la1 + 1e-9, step_lat):
        pts = [to_xy.transform(lo, lat) for lo in np.linspace(lo0 - 0.02, lo1 + 0.02, 60)]
        ln = LineString(pts).intersection(frame)
        if ln.is_empty:
            continue
        _draw(ln)
        hit = LineString(pts).intersection(left)
        if lat_labels and not hit.is_empty and hit.geom_type == "Point":
            ax.annotate(L.fmt_lat(lat), xy=(xmin, hit.y), xytext=(-2.5, 0), textcoords="offset points", ha="right", va="center", rotation=90, fontsize=fs, color="0.1", annotation_clip=False)


def furniture(ax, epsg, extent, center_lonlat, lon_labels=True, lat_labels=True, n_max=3.0, bar_frac=0.25, rec=None):
    """Graticule + metric scale bar + north arrow. Appends the exact parameters to `rec` (list of dicts) for the furniture table."""
    graticule(ax, epsg, extent, n_max=n_max, lon_labels=lon_labels, lat_labels=lat_labels)
    Lm = scale_bar(ax, extent, frac=bar_frac)
    gamma = L.meridian_convergence_deg(center_lonlat[0], center_lonlat[1], L.utm_central_meridian(epsg))
    north_arrow(ax, extent, gamma)
    if rec is not None:
        rec.append(dict(epsg=epsg, scale_bar_m=Lm, grid_convergence_deg=round(gamma, 4), centre_lon=center_lonlat[0], centre_lat=center_lonlat[1],
                        extent_xmin=extent[0], extent_xmax=extent[1], extent_ymin=extent[2], extent_ymax=extent[3]))
    return Lm, gamma


def plot_outline(ax, g, color="black", lw=1.2, ls="-", zorder=6, halo_lw=2.4):
    """Polygon outline with a white under-stroke so it reads on any relief colour (grayscale-safe)."""
    if g is None:
        return
    L.plot_geom(ax, g, color="white", lw=lw + halo_lw, ls="-", zorder=zorder - 0.1, alpha=0.9)
    L.plot_geom(ax, g, color=color, lw=lw, ls=ls, zorder=zorder)


def style_axes(ax, extent):
    L.style_map_axes(ax, extent)
    for s in ax.spines.values():
        s.set_linewidth(0.8)


# ----------------------------------------------------------------------------------------------- page layout (inches)
class Page:
    """Figure with axes placed in absolute inches (x from the left, y from the TOP)."""

    def __init__(self, plt, w, h):
        self.fig = plt.figure(figsize=(w, h))
        self.w, self.h = w, h

    def axes(self, x, y_top, w, h, **kw):
        return self.fig.add_axes([x / self.w, 1.0 - (y_top + h) / self.h, w / self.w, h / self.h], **kw)

    def legend_row(self, handles, y_bottom=0.06, ncol=None, fs=FS_BASE):
        n = ncol or len(handles)
        return self.fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, y_bottom / self.h), ncol=n, fontsize=fs, frameon=False, handlelength=2.0,
                               columnspacing=1.6, handletextpad=0.6, borderaxespad=0.0)


def aspect(extent):
    return (extent[3] - extent[2]) / (extent[1] - extent[0])


def font_audit(fig, name):
    """All visible text objects with their size in points: the A4 readability audit."""
    import matplotlib.text as mt
    rows = []
    for t in fig.findobj(mt.Text):
        s = t.get_text().strip()
        if not s or not t.get_visible():
            continue
        rows.append(dict(figure=name, text=s.replace("\n", " ")[:50], fontsize_pt=round(float(t.get_fontsize()), 2)))
    return rows
