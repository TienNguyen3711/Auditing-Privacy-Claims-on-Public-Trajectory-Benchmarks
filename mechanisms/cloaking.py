"""Non-DP mechanism 1: spatial cloaking by grid generalisation (every point snapped to its cell centre)."""
from __future__ import annotations

import math
from dataclasses import replace

from data_io.geo import LocalProjection
from data_io.geolife import Point

# Fixed grid origin for the Beijing area, so original and control are cloaked on the same grid.
GRID_ORIGIN = (39.9, 116.4)


class GridCloak:
    def __init__(self, cell_m: float = 500, origin: tuple[float, float] = GRID_ORIGIN):
        self.cell = cell_m
        self.proj = LocalProjection(*origin)

    def cell_of(self, lat: float, lon: float) -> tuple[int, int]:
        x, y = self.proj.to_xy(lat, lon)
        return math.floor(x / self.cell), math.floor(y / self.cell)

    def centre(self, cell: tuple[int, int]) -> tuple[float, float]:
        return self.proj.to_latlon((cell[0] + 0.5) * self.cell, (cell[1] + 0.5) * self.cell)

    def apply(self, points: list[Point]) -> list[Point]:
        out = []
        for p in points:
            lat, lon = self.centre(self.cell_of(p.lat, p.lon))
            out.append(replace(p, lat=round(lat, 5), lon=round(lon, 5)))
        return out
