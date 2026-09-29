# grazing

Decision-support toolkit for livestock grazing in Greek rangelands. Pilot region: Epirus.

Goal: estimate where a herd (cattle, sheep, goats) can graze and for how long, by combining
a grazing-land mask (land cover x slope) with Copernicus Dry Matter Productivity (DMP) biomass.

## Setup

```bash
uv sync
```

## Phase 1: grazing-land mask

```bash
uv run grazing fetch-landcover        # ESA WorldCover 2021, 10 m (public S3)
uv run grazing fetch-dem              # Copernicus DEM GLO-30 (Planetary Computer) + slope
uv run grazing build-mask             # -> data/processed/grazing_mask_epirus.tif + area summary
# or: uv run grazing run-all
```

Output raster (EPSG:32634, 10 m), uint8, nodata 255:

| band | name | values |
|---|---|---|
| 1 | grazing_class | 0 excluded, 1 grassland, 2 shrubland, 3 sparse, 4 cropland |
| 2-4 | suitable_cattle / sheep / goats | 1 where class is grazeable (cropland only if `include_cropland`) and slope <= animal threshold |

All thresholds, class mappings and edibility factors live in `config/epirus.yaml`.

## Data sources

- ESA WorldCover 2021 v200 (10 m land cover)
- Copernicus DEM GLO-30 (slope)
- geoBoundaries GRC ADM2 (region outline)
- Planned: Copernicus Land Monitoring Service DMP/GDMP 300 m 10-daily (biomass), needs a
  Copernicus Data Space Ecosystem account; put credentials in `.env`, never in the repo.

## Roadmap

1. Grazing-land mask (done, phase 1)
2. DMP ingestion and per-unit forage supply
3. Herd demand (livestock units) and supply/demand matching
4. Ranking of pasture units and map/table outputs
5. Validation against regional grazing management plan figures

## Viewing in QGIS

```bash
uv run grazing export-qgis
```

adds overviews and `.qml` style sidecars, so `grazing_mask_epirus.tif` opens as a paletted class map
(band 1) and `suitable_{cattle,sheep,goats}_epirus.tif` open as green/grey suitability maps.
Without the `.qml`, QGIS renders the 4-band file as an RGB composite of values 0-4, which looks blank.
