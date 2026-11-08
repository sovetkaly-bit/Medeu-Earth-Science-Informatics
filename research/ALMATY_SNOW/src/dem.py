"""Copernicus GLO-30 DEM (Planetary Computer, anonymous) resampled to a target grid."""
import numpy as np
import planetary_computer
import pystac_client
import rasterio
from rasterio.merge import merge
from rasterio.warp import reproject, Resampling

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"


def dem_on_grid(aoi, dst_crs, dst_transform, dst_shape, collection="cop-dem-glo-30", resampling=Resampling.average):
    cat = pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)
    pad = 0.1
    bbox = [aoi["west"] - pad, aoi["south"] - pad, aoi["east"] + pad, aoi["north"] + pad]
    items = list(cat.search(collections=[collection], bbox=bbox).items())
    if not items:
        raise RuntimeError("no DEM tiles found for the AOI")
    srcs = [rasterio.open(it.assets["data"].href) for it in items]
    try:
        mosaic, m_tr = merge(srcs, bounds=tuple(bbox))
        src_crs = srcs[0].crs
    finally:
        for s in srcs:
            s.close()
    dst = np.full(dst_shape, np.nan, dtype="float32")
    reproject(source=mosaic[0].astype("float32"), destination=dst, src_transform=m_tr, src_crs=src_crs,
              dst_transform=dst_transform, dst_crs=dst_crs, resampling=resampling,
              src_nodata=None, dst_nodata=np.nan)
    return dst, [it.id for it in items]
