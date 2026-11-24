"""Cross-user duplicate scan for GeoLife 1.3.

A point is identified by its raw (date, time, lat, lon) fields as written in the PLT file (no float rounding).
Reports (1) PLT files whose data lines are byte-identical across users and (2) for every user pair, the number of
identical points and the share of each user's points that they make up.

Usage (from the code folder): python -m data_io.duplicates [--out results/<date>_geolife_duplicates]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from data_io.geolife import DEFAULT_ROOT, user_files, users

ROOT = Path(__file__).resolve().parents[1]


def data_lines(path: Path) -> list[str]:
    with path.open(encoding="utf-8", errors="replace") as fh:
        return [ln.strip() for i, ln in enumerate(fh) if i >= 6 and ln.strip()]


def point_key(line: str) -> int | None:
    f = line.split(",")
    if len(f) < 7:
        return None
    return hash((f[5], f[6], f[0], f[1]))  # date, time, lat, lon as written


def scan(root: Path = DEFAULT_ROOT, log=lambda m: None) -> dict:
    seen: dict[int, str] = {}            # point key -> first user holding it
    pair_points: Counter = Counter()      # (earlier user, later user) -> identical points
    n_points: dict[str, int] = {}         # distinct points per user
    file_hash: dict[str, list[str]] = defaultdict(list)
    for u in users(root):
        own: set[int] = set()
        for f in user_files(u, root):
            lines = data_lines(f)
            file_hash[hashlib.sha256("\n".join(lines).encode()).hexdigest()].append(f"{u}/{f.name}")
            for ln in lines:
                k = point_key(ln)
                if k is not None:
                    own.add(k)
        n_points[u] = len(own)
        for k in own:
            first = seen.setdefault(k, u)
            if first != u:
                pair_points[(first, u)] += 1
        log(f"user {u}: {len(own)} distinct points")
    pairs = [{"user_a": a, "user_b": b, "shared_points": n,
              "share_of_a": round(n / n_points[a], 4), "share_of_b": round(n / n_points[b], 4)}
             for (a, b), n in pair_points.most_common()]
    dup_files = {h: fs for h, fs in file_hash.items() if len({x.split("/")[0] for x in fs}) > 1}
    return {"users": len(n_points), "points_per_user": n_points, "total_distinct_points": len(seen),
            "pairs": pairs, "identical_files_across_users": list(dup_files.values())}


def report_md(r: dict, min_share: float = 0.01) -> str:
    big = [p for p in r["pairs"] if max(p["share_of_a"], p["share_of_b"]) >= min_share]
    involved = sorted({p["user_a"] for p in big} | {p["user_b"] for p in big})
    lines = ["# GeoLife 1.3 cross-user duplicate scan", "",
             f"- users scanned: {r['users']}",
             f"- distinct points overall (by raw date, time, lat, lon): {r['total_distinct_points']:,}",
             f"- user pairs sharing any identical point: {len(r['pairs'])}",
             f"- pairs where shared points are >= {min_share:.0%} of either user: {len(big)} "
             f"(users involved: {', '.join(involved) or 'none'})",
             f"- PLT files byte-identical across users: {len(r['identical_files_across_users'])} groups", "",
             "| user A | user B | shared points | share of A | share of B |", "|---|---|---|---|---|"]
    lines += [f"| {p['user_a']} | {p['user_b']} | {p['shared_points']:,} | {p['share_of_a']:.1%} | {p['share_of_b']:.1%} |"
              for p in big]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    out = a.out or ROOT / "results" / f"{dt.date.today():%Y%m%d}_geolife_duplicates"
    out.mkdir(parents=True, exist_ok=True)
    r = scan(log=lambda m: print(m, file=sys.stderr, flush=True))
    (out / "duplicates.json").write_text(json.dumps(r, indent=1))
    (out / "report.md").write_text(report_md(r))
    print(report_md(r))
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
