"""Area of interest helpers."""

from __future__ import annotations

import math

import geopandas as gpd
from shapely.geometry import box

from .config import Config


def load_aoi(cfg: Config) -> gpd.GeoDataFrame:
    return gpd.read_file(cfg.aoi_path).to_crs("EPSG:4326")


def aoi_bounds_wgs84(cfg: Config, pad_deg: float = 0.01) -> tuple[float, float, float, float]:
    minx, miny, maxx, maxy = load_aoi(cfg).total_bounds
    return (minx - pad_deg, miny - pad_deg, maxx + pad_deg, maxy + pad_deg)


def aoi_bbox_geom(cfg: Config):
    return box(*aoi_bounds_wgs84(cfg))


def tile_corners(bounds: tuple[float, float, float, float], step: int) -> list[tuple[int, int]]:
    """Lower-left corners (lat, lon) of `step`-degree tiles intersecting bounds."""
    minx, miny, maxx, maxy = bounds
    lats = range(int(math.floor(miny / step) * step), int(math.floor(maxy / step) * step) + 1, step)
    lons = range(int(math.floor(minx / step) * step), int(math.floor(maxx / step) * step) + 1, step)
    return [(lat, lon) for lat in lats for lon in lons]
