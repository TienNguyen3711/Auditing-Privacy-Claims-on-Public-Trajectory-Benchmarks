"""GeoLife "persons": users merged into groups when they share identical points (policy (a), approved 2026-11-24).

Two users are linked when they share at least `min_shared_points` identical raw (date, time, lat, lon) points in the
duplicate scan (`data_io.duplicates`); groups are the connected components. Default 1 (the conservative choice): for
user-level adjacency, removing one user while copies of their data stay under another user would not give a true
neighbouring dataset. Group id = "g" + the smallest member id; a user without shared points is a group of one.

Usage (from the code folder):
  python -m data_io.user_groups [--scan results/<date>_geolife_duplicates/duplicates.json] [--min-shared-points 1]
writes configs/geolife_user_groups.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCAN = ROOT / "results" / "20261124_geolife_duplicates" / "duplicates.json"
DEFAULT_OUT = ROOT / "configs" / "geolife_user_groups.json"


def build(users: list[str], pairs: list[dict], min_shared_points: int = 1) -> dict[str, list[str]]:
    parent = {u: u for u in users}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for p in pairs:
        if p["shared_points"] >= min_shared_points:
            a, b = find(p["user_a"]), find(p["user_b"])
            if a != b:
                parent[max(a, b)] = min(a, b)
    groups: dict[str, list[str]] = {}
    for u in sorted(users):
        groups.setdefault(find(u), []).append(u)
    return {f"g{min(m)}": m for m in sorted(groups.values(), key=min)}


def load(path: Path = DEFAULT_OUT) -> dict[str, list[str]]:
    return json.loads(path.read_text())["groups"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scan", type=Path, default=DEFAULT_SCAN)
    ap.add_argument("--min-shared-points", type=int, default=1)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args(argv)
    scan = json.loads(a.scan.read_text())
    groups = build(list(scan["points_per_user"]), scan["pairs"], a.min_shared_points)
    multi = {g: m for g, m in groups.items() if len(m) > 1}
    doc = {
        "policy": "(a) users sharing identical raw points are merged into one person (connected components)",
        "min_shared_points": a.min_shared_points,
        "source_scan": str(a.scan.relative_to(ROOT)) if a.scan.is_relative_to(ROOT) else str(a.scan),
        "created": dt.date.today().isoformat(),
        "n_users": sum(len(m) for m in groups.values()),
        "n_groups": len(groups),
        "n_multi_user_groups": len(multi),
        "points_per_group": {g: sum(scan["points_per_user"][u] for u in m) for g, m in groups.items()},
        "groups": groups,
    }
    a.out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"{doc['n_users']} users -> {doc['n_groups']} groups ({len(multi)} with more than one user); written {a.out}")
    for g, m in sorted(multi.items(), key=lambda kv: -len(kv[1])):
        print(f"  {g}: {len(m)} users {', '.join(m)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
