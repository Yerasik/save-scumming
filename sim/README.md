# `sim/` — Yera (Yerassyl Taisarinov)

Play a session event by event. Spend time. Follow a named strategy. Roll the dice.

## Strategies

- `never`
- `always`
- `fixed_k` with `k = 2, 3, 5`
- `reward_greedy`
- `efficiency_greedy`
- `dp` — read `policy.json`, do **not** re-solve the DP

## Rules

- At least 10,000 sessions per strategy
- **Same seeds** across strategies
- Check: for a simple geometric wait, mean tries should sit near `1/p`

## Writes

`sessions.csv` with columns:

`session_id`, `experiment`, `strategy`, `seed`, `reward`, `reloads`, `time_reloading`

## Done when

One command plus a seed list produces a CSV that `analysis/` can plot without extra explanation.
