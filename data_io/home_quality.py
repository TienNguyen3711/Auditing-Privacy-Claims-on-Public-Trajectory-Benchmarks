"""Home ground-truth quality over all GeoLife persons (user groups).

For every person: home candidate, nights, night share, distance to the data median, and the failed checks
(`staypoints.assess_home`; thresholds fixed in staypoints.py before this report was run).

Usage (from the code folder): python -m data_io.home_quality [--out results/<date>_home_quality]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics
import sys
from pathlib import Path

from data_io import geolife, staypoints, user_groups

ROOT = Path(__file__).resolve().parents[1]


def assess_all(log=lambda m: None) -> list[dict]:
    rows = []
    for gid, members in user_groups.load().items():
        pts = geolife.load_group(members)
        if not pts:
            rows.append({"person": gid, "members": members, "n_points": 0, "passed": False,
                         "reasons": ["no points inside the Beijing box"]})
            continue
        a = staypoints.assess_home(pts, staypoints.detect_stays(pts))
        rows.append({"person": gid, "members": members, "n_points": len(pts), "home": a.home, "nights": a.nights,
                     "night_hours": a.night_hours, "night_share": a.night_share, "second_share": a.second_share,
                     "dist_median_km": a.dist_median_km, "passed": a.passed, "reasons": list(a.reasons)})
        log(f"{gid}: {'PASS' if a.passed else 'FAIL ' + '; '.join(a.reasons)}")
    return rows


def report_md(rows: list[dict]) -> str:
    ok = [r for r in rows if r["passed"]]
    reasons: dict[str, int] = {}
    for r in rows:
        for x in r["reasons"]:
            key = x.split(" ")[0] if not x[0].isdigit() else "km from data median"
            key = {"nights": "too few nights", "night": "night share too low", "no": x}.get(key, key)
            reasons[key] = reasons.get(key, 0) + 1

    def q(vals):
        vals = sorted(v for v in vals if v is not None)
        return f"median {statistics.median(vals):.2f}, min {vals[0]:.2f}, max {vals[-1]:.2f}" if vals else "-"

    lines = ["# GeoLife home ground-truth quality", "",
             f"Thresholds (fixed before this run): nights >= {staypoints.MIN_NIGHTS}, night share >= "
             f"{staypoints.MIN_NIGHT_SHARE}, distance to data median <= {staypoints.MAX_DIST_MEDIAN_KM} km.", "",
             f"- persons: {len(rows)}; passed: {len(ok)}; failed: {len(rows) - len(ok)}",
             f"- failures by check (a person can fail several): "
             + ", ".join(f"{k} {v}" for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])),
             f"- night share: {q(r.get('night_share') for r in rows)}",
             f"- distance to data median (km): {q(r.get('dist_median_km') for r in rows)}",
             f"- nights at home cluster: {q(r.get('nights') for r in rows)}", "",
             "| person | members | points | nights | night share | 2nd share | km to median | result |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['person']} | {len(r['members'])} | {r['n_points']:,} | {r.get('nights', '-')} | "
                     f"{r.get('night_share', '-')} | {r.get('second_share', '-')} | {r.get('dist_median_km', '-')} | "
                     f"{'pass' if r['passed'] else 'FAIL: ' + '; '.join(r['reasons'])} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    out = a.out or ROOT / "results" / f"{dt.date.today():%Y%m%d}_home_quality"
    out.mkdir(parents=True, exist_ok=True)
    rows = assess_all(log=lambda m: print(m, file=sys.stderr, flush=True))
    (out / "home_quality.json").write_text(json.dumps(rows, indent=1, default=str))
    md = report_md(rows)
    (out / "report.md").write_text(md)
    print("\n".join(md.splitlines()[:10]))
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
