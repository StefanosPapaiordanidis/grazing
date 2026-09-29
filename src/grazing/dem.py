"""Copernicus DEM GLO-30 via Microsoft Planetary Computer STAC, and slope derivation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import planetary_computer as pc
import rasterio
from pystac_client import Client
from rasterio.merge import merge
from rasterio.warp import Resampling, calculate_default_transform, reproject
from rasterio.windows import from_bounds

from .aoi import aoi_bounds_wgs84
from .config import Config

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"


def fetch_dem(cfg: Config, overwrite: bool = False) -> Path:
    """Mosaic the GLO-30 tiles covering the AOI (WGS84, ~30 m)."""
    out = cfg.raw_dir / f"cop_dem_glo30_{cfg.name}.tif"
    if out.exists() and not overwrite:
        return out

    bounds = aoi_bounds_wgs84(cfg)
    catalog = Client.open(STAC, modifier=pc.sign_inplace)
    items = list(catalog.search(collections=["cop-dem-glo-30"], bbox=bounds).items())
    if not items:
        raise RuntimeError("No DEM tiles found for AOI")

    tmp_files = []
    for it in items:
        href = it.assets["data"].href
        with rasterio.open(href) as src:
            win = from_bounds(*bounds, transform=src.transform).round_offsets().round_lengths()
            win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
            if win.width <= 0 or win.height <= 0:
                continue
            data = src.read(1, window=win)
            profile = src.profile.copy()
            profile.update(width=int(win.width), height=int(win.height),
                           transform=src.window_transform(win), driver="GTiff")
        tmp = cfg.raw_dir / f"_dem_{it.id}.tif"
        with rasterio.open(tmp, "w", **profile) as dst:
            dst.write(data, 1)
        tmp_files.append(tmp)

    srcs = [rasterio.open(p) for p in tmp_files]
    mosaic, transform = merge(srcs, bounds=bounds)
    profile = srcs[0].profile.copy()
    for s in srcs:
        s.close()
    for p in tmp_files:
        p.unlink()
    profile.update(height=mosaic.shape[1], width=mosaic.shape[2], transform=transform,
                   compress="deflate", tiled=True, blockxsize=512, blockysize=512)
    with rasterio.open(out, "w", **profile) as dst:
        dst.write(mosaic[0], 1)
    return out


def compute_slope(cfg: Config, dem_path: Path, overwrite: bool = False) -> Path:
    """Reproject DEM to the working CRS at ~30 m and compute slope in degrees (Horn's method)."""
    out = cfg.processed_dir / f"slope_deg_{cfg.name}.tif"
    if out.exists() and not overwrite:
        return out

    with rasterio.open(dem_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs, cfg.crs, src.width, src.height, *src.bounds, resolution=30.0
        )
        dem = np.full((height, width), np.nan, dtype="float32")
        reproject(
            rasterio.band(src, 1), dem, dst_transform=transform, dst_crs=cfg.crs,
            src_nodata=src.nodata, dst_nodata=np.nan, resampling=Resampling.bilinear,
        )
        profile = src.profile.copy()

    dx = transform.a
    dy = -transform.e
    z = np.pad(dem, 1, mode="edge")
    # Horn (1981) finite differences.
    dzdx = ((z[:-2, 2:] + 2 * z[1:-1, 2:] + z[2:, 2:]) - (z[:-2, :-2] + 2 * z[1:-1, :-2] + z[2:, :-2])) / (8 * dx)
    dzdy = ((z[2:, :-2] + 2 * z[2:, 1:-1] + z[2:, 2:]) - (z[:-2, :-2] + 2 * z[:-2, 1:-1] + z[:-2, 2:])) / (8 * dy)
    slope = np.degrees(np.arctan(np.hypot(dzdx, dzdy))).astype("float32")

    profile.update(driver="GTiff", crs=cfg.crs, transform=transform, width=width, height=height,
                   dtype="float32", nodata=-9999, compress="deflate", tiled=True,
                   blockxsize=512, blockysize=512)
    slope = np.where(np.isnan(slope), -9999, slope).astype("float32")
    with rasterio.open(out, "w", **profile) as dst:
        dst.write(slope, 1)
    return out
