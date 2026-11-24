"""Stay points and dataset-internal home ground truth.

Stay points follow the distance/time-threshold rule (stay within `dist_m` for at least `min_dur_s`). A recording gap
whose two ends lie within `dist_m` of each other also counts as a stay (e.g. logger switched off overnight at home).
Home = the cluster of stay points with the most night-time presence (22:00-06:00 local) over at least `min_nights`
distinct nights. This is a property of the dataset, not a real-world identity (proposal section 5.5).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from data_io.geo import haversine_m
from data_io.geolife import Point

NIGHT_START, NIGHT_END = 22, 6


@dataclass(frozen=True)
class Stay:
    lat: float
    lon: float
    start: dt.datetime
    end: dt.datetime


def night_hours(start: dt.datetime, end: dt.datetime) -> float:
    """Hours of [start, end] that fall in 22:00-06:00."""
    total, day = 0.0, start.date() - dt.timedelta(days=1)
    while dt.datetime.combine(day, dt.time()) < end:
        n0 = dt.datetime.combine(day, dt.time(NIGHT_START))
        n1 = dt.datetime.combine(day + dt.timedelta(days=1), dt.time(NIGHT_END))
        overlap = (min(end, n1) - max(start, n0)).total_seconds()
        total += max(0.0, overlap) / 3600
        day += dt.timedelta(days=1)
    return total


def nights_covered(start: dt.datetime, end: dt.datetime) -> set[dt.date]:
    """Dates d such that [start, end] overlaps the night starting at 22:00 on d."""
    out, day = set(), start.date() - dt.timedelta(days=1)
    while dt.datetime.combine(day, dt.time()) < end:
        n0 = dt.datetime.combine(day, dt.time(NIGHT_START))
        n1 = dt.datetime.combine(day + dt.timedelta(days=1), dt.time(NIGHT_END))
        if min(end, n1) > max(start, n0):
            out.add(day)
        day += dt.timedelta(days=1)
    return out


def detect_stays(points: list[Point], dist_m: float = 200, min_dur_s: float = 1200,
                 max_gap_s: float = 36 * 3600) -> list[Stay]:
    stays, i, n = [], 0, len(points)
    while i < n - 1:
        j = i + 1
        # A stay never spans a recording gap longer than max_gap_s: days without data are not evidence of presence
        # (found on user 010: two fixes 8 days apart at one place had become a 208 h stay with 64.5 night hours).
        while (j < n and haversine_m(points[i].lat, points[i].lon, points[j].lat, points[j].lon) <= dist_m
               and (points[j].t - points[j - 1].t).total_seconds() <= max_gap_s):
            j += 1
        group = points[i:j]
        dur = (group[-1].t - group[0].t).total_seconds()
        if len(group) > 1 and dur >= min_dur_s:
            stays.append(Stay(sum(p.lat for p in group) / len(group), sum(p.lon for p in group) / len(group),
                              group[0].t, group[-1].t))
            i = j
            continue
        # gap stay: next point is far in time but close in space
        a, b = points[i], points[i + 1]
        gap = (b.t - a.t).total_seconds()
        if min_dur_s <= gap <= max_gap_s and haversine_m(a.lat, a.lon, b.lat, b.lon) <= dist_m:
            stays.append(Stay((a.lat + b.lat) / 2, (a.lon + b.lon) / 2, a.t, b.t))
        i += 1
    return stays


def night_clusters(stays: list[Stay], radius_m: float = 250) -> list[dict]:
    """Stays with night-time presence, greedily clustered; sorted by night hours (w), largest first."""
    clusters: list[dict] = []
    for s in sorted(stays, key=lambda s: -night_hours(s.start, s.end)):
        w = night_hours(s.start, s.end)
        if w <= 0:
            continue
        for c in clusters:
            if haversine_m(s.lat, s.lon, c["lat"], c["lon"]) <= radius_m:
                c["lat"] = (c["lat"] * c["w"] + s.lat * w) / (c["w"] + w)
                c["lon"] = (c["lon"] * c["w"] + s.lon * w) / (c["w"] + w)
                c["w"] += w
                c["nights"] |= nights_covered(s.start, s.end)
                break
        else:
            clusters.append({"lat": s.lat, "lon": s.lon, "w": w, "nights": nights_covered(s.start, s.end)})
    return sorted(clusters, key=lambda c: -c["w"])


# Quality thresholds, fixed before looking at their distribution over the 144 persons (2026-11-24).
MIN_NIGHTS = 3            # distinct nights at the home cluster
MIN_NIGHT_SHARE = 0.5     # home cluster's share of all night hours spent at any stay
MAX_DIST_MEDIAN_KM = 30   # home to the coordinate-wise median of the person's points


@dataclass(frozen=True)
class HomeAssessment:
    home: tuple[float, float] | None
    nights: int
    night_hours: float
    night_share: float
    second_share: float
    dist_median_km: float | None
    reasons: tuple[str, ...]  # empty = passed

    @property
    def passed(self) -> bool:
        return self.home is not None and not self.reasons


def assess_home(points: list[Point], stays: list[Stay], radius_m: float = 250, min_nights: int = MIN_NIGHTS,
                min_night_share: float = MIN_NIGHT_SHARE, max_dist_median_km: float = MAX_DIST_MEDIAN_KM
                ) -> HomeAssessment:
    """Home candidate plus the quality checks it passes or fails (reasons)."""
    clusters = night_clusters(stays, radius_m)
    if not clusters:
        return HomeAssessment(None, 0, 0.0, 0.0, 0.0, None, ("no night-time stays",))
    total = sum(c["w"] for c in clusters)
    best = clusters[0]
    share = best["w"] / total
    second = clusters[1]["w"] / total if len(clusters) > 1 else 0.0
    lats, lons = sorted(p.lat for p in points), sorted(p.lon for p in points)
    med = (lats[len(lats) // 2], lons[len(lons) // 2])
    dist = haversine_m(best["lat"], best["lon"], *med) / 1000
    reasons = []
    if len(best["nights"]) < min_nights:
        reasons.append(f"nights {len(best['nights'])} < {min_nights}")
    if share < min_night_share:
        reasons.append(f"night share {share:.2f} < {min_night_share}")
    if dist > max_dist_median_km:
        reasons.append(f"{dist:.1f} km from data median > {max_dist_median_km}")
    return HomeAssessment((best["lat"], best["lon"]), len(best["nights"]), round(best["w"], 2), round(share, 3),
                          round(second, 3), round(dist, 2), tuple(reasons))


def home_location(stays: list[Stay], radius_m: float = 250, min_nights: int = 3,
                  min_night_hours: float = 6) -> tuple[float, float] | None:
    """Night-weighted cluster centroid, or None when the evidence is too thin (no quality filters; see assess_home)."""
    clusters = night_clusters(stays, radius_m)
    if not clusters:
        return None
    best = clusters[0]
    if len(best["nights"]) < min_nights or best["w"] < min_night_hours:
        return None
    return best["lat"], best["lon"]
