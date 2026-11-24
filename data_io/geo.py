"""Small geodesy helpers (standard library only)."""
from __future__ import annotations

import math

EARTH_R = 6_371_008.8  # mean Earth radius, metres

# Rough Beijing box used to drop points recorded in other cities (GeoLife User Guide 1.3: most data is in Beijing).
BEIJING_BBOX = (39.4, 41.1, 115.4, 117.6)  # lat_min, lat_max, lon_min, lon_max


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R * math.asin(math.sqrt(a))


def in_bbox(lat: float, lon: float, bbox=BEIJING_BBOX) -> bool:
    return bbox[0] <= lat <= bbox[1] and bbox[2] <= lon <= bbox[3]


class LocalProjection:
    """Equirectangular projection around (lat0, lon0): metres east (x) and north (y). Accurate at city scale."""

    def __init__(self, lat0: float, lon0: float):
        self.lat0, self.lon0 = lat0, lon0
        self.kx = math.radians(1) * EARTH_R * math.cos(math.radians(lat0))
        self.ky = math.radians(1) * EARTH_R

    def to_xy(self, lat: float, lon: float) -> tuple[float, float]:
        return (lon - self.lon0) * self.kx, (lat - self.lat0) * self.ky

    def to_latlon(self, x: float, y: float) -> tuple[float, float]:
        return self.lat0 + y / self.ky, self.lon0 + x / self.kx
