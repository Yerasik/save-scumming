# `dp/` — Daniel (Vu Q. Nguyen)

Finite-horizon DP from the project plan (`V`, `W`, `N`), known and Beta odds. Reads any session JSON and writes a `policy.json` that `sim/policy.py` loads unchanged.

## Commands

From the repository root:

```
python -B -m dp.solve data/synthetic --out dp/out            # one policy per session
python -B -m dp.plot_policy data/synthetic --out dp/out/figures   # needs matplotlib
python -B -m unittest discover -s dp -p 'test_*.py' -v
python -B -m dp.h5_recheck --seeds 10000      # H5 recheck -> dp/out/h5_recheck.csv (~1 min)
python -B -m dp.report_figure                 # report figure -> dp/out/figures/report_policy_map.png / .pdf
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
3. **H5 file cannot test H5.** DP never retries the Beta(1, 49) event (`c = 60 s`), so a retry cap and retry-until-success behave the same under DP. Needs a cheaper retry or a more optimistic prior. *(Fixed: the four sessions in `experiments/sessions/H5/` use a 20 s retry. See the H5 recheck below.)*

## H5 recheck after the Beta simulator (11 Nov)

**Policies are right.** Re-solving the four H5 sessions gives byte-identical `policy.json` files to the ones in `dp/out/`. With the Beta sim (one latent `p` drawn per seed), the simulated DP mean matches the exact `expected_value` in every session, 10,000 seeds:

| Session | DP exact | DP in sim | z |
|---|---|---|---|
| known p = 0.02 | 152.96 | 153.78 ± 0.71 | +1.17 |
| Beta(20, 980) | 151.32 | 151.61 ± 0.71 | +0.41 |
| Beta(1, 49) | 133.40 | 134.06 ± 0.70 | +0.94 |
| Beta(0.2, 9.8) | 113.93 | 114.06 ± 0.57 | +0.23 |

**The sim's `fixed_k` caps are not a fair H5 test.** `fixed_k_N` allows N attempts on *every* event. At p = 0.02 (and 0.05 on the later event) a 2–5 attempt cap barely uses the 30-minute budget, so it scores 13–32 against ~150 and loses for a reason that has nothing to do with uncertainty. `dp/h5_recheck.py` instead caps only `rare_drop` (keeping travel time to the next event) and lets the later event retry until success, then sweeps the cap from 1 to 90 attempts.

| Session | always | best cap on rare_drop | cap − always (paired SE) | DP |
|---|---|---|---|---|
| known p = 0.02 | 152.01 | 153.78 (75 attempts) | +1.77 (0.26) | 153.78 |
| Beta(20, 980) | 149.07 | 151.60 (75) | +2.53 (0.27) | 151.61 |
| Beta(1, 49) | 118.06 | 133.63 (60) | +15.57 (0.49) | 134.06 |
| Beta(0.2, 9.8) | 69.38 | 114.08 (30) | +44.70 (0.65) | 114.06 |

What this means for the report:

- **H5's main claim holds, strongly.** Under uncertain odds a sensible cap beats retry-until-success, and the gap grows from +2.5 to +44.7 as the prior gets vaguer. The best cap also shrinks (75 → 60 → 30 attempts), which matches where the DP gives up (see the figure).
- **The "but not under known odds" half does not hold as built.** Even with known p, a 75-attempt cap beats `always` by +1.8 (7 SE). That comes from the later event competing for time (H3), not from uncertainty: `always` keeps reloading the rare drop until the clock forces it out. Suggested wording: *a cap helps a little under known odds because of the later event, and a lot under uncertain odds; the extra gain (+15.6 and +44.7 vs +1.8) is the uncertainty effect.*
- **The best fixed cap is as good as the DP here** (within 0.5). For one uncertain event, "stop after N rolls" is enough if N is chosen well; the DP's value is that it finds N for you, and that N depends on how unsure you are.

The report H5 figure is `analysis/experiment_h5_chart.png`, built from this CSV:

```
python -B analysis/analyze_h5.py
```

## Report figure

`dp/out/figures/report_policy_map.png` (`.pdf` for LaTeX). One panel per H5 session: x is failed rolls so far, y is seconds left, blue is "reload", grey is "accept and move on", and the black line is the path from a full budget. The DP gives up after 76 / 73 / 55 / 34 rolls as the prior weakens, with the same 2% mean in every panel. The thin stripes near the bottom are real: rare-drop retries cost 20 s and later-event retries 30 s, so whether one more reload eats a whole later retry flips every 20 s.
