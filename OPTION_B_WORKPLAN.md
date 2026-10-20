# COMP1110 Save-Scumming — Option B work plan

Record of the agreed split: **5 equal GitHub modules**, one person, one folder. Everyone commits. Same workload on paper.

Project in one line: a Python prototype that says when to reload a bad roll under a limited playtime budget, then simulates that rule against simpler player habits. Not an app, not a live-game bot.

---

## 1. Who owns what

Each module talks to the others through shared files: `events.json` (session + event list), `policy.json` (later, from DP), `sessions.csv` (later, from the simulator).

| Person | Owns | Must commit |
|---|---|---|
| Daniel (Vu Q. Nguyen) | `dp/` | DP solver, policy map, Beta / uncertain-odds |
| Yera (Yerassyl Taisarinov) | `sim/` | Monte Carlo engine, parallel runner, shared seeds |
| Roy (Jihun Choi) | `data/pokemon/` + `experiments/` | Odds + timings, experiment configs A / C / D / B |
| Vivaan (Vivaan Kandhari) | `data/synthetic/` + `baselines/` | Synthetic generator, rho-rule, PoE snapshot |
| Yusif (Yusif Seyidov) | `analysis/` + repo glue | Plots, CIs, tests, README, CI so `main` always runs |

Pipeline:

1. Vivaan’s synthetic data (and later Roy’s Pokémon numbers) go in as JSON.
2. Daniel’s DP reads that JSON and writes a policy.
3. Yera’s simulator plays many sessions on shared seeds and writes a CSV.
4. Yusif’s analysis reads the CSV (and policies) and makes figures/tables.

Nobody waits for Pokémon. Synthetic data is enough to build DP, sim, and plots.

---

## 2. What we are building (shared picture)

Research question: in a sequence of random game events that share one finite real-time budget, when is retrying after a bad outcome worth the time it takes from later events?

- **Known odds (main):** Pokémon Scarlet/Violet — published reset odds, video timings. Nobody needs to own the game.
- **Uncertain odds (small extra):** Path of Exile-style farming in the simulator — community drop estimates, one dated price snapshot. No live scraping, no bots.

Code is a prototype for policies and simulation results, not a product.

---

## 3. Frozen JSON schema (do not rename)

Session object:

- `schema_version`
- `session_id`
- `description`
- `experiment` (`toy`, `A`, `B`, `C`, `D`, `H5`, …)
- `varied_factor`
- `varied_value`
- `budget_seconds`
- `events` (list)

Each event:

- `event_id`
- `odds_type`: `known` or `beta`
- `p` (if known)
- `alpha`, `beta` (if beta)
- `good_reward` (`g`)
- `bad_reward` (`b`)
- `retry_seconds` (`c`)
- `travel_seconds` (`f`)
- `entry_cost` (`e`, zero for save-scumming)
- `retained_failure_reward` (`h`, zero when a reload discards the bad result)

Last event: `travel_seconds = 0`.

Simulator output CSV (including Yusif’s dummy file) should use:

- `session_id`
- `experiment`
- `strategy`
- `seed`
- `reward`
- `reloads`
- `time_reloading`

Rho baseline CSV should keep:

- `session_id` (add this)
- `event_id`, `failures`, `probability`, `marginal_reward`, `retry_seconds`, `reward_per_second`, `rho`, `action`

---

## 4. Experiments the synthetic data must support

From the project plan. Each experiment changes **one** named factor.

- **Toy:** 2 events, `T = 180`. Event 1: `p = 0.1`, `g = 10`, `b = 0`, `c = 20`. Event 2: `p = 0.5`, `g = 8`, `c = 10`. First file Daniel and Yera use.
- **A (budget):** `T = 10, 20, 30, 60, 120` minutes. When does DP beat simple rules? (H1)
- **B (probability):** `p` from 0.01 to 0.90 on **one** event. How unlikely before reloading stops paying?
- **C (retry cost):** `c = 5, 20, 60, 120` seconds on **one** event, not every event. Does cost alone flip accept vs retry?
- **D (future opportunity, headline):** one early event fixed; a high-value later event added, removed, or revalued. (H3)
- **H5 (uncertain odds):** Beta prior, e.g. Beta(1, 49). Can a retry cap beat retry-until-success?

Player strategies the sim must compare: Never reload, Always reload, Fixed-k (`k = 2, 3, 5`), Reward-greedy, Efficiency-greedy, DP policy.

---

## 5. GitHub rules (apply to everyone)

1. Everyone pushes at least once per week via a pull request.
2. If it is not in GitHub, it does not count.
3. Shared schema first. One commit from each person that uses it.
4. Do not wait for Pokémon. Synthetic data unblocks DP, sim, and plots.
5. Pair on merge: reviewer from another module.
6. Report figures come from scripts in `analysis/`.
7. Do not commit `__pycache__`, `.env`, or secrets.

---

## 6. Week-1 checklist (from the original Option B note)

- Freeze the JSON schema + the 2-event toy instance.
- Daniel: DP solves the toy.
- Yera: simulator runs Never / Always / Fixed-k vs DP on that toy.
- Vivaan: synthetic 5-event (or more) files committed.
- Roy: draft Pokémon event list (timings can still be empty).
- Yusif: one analysis script that reads a CSV and prints mean + CI (dummy output is OK).

That is five GitHub commits in week 1, one each.

---

## 7. Vivaan — status and required changes

Work reviewed in `synthetic_data_and_rho_baseline` (Downloads, not yet the repo).

**Already done (good):**

- Generator + 23 JSON sessions + `manifest.json`
- Toy numbers match the plan
- Experiments A, B, C, D folders exist
- `rho_baseline.py` (known odds + Beta formula + `--solve`)
- Unit tests pass (9/9)

**Still required so Yusif can start:**

1. Put `data/synthetic/`, `baselines/`, `tests/` on GitHub. No `__pycache__`.
2. Freeze the JSON field names listed in section 3. Write that in `data/synthetic/README.md`.
3. Fix Experiment C: change retry time of **one** event only (E3 is fine). Regenerate those files.
4. Add `data/synthetic/dummy_sessions.csv` with the simulator columns in section 3 (even 20 fake rows).
5. Add `session_id` as the first column of the rho CSV. Keep other names.
6. Add one H5 JSON session with `odds_type: "beta"`, `alpha` and `beta` (plan example: 1 and 49).

**Can wait until after Yusif starts:**

- Dated Path of Exile placeholder (league, date, item list; empty prices OK at first)
- Toy E1 `travel_seconds` > 0
- Simpler Experiment D (early event + one later event, fewer bridge events)
- Literature / research-gap write-up (original Table 4)

Until items 1–6 are on `main`, Yusif is blocked.

---

## 8. Yusif — first deliverable once 7.1–7.6 exist

- Load `manifest.json`
- Load `dummy_sessions.csv`
- Print mean reward and 95% CI by `strategy` and `experiment`
- One Experiment A figure from a script in `analysis/`
- README: how to reproduce that figure
- Later: ethics/limitations freeze and report assembly on top of those artefacts

---

## 9. Roy / Daniel / Yera (so Option B stays consistent)

**Roy:** Pokémon 4–6 event list, odds table, video timings (at least 3 videos per event). Drop events where a reset is not a fresh roll. Same JSON schema as Vivaan. Swap synthetic files for `data/pokemon/` when ready.

**Daniel:** DP fills `V(i, t, k)`, `W`, `N`; policy map; then Beta module. Must run on **any** session JSON from Vivaan or Roy.

**Yera:** Monte Carlo, 10k+ sessions per strategy, identical seeds, record reward / reloads / time reloading. Write `sessions.csv` in the dummy schema Yusif already uses.

---

## 10. Why Pokémon and PoE (for the report)

- Pokémon = documented save-scumming (known `p`).
- PoE = farming with unpublished odds (Beta belief + a price snapshot).
- Same code for both. Pokémon is the main story; PoE is the contrast.
