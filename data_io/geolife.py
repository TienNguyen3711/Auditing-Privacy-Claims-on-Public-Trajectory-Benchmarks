"""GeoLife 1.3 loader.

PLT format (User Guide 1.3): lines 1-6 are headers; then `lat,lon,0,altitude_ft,days_since_1899-12-30,date,time`.
Timestamps are GMT, so local Beijing time is GMT+8.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

from data_io.geo import BEIJING_BBOX, in_bbox

BEIJING_UTC_OFFSET = dt.timedelta(hours=8)
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "data" / "Geolife Trajectories 1.3" / "Data"


@dataclass(frozen=True)
class Point:
    t: dt.datetime  # Beijing local time (naive)
    lat: float
    lon: float


def users(root: Path = DEFAULT_ROOT) -> list[str]:
    return sorted(p.name for p in root.iterdir() if p.is_dir())


def user_files(user: str, root: Path = DEFAULT_ROOT) -> list[Path]:
    return sorted((root / user / "Trajectory").glob("*.plt"))


def read_plt(path: Path) -> list[Point]:
    out = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            if i < 6:
                continue
            f = line.strip().split(",")
            if len(f) < 7:
                continue
            t = dt.datetime.strptime(f"{f[5]} {f[6]}", "%Y-%m-%d %H:%M:%S") + BEIJING_UTC_OFFSET
            out.append(Point(t, float(f[0]), float(f[1])))
    return out


def load_user(user: str, root: Path = DEFAULT_ROOT, bbox=BEIJING_BBOX) -> list[Point]:
    """All points of one user inside the bounding box, sorted by time, exact duplicates removed."""
    pts = {p for f in user_files(user, root) for p in read_plt(f) if in_bbox(p.lat, p.lon, bbox)}
    return sorted(pts, key=lambda p: p.t)


def load_group(members: list[str], root: Path = DEFAULT_ROOT, bbox=BEIJING_BBOX) -> list[Point]:
    """One person = the union of the member users' points (data_io.user_groups), identical points kept once.

    Points are compared after parsing, so copies with the same raw (date, time, lat, lon) collapse. Two members may
    still hold different points at the same second; both are kept, in time order.
    """
    pts = {p for u in members for f in user_files(u, root) for p in read_plt(f) if in_bbox(p.lat, p.lon, bbox)}
    return sorted(pts, key=lambda p: (p.t, p.lat, p.lon))
