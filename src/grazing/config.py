"""Configuration loading."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Integer codes used in the grazing-class raster.
CLASS_CODES = {"excluded": 0, "grassland": 1, "shrubland": 2, "sparse": 3, "cropland": 4}
CODE_NAMES = {v: k for k, v in CLASS_CODES.items()}
ANIMALS = ("cattle", "sheep", "goats")


@dataclass
class Config:
    root: Path
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        path = Path(path).resolve()
        with open(path) as f:
            raw = yaml.safe_load(f)
        # Project root is the parent of the config/ directory.
        return cls(root=path.parent.parent, raw=raw)

    def __getitem__(self, key: str) -> Any:
        return self.raw[key]

    @property
    def name(self) -> str:
        return self.raw["aoi"]["name"]

    @property
    def aoi_path(self) -> Path:
        return self.root / self.raw["aoi"]["path"]

    @property
    def crs(self) -> str:
        return self.raw["crs"]

    @property
    def resolution(self) -> float:
        return float(self.raw["resolution_m"])

    @property
    def raw_dir(self) -> Path:
        d = self.root / self.raw["paths"]["raw"]
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def processed_dir(self) -> Path:
        d = self.root / self.raw["paths"]["processed"]
        d.mkdir(parents=True, exist_ok=True)
        return d

    def landcover_map(self) -> dict[int, int]:
        """WorldCover code -> grazing class code. Cropland is always mapped so it shows in the class map."""
        m = {int(k): CLASS_CODES[v] for k, v in self.raw["landcover"]["classes"].items()}
        m[40] = CLASS_CODES["cropland"]
        return m

    @property
    def include_cropland(self) -> bool:
        """Whether cropland counts as grazeable (post-harvest stubble) in the suitability bands."""
        return bool(self.raw["landcover"].get("include_cropland", False))
