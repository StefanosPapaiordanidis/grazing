"""Fetch ESA WorldCover 2021 (10 m) for the AOI from the public S3 bucket."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.windows import from_bounds

from .aoi import aoi_bounds_wgs84, tile_corners
from .config import Config

WC_URL = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{lat}{lon}_Map.tif"


def _tile_name(lat: int, lon: int) -> tuple[str, str]:
    ns = f"N{lat:02d}" if lat >= 0 else f"S{-lat:02d}"
    ew = f"E{lon:03d}" if lon >= 0 else f"W{-lon:03d}"
    return ns, ew


def fetch_worldcover(cfg: Config, overwrite: bool = False) -> Path:
    """Download the AOI window of each intersecting WorldCover tile and mosaic them (WGS84, 10 m)."""
    out = cfg.raw_dir / f"worldcover_2021_{cfg.name}.tif"
    if out.exists() and not overwrite:
        return out

    bounds = aoi_bounds_wgs84(cfg)
    datasets = []
    for lat, lon in tile_corners(bounds, step=3):
        ns, ew = _tile_name(lat, lon)
        url = WC_URL.format(lat=ns, lon=ew)
        try:
            src = rasterio.open(url)
        except rasterio.errors.RasterioIOError:
            continue  # tile does not exist (sea)
        win = from_bounds(*bounds, transform=src.transform).round_offsets().round_lengths()
        win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
        if win.width <= 0 or win.height <= 0:
            src.close()
            continue
        data = src.read(1, window=win)
        profile = src.profile.copy()
        profile.update(width=int(win.width), height=int(win.height),
                       transform=src.window_transform(win), driver="GTiff")
        tmp = cfg.raw_dir / f"_wc_{ns}{ew}.tif"
        with rasterio.open(tmp, "w", **profile) as dst:
            dst.write(data, 1)
        src.close()
        datasets.append(tmp)

    if not datasets:
        raise RuntimeError("No WorldCover tiles intersect the AOI")

    srcs = [rasterio.open(p) for p in datasets]
    mosaic, transform = merge(srcs, bounds=bounds, nodata=0)
    profile = srcs[0].profile.copy()
    for s in srcs:
        s.close()
    for p in datasets:
        p.unlink()
    profile.update(height=mosaic.shape[1], width=mosaic.shape[2], transform=transform,
                   nodata=0, compress="deflate", tiled=True, blockxsize=512, blockysize=512)
    with rasterio.open(out, "w", **profile) as dst:
        dst.write(mosaic[0].astype(np.uint8), 1)
    return out
