# Synthetic event sequences

This directory contains deterministic input sessions for the dynamic program
and Monte Carlo simulator.  These are **parameters**, not simulated results.
Run the generator from the repository root:

```bash
python data/synthetic/generate_synthetic.py
```

## Schema

The shared interface is frozen: `session_id`, `experiment`, `budget_seconds`,
and `events` will not be renamed. Each event keeps `good_reward`, `bad_reward`,
`retry_seconds`, and `travel_seconds`. Known-odds events also contain `p`.
Additional metadata does not replace these fields.

Event fields match the project plan:

- `p`: success probability per attempt, present for known odds only.
- `good_reward`, `bad_reward`: rewards `g_i` and `b_i`.
- `retry_seconds`: retry/replay cost `c_i`.
- `travel_seconds`: travel time `f_i` to the next event.
- `entry_cost`: event entry cost `e_i` (zero in these save-scumming inputs).
- `retained_failure_reward`: retained failure value `h_i` (zero here).

The final event always has `travel_seconds = 0`.

For `odds_type: "beta"`, use `alpha` and `beta` instead of `p`.
Do not add a made-up `p`, even if the prior mean can be calculated. A loader
must check `odds_type` before reading probability fields:

```python
# Default supports older known-odds inputs that do not include odds_type.
if event.get("odds_type", "known") == "beta":
    q = event["alpha"] / (event["alpha"] + event["beta"] + failures)
else:
    q = event["p"]
```

Here `failures` counts observations already incorporated at this decision.
For a simulation, draw one latent probability per Beta event/run, then use
that fixed probability for its attempts. Do not redraw the latent probability
independently on each retry; that would erase learning about the event.

## Included sets

- `toy/`: exact two-event instance from the plan (`T=180`, `p1=0.1`,
  `p2=0.5`). Unspecified toy travel times default to zero.
  Use this first for DP/simulator sanity checks.
- `experiment_A_budget/`: the same eight events under 10, 20, 30, 60, and
  120 minute budgets.
- `experiment_C_retry_cost/`: a 30-minute session with **only E3's** retry
  time set to 5, 20, 60, or 120 seconds. Every other event field stays fixed.
- `experiment_D_future_opportunity/`: a fixed early target with a later event
  removed or assigned reward 8, 20, 40, or 80.  This is the headline
  future-opportunity comparison.
- `experiment_B_probability/`: the same eight-event session while only E3's
  probability varies from 0.01 to 0.90.
- `uncertain_odds/`: one additional eight-event session. E3 uses Beta(1,49)
  and deliberately omits `p`; its prior mean is 0.02, falling to 0.01 after
  50 failures. All other events retain known odds. This is not a PoE snapshot.

There are 24 sessions (1 toy, 5 A, 4 C, 5 D, 8 B, 1 uncertain).
`manifest.json` lists every generated session and is the recommended entry
point for an experiment runner.

## Dummy plotting data: not findings

`dummy_sessions.csv` contains 40 **fabricated** plotting-fixture rows, with
exactly these columns:

```text
session_id,experiment,strategy,seed,reward,reloads,time_reloading
```

Two sessions (A and C), four strategy labels, and five seeds per group let
Yusif build grouped means and confidence intervals. Time is in seconds.
The four labels are `never_reload`, `always_reload`, `fixed_retry_3`, and `rho`.
These labels and arbitrary values do not show actual policy performance;
there is no simulator behind them. Never report these rows or their confidence
intervals as project findings. The sidecar `dummy_sessions.metadata.json`
records this provenance without changing the requested CSV columns.

Regenerating the inputs also regenerates the dummy CSV deterministically.

## Design choices

All non-toy sessions contain 5-8 events.  Each experiment changes one named
factor and leaves the remaining fields fixed.  The values are intentionally
synthetic and must not be presented as Pokemon or Path of Exile measurements.
The D removal variant also removes that event's travel time; the surviving
events are unchanged. No early-decision flip or policy ranking is claimed
until the team's DP/simulator has actually evaluated these inputs.

## Checks

From the repository root (Python 3.10+, standard library only):

```bash
python -B -m unittest discover -s baselines -p 'test_*.py' -v
```

The local `.gitignore` ignores bytecode, so no `__pycache__` should be committed.
