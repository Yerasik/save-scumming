# `dp/` — Daniel (Vu Q. Nguyen)

Finite-horizon DP from the project plan (`V`, `W`, `N`), known and Beta odds. Reads any session JSON and writes a `policy.json` that `sim/policy.py` loads unchanged.

## Commands

From the repository root:

```
python -B -m dp.solve data/synthetic --out dp/out            # one policy per session
python -B -m dp.plot_policy data/synthetic --out dp/out/figures   # needs matplotlib
python -B -m unittest discover -s dp -p 'test_*.py' -v
```

A single file works too: `python -B -m dp.solve data/synthetic/toy/toy_2_event_T180.json`.

Then play the policy in the simulator:

```
python -B -m sim.run --session data/synthetic/toy/toy_2_event_T180.json \
  --policy dp/out/toy_2_event_T180.policy.json --strategies dp,always,never --seeds 10000 --out sim/out/toy_dp.csv
```

## Policy file

`dp/out/<session_id>.policy.json`. Rules are first-match, as `sim/policy.py` reads them:

- per event, grouped by failure count (lowest first; known odds use one group with `max_failures = 1000000`)
- inside a group, `min_time_left` thresholds run high to low and cover every `t >= 0`
- `default_action` is `accept`

Extra keys (`solver`, `budget_seconds`, `expected_value`) are ignored by the loader. `expected_value` is `V(1, T, 0) - e_1`.

## Choices that follow the simulator, not the printed plan

- Retry is allowed when `time_left >= retry_seconds` (the plan prints `>`).
- Ties go to `accept`.
- Time is whole seconds; non-integer budgets, retry or travel times are rejected.

## Checks

- Simulator playing each DP policy for 20,000 seeds averages to `expected_value` on all 23 known-odds sessions (all within 2.5 SE; toy and D re-checked on 200k fresh seeds, within 1.3 SE).
- Toy, 20,000 seeds: DP 13.77 (exact 13.68), always 13.00, fixed-k=5 11.91, never 5.10.

## Findings for the team

1. **Toy.** The plan says DP "refuses a third retry on E1". It doesn't: DP retries E1 until fewer than 40 s are left. E2's first attempt is free and there is no travel, so E2 is never missed.
2. **Experiment D does not test H3 as built.** Adding the later event moves the early cutoff from 275 s to 325 s, but revaluing it from 8 to 80 changes nothing in the early policy: at `p = 0.5`, `c = 10` it is nearly always won within a few retries. The later event needs a low `p` (or high `c`) for its value to compete for time.
3. **H5 file cannot test H5.** DP never retries the Beta(1, 49) event (`c = 60 s`), so a retry cap and retry-until-success behave the same under DP. Needs a cheaper retry or a more optimistic prior.
