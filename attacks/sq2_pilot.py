"""SQ2 PILOT: does the end-to-end attack pipeline run? (GeoLife -> home ground truth -> original / rotated control
-> grid cloaking -> LLM and baseline home inference -> error in metres.)

LM Studio prototyping run: outputs are NOT paper data (PLAN.md, decisions).
Usage (from the code folder): python -m attacks.sq2_pilot --model <lmstudio id> --users 10
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import statistics
import sys
import time
from pathlib import Path

from attacks.home_inference import baseline_home, build_prompt, parse_latlon, segments, shown_segments
from controls.geometric import Rotation
from data_io import geolife, user_groups
from data_io.geo import haversine_m
from data_io.staypoints import assess_home, detect_stays
from llm import lmstudio
from mechanisms.cloaking import GridCloak

ROOT = Path(__file__).resolve().parents[1]


def pick_users(n: int, min_points: int, log, max_members: int | None = None) -> list[tuple[str, list, tuple[float, float]]]:
    """The first n persons (user groups) with enough points and a home that passes the quality checks."""
    picked = []
    for gid, members in user_groups.load().items():
        if max_members and len(members) > max_members:
            log(f"group {gid}: {len(members)} members, skipped (--max-members {max_members})")
            continue
        pts = geolife.load_group(members)
        if len(pts) < min_points:
            continue
        a = assess_home(pts, detect_stays(pts))
        log(f"group {gid} ({'+'.join(members)}): {len(pts)} points, home "
            f"{'passed' if a.passed else 'FAILED: ' + '; '.join(a.reasons)}")
        if a.passed:
            picked.append((gid, pts, a.home))
        if len(picked) == n:
            break
    return picked


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True, help="model identifier loaded in LM Studio")
    ap.add_argument("--users", type=int, default=10, help="number of persons (user groups)")
    ap.add_argument("--max-members", type=int, default=None, help="skip groups with more member users")
    ap.add_argument("--min-points", type=int, default=20000)
    ap.add_argument("--cell", type=float, default=500)
    ap.add_argument("--max-lines", type=int, default=250)
    ap.add_argument("--hit-m", type=float, default=1000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--suffix", default=" /no_think", help="appended to the prompt (Qwen3: disable thinking)")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)

    out = a.out or ROOT / "results" / f"{dt.date.today():%Y%m%d}_sq2_pilot_{a.model.replace('/', '_')}"
    out.mkdir(parents=True, exist_ok=True)
    log = lambda m: print(m, file=sys.stderr, flush=True)
    rng = random.Random(a.seed)
    cloak = GridCloak(a.cell)
    records = []

    for user, pts, home in pick_users(a.users, a.min_points, log, a.max_members):
        angle = rng.uniform(90, 270)
        rot = Rotation.about_centroid(pts, angle)
        cloaked = cloak.apply(pts)
        # Control = the protected output, rotated (cloak first, then rotate): both variants have exactly the same
        # segments and timing and differ only in coordinates, so task difficulty is held constant (N2).
        variants = {"original": (cloaked, home), "control": (rot.points(cloaked), rot.latlon(*home))}
        for name, (vp, vhome) in variants.items():
            segs = shown_segments(segments(vp), max_lines=a.max_lines)
            prompt = build_prompt(segs, a.cell, a.suffix)
            t0 = time.time()
            try:
                resp = lmstudio.chat(a.model, prompt, max_tokens=300)
                err = None
            except Exception as exc:  # record and continue: the pilot is about whether the pipeline runs
                resp, err = {"text": "", "usage": {}}, f"{type(exc).__name__}: {exc}"
            pred = parse_latlon(resp["text"])
            base = baseline_home(segs)
            rec = {
                "user": user, "variant": name, "angle_deg": round(angle, 1) if name == "control" else 0.0,
                "n_points": len(vp), "n_segments_shown": len(segs), "prompt_tokens": resp["usage"].get("prompt_tokens"),
                "latency_s": round(time.time() - t0, 1), "error": err, "raw": resp["text"][:500],
                "pred": pred, "err_m": round(haversine_m(*pred, *vhome)) if pred else None,
                "baseline": base, "baseline_err_m": round(haversine_m(*base, *vhome)) if base else None,
            }
            rec["hit"] = rec["err_m"] is not None and rec["err_m"] <= a.hit_m
            rec["baseline_hit"] = rec["baseline_err_m"] is not None and rec["baseline_err_m"] <= a.hit_m
            records.append(rec)
            log(f"  {user} {name}: llm err {rec['err_m']} m, baseline err {rec['baseline_err_m']} m, "
                f"{rec['prompt_tokens']} prompt tokens, {rec['latency_s']} s")

    (out / "records.jsonl").write_text("".join(json.dumps(r, default=str) + "\n" for r in records))
    failed = sum(1 for r in records if r["error"])
    lines = [f"> ⚠️ {failed}/{len(records)} LLM calls failed (see `error` in records.jsonl); LLM columns are not "
             "valid for those rows.", ""] if failed else []
    lines += [f"# SQ2 pilot ({a.model}) - LM Studio prototyping, NOT paper data", "",
             f"cell {a.cell:.0f} m, hit <= {a.hit_m:.0f} m, max {a.max_lines} segments shown, seed {a.seed}", "",
             "| variant | n | LLM parsed | LLM hits | LLM median err (m) | baseline hits | baseline median err (m) |",
             "|---|---|---|---|---|---|---|"]
    for name in ("original", "control"):
        rs = [r for r in records if r["variant"] == name]
        e = [r["err_m"] for r in rs if r["err_m"] is not None]
        b = [r["baseline_err_m"] for r in rs if r["baseline_err_m"] is not None]
        lines.append(f"| {name} | {len(rs)} | {len(e)} | {sum(r['hit'] for r in rs)} | "
                     f"{statistics.median(e) if e else '-'} | {sum(r['baseline_hit'] for r in rs)} | "
                     f"{statistics.median(b) if b else '-'} |")
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwritten: {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
