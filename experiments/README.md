# `experiments/` — Roy (Jihun Choi)

One config per experiment. Each changes **one** named factor (PLAN.md section 4).

| Config | Factor | Sessions | Question |
|---|---|---|---|
| `configs/toy.json` | none | toy, T = 180 s | Do DP and the simulator agree? |
| `configs/A_budget.json` | `budget_seconds` 10–120 min | `data/synthetic/experiment_A_budget/` | When does DP beat simple rules? (H1) |
| `configs/B_probability.json` | `p` on one event, 0.01–0.90 | `data/synthetic/experiment_B_probability/` | How rare before reloading stops paying? |
| `configs/C_retry_cost.json` | `retry_seconds` on E3 only, 5–120 s | `data/synthetic/experiment_C_retry_cost/` | Does cost alone flip accept vs retry? |
| `configs/D_future_opportunity.json` | later event's `good_reward` | `experiments/sessions/D/` (**v2**) | Does a later prize stop the early reload? (H3) |
| `configs/H5_uncertain_odds.json` | prior on the rare drop | `experiments/sessions/H5/` (**v2**) | Can a retry cap beat retry-until-success? (H5) |
| `configs/pokemon.json` | none | `data/pokemon/pokemon_sv_main.json` | Does DP beat simple habits on the real SV route? |
| `configs/poe.json` | none | `data/poe/poe_exarch_beta.json` | Same 2% mean as H5, as a PoE-named contrast |

## Commands

From the repository root (Python 3.10+, standard library only):

```
python -B experiments/run_experiment.py experiments/configs/A_budget.json
python -B experiments/run_experiment.py experiments/configs/D_future_opportunity.json
python -B experiments/run_experiment.py experiments/configs/pokemon.json
python -B experiments/run_experiment.py experiments/configs/poe.json
python -B experiments/make_sessions.py                      # rebuild D v2 and H5 v2
python -B -m unittest discover -s experiments -p 'test_*.py' -v
```

`run_experiment.py` writes `dp/out/<session_id>.policy.json` and `sim/out/<experiment>/<session_id>.csv` (all strategies, seeds `0 .. N-1`). `--seeds 2000` for a quick run.

## Why D and H5 were rebuilt

Daniel's DP check (`dp/README.md`, findings 2 and 3):

- **Old D** — later event at `p = 0.5`, `c = 10 s` was nearly always won in a few retries, so raising its value from 8 to 80 never changed the early policy. **D v2** keeps the toy's early event (`p = 0.1`, `g = 10`, `c = 20 s`) and makes the later event rare and slow (`p = 0.05`, `c = 30 s`), budget 600 s. Only the later `good_reward` changes: removed, 10, 20, 40, 80, 160.
- **Old H5** — Beta(1, 49) event cost 60 s per retry, so DP never retried it. **H5 v2** uses a 20 s retry and four priors with the same mean (0.02): known, Beta(20, 980), Beta(1, 49), Beta(0.2, 9.8). A later known event competes for time.

DP retries of the early / rare event from a full budget (`test_experiments.py` locks these in):

| D v2 later reward | removed | 10 | 20 | 40 | 80 | 160 |
|---|---|---|---|---|---|---|
| early retries | 30 | 30 | 30 | 18 | **0** | **0** |

| H5 v2 prior | known 0.02 | Beta(20, 980) | Beta(1, 49) | Beta(0.2, 9.8) |
|---|---|---|---|---|
| rare-drop retries | 75 | 72 | 54 | 33 |

Note: under a Beta prior DP has no hard cap. The posterior mean falls like `1/k`, so DP stops earlier the weaker the prior, but with more time it keeps going. The simulator draws one latent `p` per seed from the prior and keeps it on retries.

## Preliminary results (1 Nov, 10,000 seeds, mean reward ± 95% CI)

Synthetic sessions only. Not Pokémon data.

**Experiment A (H1).** DP minus the best simple rule, paired by seed:

| Budget | Best simple rule | DP | Best simple | DP − best |
|---|---|---|---|---|
| 10 min | efficiency_greedy | 67.0 ± 0.5 | 66.9 ± 0.5 | 0.1 ± 0.2 |
| 20 min | efficiency_greedy | 91.5 ± 0.5 | 82.8 ± 0.3 | 8.6 ± 0.5 |
| 30 min | fixed_k_5 | 107.5 ± 0.6 | 88.7 ± 0.6 | **18.7 ± 0.6** |
| 60 min | always | 137.9 ± 0.7 | 127.8 ± 1.0 | 10.1 ± 0.5 |
| 120 min | always | 158.5 ± 0.4 | 156.4 ± 0.5 | 2.1 ± 0.2 |

DP's edge peaks at moderate pressure and is near zero at both ends. That is what H1 predicts. The best simple rule also changes with the budget (efficiency-greedy when tight, always-reload when loose), which is the practical point for players.

**Experiment D v2 (H3).**

| Later reward | removed | 10 | 20 | 40 | 80 | 160 |
|---|---|---|---|---|---|---|
| DP | 9.6 | 14.5 | 19.4 | 29.2 | 52.7 | 104.2 |
| Always reload | 9.6 | 14.5 | 19.4 | 29.1 | 48.5 | 87.4 |
| Reward-greedy | 9.6 | 10.0 | 14.0 | 26.9 | 52.7 | 104.2 |

Once the later prize is worth 80 or more, DP stops reloading the early event and always-reload loses 4.2 (80) and 16.8 (160). No single simple rule matches DP across the sweep: always-reload is right when the later prize is small, reward-greedy when it is large. DP switches between them by itself.

**Pokémon SV main (known p = 0.08, 10,000 seeds).** Policy `dp/out/pokemon_sv_main.policy.json`, CSV `sim/out/pokemon/pokemon_sv_main.csv`. Mean reward ± 95% CI:

| Strategy | Mean |
|---|---|
| DP | 56.36 ± 0.53 |
| Always reload | 56.36 ± 0.53 |
| Fixed-k = 5 | 33.84 ± 0.47 |
| Reward-greedy | 32.00 ± 0.29 |
| Never / efficiency-greedy | 8.14 ± 0.27 |

DP equals always-reload. Same odds and similar reward-per-second on every shrine, so the simple habit is already optimal (H1 near-zero).

**PoE Exarch Beta(1, 49) contrast (10,000 seeds).** Session `data/poe/poe_exarch_beta.json` (2% mean from the dated snapshot; timings match H5 v2, not PoE footage). Policy `dp/out/poe_exarch_beta.policy.json`, CSV `sim/out/poe/poe_exarch_beta.csv`.

| Strategy | Mean |
|---|---|
| DP | 133.64 ± 1.37 |
| Always reload | 118.03 ± 1.79 |
| Efficiency-greedy | 119.11 ± 1.78 |
| Reward-greedy | 69.97 ± 1.03 |
| Fixed-k = 5 (every event) | 31.32 ± 1.00 |
| Never | 6.91 ± 0.51 |

DP beats always-reload by about 15.6. That is the H5 story on PoE names. `fixed_k_5` here caps **every** event, so it is not a fair H5 test; use `dp/out/h5_recheck.csv` for caps on the rare drop only.
