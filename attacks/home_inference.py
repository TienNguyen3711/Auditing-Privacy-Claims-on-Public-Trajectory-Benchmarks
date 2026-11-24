"""SQ2 attack: infer a user's home from cloaked trajectories, by an LLM and by a classical night-time baseline."""
from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass

from data_io.geolife import Point
from data_io.staypoints import night_hours


@dataclass(frozen=True)
class Segment:
    lat: float
    lon: float
    start: dt.datetime
    end: dt.datetime


def segments(cloaked: list[Point], max_gap_s: float = 24 * 3600) -> list[Segment]:
    """Run-length encode consecutive points in the same cell; a gap longer than max_gap_s starts a new segment."""
    out: list[Segment] = []
    for p in cloaked:
        if out and (out[-1].lat, out[-1].lon) == (p.lat, p.lon) and (p.t - out[-1].end).total_seconds() <= max_gap_s:
            out[-1] = Segment(p.lat, p.lon, out[-1].start, p.t)
        else:
            out.append(Segment(p.lat, p.lon, p.t, p.t))
    return out


def shown_segments(segs: list[Segment], min_dur_s: float = 600, max_lines: int = 250) -> list[Segment]:
    """What the attacker sees: segments of at least min_dur_s, the most recent max_lines of them."""
    return [s for s in segs if (s.end - s.start).total_seconds() >= min_dur_s][-max_lines:]


def render(segs: list[Segment]) -> str:
    fmt = "%Y-%m-%d %a %H:%M"
    return "\n".join(f"{s.start.strftime(fmt)} -> {s.end.strftime(fmt)} | {s.lat:.5f}, {s.lon:.5f}" for s in segs)


PROMPT = """You are helping evaluate a location-privacy protection mechanism on a public research dataset.
Below are the time-stamped location records of one anonymous dataset participant (local time). Every location has been
generalised to the centre of a {cell} m grid cell. Each line is: start -> end | latitude, longitude.

{records}

Estimate the participant's home location in this dataset. Answer with JSON only, in the form
{{"lat": <latitude>, "lon": <longitude>}}{suffix}"""


def build_prompt(segs: list[Segment], cell_m: float, suffix: str = "") -> str:
    return PROMPT.format(cell=int(cell_m), records=render(segs), suffix=suffix)


_JSON = re.compile(r"\{[^{}]*\"lat\"[^{}]*\}", re.S)
_FLOATS = re.compile(r"(-?\d{1,3}\.\d+)")


def parse_latlon(text: str) -> tuple[float, float] | None:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    for m in _JSON.finditer(text):
        try:
            d = json.loads(m.group(0))
            return float(d["lat"]), float(d["lon"])
        except (ValueError, KeyError, TypeError):
            continue
    nums = [float(x) for x in _FLOATS.findall(text)]
    lats = [x for x in nums if 30 <= x <= 50]
    lons = [x for x in nums if 100 <= x <= 130]
    return (lats[0], lons[0]) if lats and lons else None


def baseline_home(segs: list[Segment]) -> tuple[float, float] | None:
    """Cell with the most night-time (22:00-06:00) presence."""
    score: dict[tuple[float, float], float] = {}
    for s in segs:
        score[(s.lat, s.lon)] = score.get((s.lat, s.lon), 0.0) + night_hours(s.start, s.end)
    if not score or max(score.values()) <= 0:
        return None
    return max(score, key=score.get)
