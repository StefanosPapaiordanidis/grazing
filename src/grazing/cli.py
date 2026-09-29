"""Command line interface."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from .config import Config

app = typer.Typer(help="Grazing suitability toolkit", no_args_is_help=True)
CFG_OPT = typer.Option("config/epirus.yaml", "--config", "-c", help="YAML config path")


@app.command()
def fetch_landcover(config: Path = CFG_OPT, overwrite: bool = False):
    """Download ESA WorldCover 2021 for the AOI."""
    from .landcover import fetch_worldcover
    cfg = Config.load(config)
    typer.echo(fetch_worldcover(cfg, overwrite=overwrite))


@app.command()
def fetch_dem(config: Path = CFG_OPT, overwrite: bool = False):
    """Download Copernicus DEM GLO-30 for the AOI and derive slope."""
    from .dem import compute_slope, fetch_dem as _fetch
    cfg = Config.load(config)
    dem = _fetch(cfg, overwrite=overwrite)
    typer.echo(dem)
    typer.echo(compute_slope(cfg, dem, overwrite=overwrite))


@app.command()
def build_mask(config: Path = CFG_OPT, overwrite: bool = False):
    """Combine land cover, slope and AOI into the grazing mask and print an area summary."""
    from .mask import build_mask as _build, summarize
    cfg = Config.load(config)
    wc = cfg.raw_dir / f"worldcover_2021_{cfg.name}.tif"
    sl = cfg.processed_dir / f"slope_deg_{cfg.name}.tif"
    for p in (wc, sl):
        if not p.exists():
            raise typer.BadParameter(f"missing input {p}; run fetch-landcover / fetch-dem first")
    out = _build(cfg, wc, sl, overwrite=overwrite)
    typer.echo(out)
    typer.echo(json.dumps(summarize(cfg, out), indent=2))


@app.command()
def run_all(config: Path = CFG_OPT, overwrite: bool = False):
    """Fetch inputs and build the mask in one go."""
    fetch_landcover(config, overwrite)
    fetch_dem(config, overwrite)
    build_mask(config, overwrite)



@app.command()
def export_qgis(config: Path = CFG_OPT):
    """Add overviews and QGIS styles to the mask; write per-animal suitability rasters."""
    from .qgis import export_qgis as _export
    cfg = Config.load(config)
    mask = cfg.processed_dir / f"grazing_mask_{cfg.name}.tif"
    if not mask.exists():
        raise typer.BadParameter(f"missing {mask}; run build-mask first")
    for p in _export(cfg, mask):
        typer.echo(p)


def main():
    app()
