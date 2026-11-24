"""Statistics-preserving geometric control (N2): rotate a user's points about their centroid.

Rotation in a local metric projection keeps step lengths, speeds and timing unchanged (up to projection error at
city scale) while moving every location. The same transform is applied to the ground truth.
"""
from __future__ import annotations

import math
from dataclasses import replace

from data_io.geo import LocalProjection
from data_io.geolife import Point


class Rotation:
    def __init__(self, lat0: float, lon0: float, angle_deg: float):
        self.proj = LocalProjection(lat0, lon0)
        a = math.radians(angle_deg)
        self.c, self.s = math.cos(a), math.sin(a)

    @classmethod
    def about_centroid(cls, points: list[Point], angle_deg: float) -> "Rotation":
        return cls(sum(p.lat for p in points) / len(points), sum(p.lon for p in points) / len(points), angle_deg)

    def latlon(self, lat: float, lon: float) -> tuple[float, float]:
        x, y = self.proj.to_xy(lat, lon)
        return self.proj.to_latlon(self.c * x - self.s * y, self.s * x + self.c * y)

    def points(self, points: list[Point]) -> list[Point]:
        out = []
        for p in points:
            lat, lon = self.latlon(p.lat, p.lon)
            out.append(replace(p, lat=lat, lon=lon))
        return out
