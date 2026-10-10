"""Pure-numpy terrain primitives for R40 (no raster I/O, testable offline).

All arrays are 2-D float arrays with NaN as NoData. Every operator that needs a
neighbourhood returns NaN unless the *whole* neighbourhood is valid, so that all
slope algorithms share one common valid mask.
"""
from __future__ import annotations
import warnings
import numpy as np
from scipy import ndimage as ndi

warnings.filterwarnings("ignore", category=RuntimeWarning)

ALGORITHMS = ("horn", "zt", "evans")


def _neigh(z):
    zp = np.pad(z, 1, constant_values=np.nan)
    return (zp[:-2, :-2], zp[:-2, 1:-1], zp[:-2, 2:],
            zp[1:-1, :-2], zp[1:-1, 1:-1], zp[1:-1, 2:],
            zp[2:, :-2], zp[2:, 1:-1], zp[2:, 2:])


def slope_deg(z, res, method="horn"):
    """Slope in degrees. res = cell size in metres (square cells).

    horn  : Horn (1981) 3x3 weighted finite difference (default; GDAL/ArcGIS).
    zt    : Zevenbergen & Thorne (1987) central difference on 4 neighbours.
    evans : Evans (1980) / Burrough equal-weight 3x3 finite difference.
    """
    a, b, c, d, e, f, g, h, i = _neigh(np.asarray(z, dtype="float64"))
    if method == "horn":
        dzdx = ((c + 2 * f + i) - (a + 2 * d + g)) / (8.0 * res)
        dzdy = ((g + 2 * h + i) - (a + 2 * b + c)) / (8.0 * res)
    elif method == "zt":
        dzdx = (f - d) / (2.0 * res)
        dzdy = (h - b) / (2.0 * res)
    elif method == "evans":
        dzdx = ((c + f + i) - (a + d + g)) / (6.0 * res)
        dzdy = ((g + h + i) - (a + b + c)) / (6.0 * res)
    else:
        raise ValueError(method)
    s = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    # common valid mask for every algorithm: whole 3x3 window finite
    ok = np.isfinite(a) & np.isfinite(b) & np.isfinite(c) & np.isfinite(d) & np.isfinite(e) \
        & np.isfinite(f) & np.isfinite(g) & np.isfinite(h) & np.isfinite(i)
    return np.where(ok, s, np.nan).astype("float32")


def tri_riley(z):
    """Terrain Ruggedness Index (Riley et al. 1999), metres."""
    a, b, c, d, e, f, g, h, i = _neigh(np.asarray(z, dtype="float64"))
    s = sum((n - e) ** 2 for n in (a, b, c, d, f, g, h, i))
    return np.sqrt(s).astype("float32")


def block_mean(z, k):
    """Strict block mean: a block containing any NaN becomes NaN. Shape must divide by k."""
    if k == 1:
        return z.astype("float64")
    H, W = z.shape
    if H % k or W % k:
        raise ValueError(f"shape {z.shape} not divisible by {k}")
    return z.astype("float64").reshape(H // k, k, W // k, k).mean(axis=(1, 3))


def upsample(z, k):
    return np.repeat(np.repeat(z, k, axis=0), k, axis=1) if k > 1 else z


def local_std(x, size=3):
    """Std-dev in a size x size window; NaN unless the whole window is valid."""
    x = np.asarray(x, dtype="float64")
    valid = np.isfinite(x)
    x0 = np.where(valid, x, 0.0)
    n = ndi.uniform_filter(valid.astype("float64"), size=size, mode="constant")
    m = ndi.uniform_filter(x0, size=size, mode="constant") / np.maximum(n, 1e-12)
    m2 = ndi.uniform_filter(x0 ** 2, size=size, mode="constant") / np.maximum(n, 1e-12)
    var = np.maximum(m2 - m ** 2, 0.0)
    return np.where(n > 0.999, np.sqrt(var), np.nan).astype("float32")


def coarse_slope(z, res, k, method="horn"):
    """Slope at k-times coarser support, returned on the original grid (nearest)."""
    zc = block_mean(z, k)
    sc = slope_deg(zc, res * k, method)
    return upsample(sc, k)


def classes(s, t):
    """1 = ABOVE (>= t), 0 = BELOW, NaN where slope is NaN."""
    out = (s >= t).astype("float32")
    out[~np.isfinite(s)] = np.nan
    return out


def decision_features(z_by_dem, primary, res, t):
    """Features available at decision time (never uses reference data).

    z_by_dem: dict name -> elevation array on the 30-m grid (NaN = NoData)
    primary : key of the DEM whose class is being predicted
    Returns dict of 2-D float32 arrays.
    """
    zp = z_by_dem[primary]
    s30 = slope_deg(zp, res)
    slopes = {k: slope_deg(v, res) for k, v in z_by_dem.items()}
    stack = np.stack([slopes[k] for k in sorted(slopes)], axis=0)
    with np.errstate(all="ignore"):
        dis_std = np.nanstd(stack, axis=0)
        votes = np.nanmean(np.where(np.isfinite(stack), (stack >= t).astype("float32"), np.nan), axis=0)
    all_ok = np.all(np.isfinite(stack), axis=0)
    dis_std = np.where(all_ok, dis_std, np.nan)
    vote_split = np.where(all_ok, np.minimum(votes, 1 - votes), np.nan)  # 0 = unanimous
    s60 = coarse_slope(zp, res, 2)
    s90 = coarse_slope(zp, res, 3)
    scale_instab = np.maximum(np.abs(s60 - s30), np.abs(s90 - s30))
    scale_flip = ((s60 >= t) != (s30 >= t)).astype("float32") + ((s90 >= t) != (s30 >= t)).astype("float32")
    scale_flip[~np.isfinite(scale_instab)] = np.nan
    return {
        "slope": s30,
        "dist": np.abs(s30 - t).astype("float32"),
        "dem_disagreement_std": dis_std.astype("float32"),
        "vote_split": vote_split.astype("float32"),
        "local_slope_std": local_std(s30, 3),
        "tri": tri_riley(zp),
        "scale_instab": scale_instab.astype("float32"),
        "scale_flip": scale_flip,
        "pred": classes(s30, t),
    }
