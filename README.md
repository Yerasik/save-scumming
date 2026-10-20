# Save Your Save

COMP1110 group project (HKU, 2026/27 Semester 1). Hybrid: dynamic programming + simulation.

This repo is a **Python prototype**, not an app and not a game bot. It answers one question:

**If you have a limited play session and several random events in a row, when is reloading a bad roll worth the time it takes from later events?**

Save-scumming means saving before a random roll (loot, a catch, a check) and reloading until you like the result. The same choice shows up when you farm a boss for a rare drop. Reloading once is easy to think about. Reloading when a better event is still ahead is not: every retry burns minutes you might need later.

The code computes a reload-or-accept rule, then fake-plays thousands of sessions to see if that rule beats simple habits (never reload, always reload, reload at most *k* times, and a couple of greedy rules).

## What we are not doing

- Building a product or UI
- Scraping live markets or talking to game servers
- Surveying players
- Modelling branching stories or RNG seed tricks

## Two game illustrations

| | Role | Odds | Data |
|---|---|---|---|
| Pokémon Scarlet / Violet | Main case | Published (known `p`) | Public tables + timestamps from public videos. Nobody needs to own the game. |
| Path of Exile-style farming | Small extra | Uncertain (Beta belief) | Community drop estimates + **one dated** price snapshot. No live scrape. |

Same code for both. Pokémon is the story. Path of Exile is the contrast.

## How the pieces fit

```
JSON session (events + time budget)
        |
        v
   dp/  writes a policy map  (retry or accept)
        |
        v
  sim/  plays 10k+ sessions on shared seeds
        |
        v
  sessions.csv
        |
        v
analysis/  means, 95% CIs, figures
```

Start with **synthetic** sessions in `data/synthetic/`. Pokémon files in `data/pokemon/` replace those later. Do not wait for video timings to write DP, the simulator, or plots.

## Folder map

| Folder | Owner | What goes here |
|---|---|---|
| `dp/` | Daniel | Solver and policy map (known odds, then Beta) |
| `sim/` | Yera | Monte Carlo engine, shared seeds, `sessions.csv` |
| `data/synthetic/` | Vivaan | Fake sessions + `manifest.json` so everyone can start |
| `data/pokemon/` | Roy | Real event list, odds, video timings (same JSON shape) |
| `experiments/` | Roy | Configs for experiments A, B, C, D |
| `baselines/` | Vivaan | Reward-per-second (ρ) rule |
| `analysis/` | Yusif | Plots, CIs, README commands that reproduce figures |
| `tests/` | shared (Yusif glue) | Schema and pipeline checks so `main` stays runnable |

Shared files between modules (do not rename fields):

- session JSON (event list + budget)
- `policy.json` (from DP)
- `sessions.csv` (from the simulator)

JSON field names are frozen in [PLAN.md](PLAN.md).

## Experiments (short)

Each run changes **one** thing.

- **Toy** — 2 events, 180 seconds. First thing DP and sim must solve.
- **A** — different time budgets. When does DP actually beat simple rules?
- **B** — change probability on one event. How rare before reloading stops paying?
- **C** — change retry cost on **one** event only.
- **D** — headline. Same early event; a high-value later event is added, removed, or revalued.
- **H5** — uncertain odds. Can a retry cap beat “retry until success”?

## Course deliverables

The course mark is the write-up and talk. This repo exists to produce numbers and figures for those.

| Date | What |
|---|---|
| 20–24 Oct 2026 | Interim progress meeting (~5 min) |
| 3–4 Nov 2026 | Individual progress log; experiments A and D |
| **15 Nov 2026** | Final report |
| 17–26 Nov 2026 | 10-minute group presentation |

## Team

| Name | UID | Lead |
|---|---|---|
| Vu Q. Nguyen (Daniel) | 3036755728 | Dynamic program and policy map |
| Yerassyl Taisarinov (Yera) | 3036459776 | Simulator and experiment runs |
| Jihun Choi (Roy) | 3036734023 | Pokémon case study and experiment configs |
| Yusif Seyidov (Yusif) | 3036538850 | Analysis, report, coordination |
| Vivaan Kandhari (Vivaan) | 3036684400 | Synthetic data, ρ-baseline, PoE snapshot, literature |

Who does what week by week: **[PLAN.md](PLAN.md)**.

Submitted project plan (LaTeX): `COMP1110_Project_Plan.tex`.

## Repo rules

1. Everyone pushes at least once a week, via a pull request.
2. If it is not on GitHub, it does not count.
3. Reviewer should be from another folder.
4. Do not commit `__pycache__`, `.env`, or secrets.
5. Report figures come from scripts in `analysis/`, not from hand-edited charts.
