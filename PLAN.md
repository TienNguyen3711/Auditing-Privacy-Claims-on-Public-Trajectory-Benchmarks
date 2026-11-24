# Paper 6 codebase plan

Source of the design: `Material/Auditing Privacy Claims on Public Trajectory Benchmarks in the LLM Era.docx`
(package `Material/_reading/auditing_privacy_claims_on_public_trajectory_benchmarks_in_the_llm_era/`).
Section numbers (§) and SQ1-SQ4 / N1-N5 refer to that document.

## Decisions (2026-11-24)
- New git repository for Paper 6 (the old `.git` was a copy of Paper 5's repo; its history lives in Paper 5).
- LLMs run locally with Hugging Face `transformers` (log-probabilities are needed for Min-K% and CoDeC).
- Models (`configs/models.yaml`): OLMo 2 13B, Llama 3.1 8B, Gemma 3 12B, Qwen3 14B; base + instruct each.
- LM Studio vs transformers (tested 2026-11-24 on the local LM Studio server with Qwen3 4B):
  `/v1/completions` returns `"logprobs": null` and ignores `echo`; `/v1/chat/completions` returns log-probabilities
  for generated tokens only. LM Studio therefore cannot score given text, so Min-K% and CoDeC must run in transformers.
- All reported numbers (SQ1-SQ4) come from transformers on the same pinned bf16 checkpoints. Reason: LM Studio serves
  third-party GGUF/MLX quantisations (often 4-8 bit) that may memorise differently, may lack base variants, and cannot be
  pinned to the original Hugging Face revision; SQ2 interprets attacker success through SQ1 contamination, so both must
  use the same weights. LM Studio is used only to prototype SQ2 attacker prompts; its outputs never enter the paper.

## Step 0: open items before experiments
- [ ] Approve and run the model downloads (Llama and Gemma: accept the Hugging Face licences first); pin revisions.
- [ ] Create the Python environment from `requirements.txt` and pin versions.
- [ ] Training cutoff of OLMo 2 13B; check Meta's own Llama 3.1 card; Qwen3 cutoff has no official source.
- [ ] Proposal inconsistency: main RQ says "two DP, two non-DP", Scope says "2-3 DP". Decide.
- [ ] Post-cutoff controls (§5.2 ii): every local dataset predates all four cutoffs (GeoLife, T-Drive 2008; Foursquare 2012-13; Porto; Gowalla). Find a post-cutoff mobility dataset or drop control (ii).
- [ ] Public code for the mechanisms: DPT, AdaTrace, LDPTrace (PrivTrace as fallback), a trajectory k-anonymity method. Pin commits.
- [ ] Missing sources: Min-K% (Shi et al., ICLR 2024), Adversary Instantiation (Nasr et al., S&P 2021), Li 2026 (agentic deanonymizers), "The long road to trajectory privacy" (2025); replace the two mis-saved PDFs ("What is the Cost of DP...", "A Dual Perspective...").
- [ ] Optional, needs approval (sends public dataset strings to an external API): infini-gram lookup of GeoLife/T-Drive strings in Pile, Dolma and OLMo-mix-1124.

## Data on disk (`data/`, git-ignored)
- GeoLife 1.3: 182 users, 18,670 `.plt` files (6 header lines, then `lat,lon,0,alt_ft,days,date,time`).
- T-Drive: 10,357 taxi files (`id,datetime,lon,lat`; note lon before lat).

## 1. Shared infrastructure
- [ ] `data_io`: loaders, cleaning (Beijing bounding box, speed filter, duplicates), trip segmentation, stay points, seeded subsets with a hash manifest.
- [ ] `serialize`: original formats and neutral formats.
- [ ] `controls`: translation / rotation, tests that statistics are preserved, plausibility check.
- [ ] `llm`: generation + per-token log-probabilities, cache, seeds, model metadata in every result.
- [ ] Experiment configs in `configs/`, dated outputs in `results/`, offline unit tests in `tests/`.

## 2. Phase 1, SQ1: contamination (`contamination/`)
- [ ] Row completion from random starts; exact line match, haversine error (m), timestamp match; original vs control.
- [ ] Min-K% prob and CoDeC on the same pairs.
- [ ] Format vs coordinate memorisation (PLT header lines vs coordinate lines).
- [ ] Paired permutation / bootstrap tests, multiple-comparison correction.
- [ ] Pilot: one model, about 200 snippets, to size runtime and effect before the full run.

## 3. Phase 2, SQ2: attacks on non-DP protection (`mechanisms/`, `attacks/`, `analysis/`)
- [ ] Spatial cloaking (grid generalisation) and trajectory k-anonymity.
- [ ] LLM home/work inference (hit = within r m of the stay point) and trajectory-user linking; classical baselines.
- [ ] Mixed-effects logistic regression, random effect per user; report a difference, not a causal effect.
- Pilot 2026-11-24 (`results/20261124_sq2_pilot_pilot-qwen3-4b/`, Qwen3 4B on LM Studio, 10 users, NOT paper data):
  the pipeline runs end to end (20/20 calls, 20/20 answers parsed, about 2.5 min). Two design issues found:
  - [x] Rotating before cloaking changes which points share a grid cell, so original and control can differ in the
    records shown (e.g. user 001: 210 vs 196 segments). Fixed (approved 2026-11-24): cloak first, then rotate the
    cloaked output. Rerun `results/20261124_sq2_pilot_v2_cloak_then_rotate/`: prompt token counts now identical for
    every original/control pair; the baseline error is identical for every pair.
  - [x] Cross-user duplicate check added (`data_io/duplicates.py`). Full scan
    `results/20261124_geolife_duplicates/report.md`: 41 user pairs share identical raw (date, time, lat, lon) points,
    36 of them for >= 1% of either user (52 users involved); 821 PLT files are byte-identical across users. Several
    users are fully contained in another (e.g. 124 in 010, 070 in 013, 088 in 011, 127 in 012, 156 in 153, 109 in 101;
    055/075, 058/059, 069/129, 057/094/150 near-identical). A point held by three users is credited only to the pair
    with its first holder.
  - [x] Duplicate policy (a), approved 2026-11-24: users sharing at least one identical raw point are merged into
    one person (connected components; `data_io/user_groups.py` -> `configs/geolife_user_groups.json`,
    `geolife.load_group`). 182 users -> 144 persons; 17 groups have more than one user. At the >= 1% threshold it
    would be 147 persons. The unit for user-level adjacency (SQ3), trajectory-user linking and the per-person random
    effect is the group.
  - [ ] Group g056 has 19 users and 6,871,175 points (about 30% of all distinct points). It is the conservative unit
    for adjacency, but it is unlikely to be one person: its home ground truth is not a single home. Decide for SQ2
    home inference: exclude g056 (`--max-members`), or keep it only for SQ3.
  - [ ] Report the duplicate finding in the paper's data section (benchmark property, relevant to N1 and SQ3).
  - Pilot v3 on groups (`results/20261124_sq2_pilot_v3_user_groups/`, 4B model, 10 persons, 20/20 calls OK):
    LLM hits 5/10 original vs 8/10 control; baseline 8/10 both.
  - [x] Home ground-truth quality: g010 (= 010; 124 is contained in it) got a home on the southern edge of the Beijing box, about
    71 km from the cell every attacker picks. Cause: `detect_stays` let one stay span recording gaps of any length
    (two fixes 8 days apart became a 208 h stay with 64.5 night hours). Fixed: a stay never spans a gap > 36 h.
    Quality checks added (`staypoints.assess_home`, thresholds fixed before the run): nights >= 3, night share >= 0.5,
    home <= 30 km from the data median. Report `results/20261124_home_quality/report.md`: 58 of 144 persons pass
    (51 with >= 20,000 points); failures: too few nights 46, night share 25, no night stays 16, no points in the
    Beijing box 3, distance 1 (g010, which also fails night share 0.34). g056 fails night share (0.46), as expected
    for a 19-user group. Narrow failures: g007 0.496, g004 0.43 (3 merged users).
  - [ ] Decide whether 58 persons are enough for SQ2 or whether a threshold changes (any change must be decided
    before new SQ2 runs and recorded here). Pilots v1-v3 used the old stay rule and unfiltered homes; rerun.
  - Observation (4B model only): every LLM miss > 1 km was a cell listed in the prompt, mostly a frequently listed
    one (36-57 times), not the night-time cell. Prompt or model size, to revisit with the chosen models.

## 4. Phase 3, SQ3: epsilon auditing (`mechanisms/`, `audit/`)
- [ ] Uniform wrapper `run(dataset, epsilon, seed)` for 2-3 DP implementations.
- [ ] Neighbouring datasets: canary trajectory (trajectory level), one user removed (user level); LDPTrace needs a local-DP neighbour definition.
- [ ] Distinguisher score on the outputs; threshold chosen on held-out runs.
- [ ] Epsilon lower bound from Clopper-Pearson (95%) bounds on FPR / FNR, about 500-1000 runs per setting.
- [ ] Self-checks: correct Laplace reference gets close to its epsilon; a planted bug (doubled epsilon) is detected.
- [ ] Measure one run per mechanism before fixing N.

## 5. Phase 4, SQ4 (optional) and release
- [ ] LLM distinguisher on one reduced configuration.
- [ ] Toolkit release (N5): README, configs, tests; no re-identification outputs; responsible-disclosure procedure for SQ3 findings.

## Order
1. Step 0 and `data_io`.
2. In parallel: (a) SQ1 pilot with one model (decides whether SQ2 is worth running); (b) SQ3 audit harness with its two self-checks (no LLM needed).
3. Alongside the code: reading cards and `gaps.md` for `Material/`, to confirm N1-N5 and the gap in §2.3.

## Layout
```
data_io/  serialize/  controls/  llm/  contamination/  mechanisms/  attacks/  audit/  analysis/
configs/  results/  tests/  data/ (git-ignored)
```
