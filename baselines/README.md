# Reward-per-second baseline

`rho_baseline.py` implements the Section 2.3 threshold rule:

```text
retry iff q(k) * (good_reward - bad_reward) + retained_failure_reward
          >= rho * retry_seconds
```

For documented odds, `q(k) = p`.  For uncertain odds with a Beta prior,
`q(k) = alpha / (alpha + beta + k)` after `k` failures.
The count includes failures already observed at the current decision; a caller
must pass the correct per-event count. The CLI applies `--failures` to every
Beta event (this fixture has just one); known odds remain unchanged.

Example using the two-event toy session:

```bash
python baselines/rho_baseline.py \
  data/synthetic/toy/toy_2_event_T180.json \
  --rho 0.10 \
  --csv baselines/toy_rho_0p10.csv
```

The toy marginal rates are:

- E1: `0.1 * (10 - 0) / 20 = 0.05` reward/second, so accept at
  `rho = 0.10`.
- E2: `0.5 * (8 - 0) / 10 = 0.40` reward/second, so retry at
  `rho = 0.10`.

`rho` represents the value of a second spent elsewhere.  It can be supplied
externally as above.  For a known-odds session, it can also be solved
self-consistently by maximising expected reward divided by expected time:

```bash
python baselines/rho_baseline.py \
  data/synthetic/experiment_A_budget/A_budget_T030min.json \
  --solve \
  --csv baselines/base_session_rho_policy.csv
```

The solver compares `never_retry` with `retry_until_success` independently at
each event and uses Dinkelbach iterations to find the resulting session rate.
Mandatory first-attempt rewards and travel times are included.  Because the
current model does not record the duration of a first attempt separately, use
`--fixed-seconds` if the real case study later supplies additional unavoidable
session time.  Do not estimate rho from the finite-budget DP result; that would
make the baseline circular.

This is an unlimited-time reward-rate baseline, not the finite-budget optimal
policy. A simulator must also refuse a retry when `retry_seconds` exceeds the
remaining budget. The rho rule alone does not enforce time feasibility or
reserve enough time for later events.

## CSV contract

Every generated rho CSV adds `session_id` while preserving all original
column names:

```text
session_id,event_id,failures,probability,marginal_reward,retry_seconds,reward_per_second,rho,action
```

`--solve` retains its two extra columns:
`expected_extra_reward_until_success` and
`expected_extra_seconds_until_success`. The CLI obtains `session_id` from
the JSON; Python callers using `evaluate` or `solve_self_consistent_rho`
should pass `session_id=payload["session_id"]` before exporting rows.

## Uncertain-odds example

```bash
python baselines/rho_baseline.py \
  data/synthetic/uncertain_odds/uncertain_beta_a1_b49_T030min.json \
  --rho 0.006 --failures 0 --csv baselines/beta_rho_prior.csv
python baselines/rho_baseline.py \
  data/synthetic/uncertain_odds/uncertain_beta_a1_b49_T030min.json \
  --rho 0.006 --failures 50 --csv baselines/beta_rho_50_failures.csv
```

Here 0.006 is an illustrative external threshold, not a measured PoE rate.
For E3, the rule changes from retry to accept as the posterior mean falls.
The loader branches on `odds_type`; it never requires `p` for a Beta event.
`--solve` rejects uncertain-odds sessions rather than pretending a prior mean
is a known fixed probability.

## Reproducibility checks

```bash
python -B -m unittest discover -s baselines -p 'test_*.py' -v
```

All code uses Python 3.10+ and the standard library, with docstrings and
comments explaining the model, experiment controls, and output contracts.

The Path of Exile H5 snapshot is intentionally not fabricated here.  Once the
team fixes a date, league, item targets, source, and currency unit, those data
can be added as a separate dated input and evaluated by this same module.
