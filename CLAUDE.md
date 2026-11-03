# CLAUDE.md - instructions for Claude Code in this repository

## Engineering protocol (binding for every coding task)
Follow @docs/engineering_protocol.md: formulate first (objective, hard/soft constraints,
Gherkin acceptance criteria, verification tier), enforce quality through deterministic
gates, run the role pipeline, and end with a verification report. The conventions below
win on any conflict.

## What this is
Data and code of the VN2 Inventory Planning Challenge (Vandeput, 2025;
https://supchains.com/vn2-inventory-competition/), and the ordering policy we build for it.
599 Store x Product rows, six weekly orders, lead time 2 weeks, lost sales,
holding 0.2 EUR per unit per week, shortage 1 EUR per lost unit. Score = cost of weeks 3 to 8.
See `README.md` for the full rules.

## Commands
```bash
python vn2_play.py vn2_benchmark.py   # must print a setup of 913.8 EUR and a score of 4,334.0 EUR
python vn2_play.py <policy>.py        # replay the six rounds with a policy and print its score
python vn2_simulate.py "<folder>"     # score six order files
ruff check .                          # lint gate: complexity <= 10, <= 40 statements per function
python -m pytest                      # all hard-rule tests + coverage gate (85 % on vn2/)
python scripts/final_score.py <policy>.py   # the final exam: committed code only, every run logged
```

## Layout
- `vn2/`: our package. `vn2/data.py::as_of(cutoff)` is the only way to read the data.
- `scripts/`: entry points. Only `scripts/final_score.py` may touch the weeks 1-8 demand.
- `tests/`: the gates. `tests/official_manifest.sha256` freezes the official files.
- `results/final_runs.csv`: the log of every final run (commit it after each run).

## Conventions (do not break)
- **The official files are the oracle.** `vn2_simulate.py`, `vn2_play.py`,
  `vn2_benchmark.py`, `README.md` and everything in `Data/` stay as published. Never edit them to
  make a result look better.
- **No look-ahead.** A policy may use only what `vn2_play.py` hands it before a round.
  Tuning and validation use past weeks only (e.g. replays that end before 2024-04-08);
  the weeks 1 to 8 scored by the competition are the final test, not a training set.
- **Report the score honestly**, with the benchmark (4,334.0) and the winner (3,763.2)
  beside it.
- **Hard rules H1-H11** in `docs/project_plan.md` §3 (official files frozen, no look-ahead,
  test-set lock, provenance, solver checked against an exact oracle, honest reporting) are
  hard constraints. Each one is enforced by a test; never weaken or skip such a test.
- **Tools:** forecasts come from t0-gamma (`docs/t0_gamma_guide.md`), orders from the Seeker
  solver. Both run on the user's machine; Claude writes the scripts and reads the outputs.
- Never commit the Seeker licence (`*.sio`) or the Seeker manuals (licensed material).
- `Orders - */` folders are run output and stay out of git.

## Workflow
- Work on a branch and open a pull request; do not push directly to `main`.
- Update the docs in `docs/` when behaviour or outputs change (`README.md` is the official
  competition README and stays frozen).
- Changes to anything in `tests/` or to the gate settings in `pyproject.toml` and CI are
  listed explicitly in the pull request, so a human can check that no gate was weakened.
