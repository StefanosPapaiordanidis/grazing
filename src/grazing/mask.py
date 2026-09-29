"""Build the grazing-land mask: land-cover class x slope x AOI, per animal."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT

from .config import ANIMALS, CLASS_CODES, CODE_NAMES, Config

BLOCK = 2048


def target_grid(cfg: Config) -> tuple[rasterio.Affine, int, int, gpd.GeoDataFrame]:
    aoi = gpd.read_file(cfg.aoi_path).to_crs(cfg.crs)
    res = cfg.resolution
    minx, miny, maxx, maxy = aoi.total_bounds
    minx, maxy = np.floor(minx / res) * res, np.ceil(maxy / res) * res
    width = int(np.ceil((maxx - minx) / res))
    height = int(np.ceil((maxy - miny) / res))
    return from_origin(minx, maxy, res, res), width, height, aoi


def build_mask(cfg: Config, worldcover: Path, slope: Path, overwrite: bool = False) -> Path:
    """Write a multi-band uint8 GeoTIFF: band 1 grazing class, bands 2-4 suitability per animal."""
    out = cfg.processed_dir / f"grazing_mask_{cfg.name}.tif"
    if out.exists() and not overwrite:
        return out

    transform, width, height, aoi = target_grid(cfg)
    lc_map = cfg.landcover_map()
    lut = np.zeros(256, dtype=np.uint8)
    for wc_code, cls in lc_map.items():
        lut[wc_code] = cls
    slope_max = {a: float(cfg["slope_max_deg"][a]) for a in ANIMALS}
    grazeable = np.zeros(256, dtype=bool)
    for c in (CLASS_CODES["grassland"], CLASS_CODES["shrubland"], CLASS_CODES["sparse"]):
        grazeable[c] = True
    grazeable[CLASS_CODES["cropland"]] = cfg.include_cropland
    aoi_geoms = list(aoi.geometry)

    vrt_kw = dict(crs=cfg.crs, transform=transform, width=width, height=height)
    profile = dict(driver="GTiff", dtype="uint8", count=1 + len(ANIMALS), crs=cfg.crs,
                   transform=transform, width=width, height=height, nodata=255,
                   compress="deflate", tiled=True, blockxsize=512, blockysize=512, BIGTIFF="IF_SAFER")

    with rasterio.open(worldcover) as wc_src, rasterio.open(slope) as sl_src, \
         WarpedVRT(wc_src, resampling=Resampling.nearest, **vrt_kw) as wc, \
         WarpedVRT(sl_src, resampling=Resampling.bilinear, nodata=-9999, **vrt_kw) as sl, \
         rasterio.open(out, "w", **profile) as dst:
        dst.descriptions = ("grazing_class",) + tuple(f"suitable_{a}" for a in ANIMALS)
        for row in range(0, height, BLOCK):
            for col in range(0, width, BLOCK):
                win = rasterio.windows.Window(col, row, min(BLOCK, width - col), min(BLOCK, height - row))
                wtr = rasterio.windows.transform(win, transform)
                inside = ~geometry_mask(aoi_geoms, out_shape=(win.height, win.width), transform=wtr)
                if not inside.any():
                    dst.write(np.full((profile["count"], win.height, win.width), 255, np.uint8), window=win)
                    continue
                cls = lut[wc.read(1, window=win)]
                slp = sl.read(1, window=win)
                valid_slope = slp != -9999
                cls[~inside] = 255
                bands = [cls]
                for a in ANIMALS:
                    ok = grazeable[cls] & valid_slope & (slp <= slope_max[a])
                    band = ok.astype(np.uint8)
                    band[~inside] = 255
                    bands.append(band)
                dst.write(np.stack(bands), window=win)
    return out


def summarize(cfg: Config, mask_path: Path) -> dict:
    """Area (km2) by grazing class and by animal suitability."""
    px_km2 = (cfg.resolution ** 2) / 1e6
    class_counts = np.zeros(256, dtype=np.int64)
    animal_counts = {a: np.zeros(len(CLASS_CODES) + 1, dtype=np.int64) for a in ANIMALS}
    with rasterio.open(mask_path) as src:
        for _, win in src.block_windows(1):
            cls = src.read(1, window=win)
            class_counts += np.bincount(cls.ravel(), minlength=256)
            for i, a in enumerate(ANIMALS, start=2):
                ok = src.read(i, window=win) == 1
                animal_counts[a] += np.bincount(cls[ok].ravel(), minlength=len(CLASS_CODES) + 1)[: len(CLASS_CODES) + 1]
    total_inside = class_counts[:255].sum()
    return {
        "aoi_km2": round(total_inside * px_km2, 1),
        "by_class_km2": {CODE_NAMES[c]: round(class_counts[c] * px_km2, 1) for c in CODE_NAMES},
        "suitable_km2": {
            a: {CODE_NAMES[c]: round(animal_counts[a][c] * px_km2, 1) for c in CODE_NAMES if c != 0}
            | {"total": round(animal_counts[a][1:].sum() * px_km2, 1)}
            for a in ANIMALS
        },
    }
