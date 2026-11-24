# Auditing privacy claims on public trajectory benchmarks in the LLM era

Code for Paper 6: (1) contamination tests of open-weight LLMs on GeoLife and T-Drive, (2) LLM attacks on
non-DP protected trajectories with matched controls, (3) empirical epsilon auditing of DP trajectory mechanisms.

Status: skeleton only. The work plan and open decisions are in [PLAN.md](PLAN.md); models are in
[configs/models.yaml](configs/models.yaml).

| Folder | Purpose |
|---|---|
| `data_io/` | GeoLife / T-Drive loaders, cleaning, stay points, fixed subsets |
| `serialize/` | trajectories as text (original and neutral formats) |
| `controls/` | statistics-preserving geometric controls |
| `llm/` | transformers runner (generation + log-probabilities) |
| `contamination/` | SQ1 tests |
| `mechanisms/` | non-DP mechanisms and DP wrappers |
| `attacks/` | SQ2 attacks |
| `audit/` | SQ3 epsilon auditing |
| `analysis/` | statistics, tables, figures |
| `configs/`, `results/`, `tests/` | run configs, dated outputs, unit tests |

Datasets live in `data/` and are not tracked. Only public datasets are used; no re-identification outputs are released.

Tests (from this folder): `python -m unittest discover -s tests -t .`
