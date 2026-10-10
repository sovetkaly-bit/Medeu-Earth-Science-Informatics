"""Figures and markdown rendering for R40."""
from __future__ import annotations
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch
from shapely.geometry import mapping
from . import common as C

OKABE = {"random": "#999999", "distance": "#0072B2", "norm_margin": "#56B4E9", "dem_disagreement": "#E69F00",
         "local_variability": "#009E73", "scale_stability": "#CC79A7", "combined": "#D55E00"}
DEC_COLORS = ["#4C78A8", "#E45756", "#BDBDBD"]  # BELOW, ABOVE, ABSTAIN
DEC_LABELS = ["BELOW", "ABOVE", "ABSTAIN"]


def md_table(rows, cols=None, fmt=None, max_rows=60):
    if not rows:
        return "_нет данных_\n"
    cols = cols or list(rows[0].keys())
    fmt = fmt or {}

    def f(k, v):
        if v is None or (isinstance(v, float) and not np.isfinite(v)):
            return "—"
        if k in fmt:
            return fmt[k](v)
        if isinstance(v, float):
            return f"{v:.4g}"
        return str(v)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in rows[:max_rows]:
        out.append("| " + " | ".join(f(c, r.get(c)) for c in cols) + " |")
    if len(rows) > max_rows:
        out.append(f"| … ещё {len(rows) - max_rows} строк в CSV |" + " |" * (len(cols) - 1))
    return "\n".join(out) + "\n"


def _extent(grid):
    x0, y0, x1, y1 = grid.bounds()
    return (x0, x1, y0, y1)


def _outline(ax, geom_utm, color="k", lw=1.2, ls="-"):
    if geom_utm is None:
        return
    geoms = list(geom_utm.geoms) if geom_utm.geom_type.startswith("Multi") else [geom_utm]
    for g in geoms:
        if g.geom_type == "Polygon":
            x, y = g.exterior.xy
            ax.plot(x, y, color=color, lw=lw, ls=ls)


def site_figure(path, key, title, grid, slope, decisions, thresholds, territory_utm=None, footprint_utm=None, target=0.10):
    """Slope map + decision maps (BELOW/ABOVE/ABSTAIN) per threshold for one territory."""
    n = 1 + len(thresholds)
    fig, axes = plt.subplots(1, n, figsize=(4.6 * n, 4.8), constrained_layout=True)
    ext = _extent(grid)
    im = axes[0].imshow(slope, extent=ext, cmap="cividis", vmin=0, vmax=45)
    fig.colorbar(im, ax=axes[0], shrink=0.75, label="уклон, ° (Horn, 30 м)")
    axes[0].set_title(f"{title}\nуклон ({'контур территории' if territory_utm is not None else 'контур не найден' if footprint_utm is None else 'функц. контур OSM'})", fontsize=9)
    cm = ListedColormap(DEC_COLORS)
    norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5], cm.N)
    for ax, t in zip(axes[1:], thresholds):
        d = decisions[t].astype("float32")
        d[d == 255] = np.nan
        ax.imshow(d, extent=ext, cmap=cm, norm=norm, interpolation="nearest")
        share = {k: float(np.nanmean(d == i)) * 100 for i, k in enumerate(DEC_LABELS)}
        ax.set_title(f"порог {t}°; допуст. риск {int(target*100)}%\nBELOW {share['BELOW']:.0f}% · ABOVE {share['ABOVE']:.0f}% · ABSTAIN {share['ABSTAIN']:.0f}%", fontsize=9)
    for ax in axes:
        _outline(ax, territory_utm, "k", 1.4)
        _outline(ax, footprint_utm, "#7f3c8d", 1.0, "--")
        ax.set_xticks([]); ax.set_yticks([])
    axes[-1].legend(handles=[Patch(color=c, label=l) for c, l in zip(DEC_COLORS, DEC_LABELS)], loc="lower right", fontsize=8, framealpha=0.9)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def rc_figure(path, rc_rows, thresholds):
    fig, axes = plt.subplots(1, len(thresholds), figsize=(4.8 * len(thresholds), 4.2), constrained_layout=True, squeeze=False)
    for ax, t in zip(axes[0], thresholds):
        for m in OKABE:
            xs = [r for r in rc_rows if r["threshold_deg"] == t and r["method"] == m]
            if xs:
                ax.plot([r["coverage"] for r in xs], [r["risk"] for r in xs], color=OKABE[m], lw=1.8 if m in ("combined", "distance") else 1.1, label=m)
        ax.set_xlabel("покрытие (доля решений без ABSTAIN)"); ax.set_ylabel("selective risk (доля ошибок)")
        ax.set_title(f"risk–coverage, порог {t}° (LOSO, независимые территории)", fontsize=9)
        ax.grid(alpha=0.25)
    axes[0][-1].legend(fontsize=7)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def calib_figure(path, calib_rows, thresholds):
    fig, axes = plt.subplots(1, len(thresholds), figsize=(4.2 * len(thresholds), 4.0), constrained_layout=True, squeeze=False)
    for ax, t in zip(axes[0], thresholds):
        xs = [r for r in calib_rows if r["threshold_deg"] == t]
        ax.plot([0, 1], [0, 1], color="#999", lw=1)
        if xs:
            ax.plot([r["mean_p_err"] for r in xs], [r["observed_err"] for r in xs], "o-", color=OKABE["combined"])
            lim = max(max(r["mean_p_err"] for r in xs), max(r["observed_err"] for r in xs)) * 1.1
            ax.set_xlim(0, lim); ax.set_ylim(0, lim)
        ax.set_xlabel("предсказанная вероятность ошибки"); ax.set_ylabel("наблюдаемая доля ошибок")
        ax.set_title(f"калибровка, порог {t}°", fontsize=9)
        ax.grid(alpha=0.25)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def comparison_figure(path, shares_rows):
    """Stacked slope-class shares by site (primary DEM, context mask)."""
    rows = [r for r in shares_rows if r["mask"] == "context"]
    if not rows:
        return
    labels = [f"{r['site']}\n({r['group']})" for r in rows]
    parts = ["share_lt_7.5", "share_7.5_15", "share_15_25", "share_ge_25"]
    cols = ["#DCE9F5", "#9ECAE1", "#4292C6", "#08306B"]
    names = ["< 7,5°", "7,5–15°", "15–25°", "≥ 25°"]
    fig, ax = plt.subplots(figsize=(1.1 * len(rows) + 3, 4.6), constrained_layout=True)
    bottom = np.zeros(len(rows))
    for p, c, nme in zip(parts, cols, names):
        v = np.array([r[p] for r in rows])
        ax.bar(range(len(rows)), v, bottom=bottom, color=c, label=nme, edgecolor="white", lw=0.5)
        bottom += v
    ax.set_xticks(range(len(rows))); ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel("доля площади окна, %"); ax.legend(fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def vector_geojson(arr, grid, to_wgs, labels, nodata=255):
    """Dissolved polygons of a uint8 class raster in WGS84."""
    from rasterio.features import shapes
    from shapely.geometry import shape
    from shapely.ops import transform as shp_transform
    feats = []
    for geom, val in shapes(arr, mask=(arr != nodata), transform=grid.transform, connectivity=8):
        g = shp_transform(to_wgs, shape(geom))
        feats.append({"type": "Feature", "geometry": mapping(g), "properties": {"class": labels.get(int(val), str(int(val))), "value": int(val)}})
    return {"type": "FeatureCollection", "features": feats}
