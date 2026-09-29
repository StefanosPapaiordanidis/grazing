"""QGIS-friendly exports: overviews, style sidecars (.qml) and per-animal single-band rasters."""

from __future__ import annotations

from pathlib import Path

import rasterio
from rasterio.enums import Resampling

from .config import ANIMALS, CODE_NAMES, Config

CLASS_COLORS = {
    0: ("#e6e6e6", "excluded"),
    1: ("#5fae3a", "grassland"),
    2: ("#b8863b", "shrubland"),
    3: ("#d9d0b0", "sparse"),
    4: ("#f2e394", "cropland"),
}
SUIT_COLORS = {0: ("#f0f0f0", "not suitable"), 1: ("#1b7837", "suitable")}

_QML = """<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.34" styleCategories="AllStyleCategories" hasScaleBasedVisibilityFlag="0">
  <pipe>
    <provider>
      <resampling enabled="false" zoomedInResamplingMethod="nearestNeighbour" zoomedOutResamplingMethod="nearestNeighbour" maxOversampling="2"/>
    </provider>
    <rasterrenderer type="paletted" opacity="1" band="{band}" alphaBand="-1" nodataColor="">
      <colorPalette>
{entries}
      </colorPalette>
    </rasterrenderer>
    <brightnesscontrast brightness="0" contrast="0" gamma="1"/>
    <huesaturation saturation="0" grayscaleMode="0" colorizeOn="0"/>
    <rasterresampler maxOversampling="2"/>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
"""


def write_qml(tif: Path, palette: dict[int, tuple[str, str]], band: int = 1) -> Path:
    entries = "\n".join(
        f'        <paletteEntry value="{v}" color="{c}" label="{lbl}" alpha="255"/>'
        for v, (c, lbl) in palette.items()
    )
    qml = tif.with_suffix(".qml")
    qml.write_text(_QML.format(band=band, entries=entries))
    return qml


def add_overviews(tif: Path, factors=(4, 16, 64, 256)) -> None:
    with rasterio.open(tif, "r+") as ds:
        if not ds.overviews(1):
            ds.build_overviews(factors, Resampling.nearest)
            ds.update_tags(ns="rio_overview", resampling="nearest")


def export_qgis(cfg: Config, mask_path: Path) -> list[Path]:
    """Add overviews + .qml to the mask, and write one styled single-band GeoTIFF per animal."""
    add_overviews(mask_path)
    outputs = [write_qml(mask_path, CLASS_COLORS, band=1)]

    with rasterio.open(mask_path) as src:
        profile = src.profile.copy()
        profile.update(count=1)
        for i, animal in enumerate(ANIMALS, start=2):
            out = cfg.processed_dir / f"suitable_{animal}_{cfg.name}.tif"
            with rasterio.open(out, "w", **profile) as dst:
                for _, win in src.block_windows(1):
                    dst.write(src.read(i, window=win), 1, window=win)
                dst.descriptions = (f"suitable_{animal}",)
            add_overviews(out)
            write_qml(out, SUIT_COLORS)
            outputs.append(out)
    return outputs
