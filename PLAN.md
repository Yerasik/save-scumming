# Project plan and roles

This is the working plan for the repo. The submitted course plan is `COMP1110_Project_Plan.tex`. If the two disagree on dates, Moodle wins.

Project in one line: compute when to reload a bad roll under a limited playtime budget, then simulate that rule against simpler player habits.

---

## 1. Research question

In a sequence of random game events that share one finite real-time budget, when is retrying after a bad outcome worth the time it takes from later events?

**Limited playtime (main).** There is a deadline. Events you never reach are missed. Solved with dynamic programming (DP).

**Unlimited playtime (baseline).** No deadline, but time still has a value. Retry if expected extra reward per second beats a cutoff `ρ`.

### Hypotheses we will actually lead with

- **H1.** DP’s edge over simple rules is largest at moderate time pressure, and near zero if the budget is tiny or huge.
- **H3.** There is a later reward large enough that DP stops retrying an earlier event. (Headline.)
- **H5.** When odds are unknown, a retry cap can beat “retry until success.” That should not happen when odds are known.

### Player strategies the simulator compares

| Strategy | After a bad roll |
|---|---|
| Never reload | Always accept |
| Always reload | Reload if there is time |
| Fixed-k | At most k rolls per event (`k = 2, 3, 5`) |
| Reward-greedy | Only chase the best rewards, while time remains to finish the route |
| Efficiency-greedy | Reload while reward-per-second is above a cutoff |
| DP policy | The map from `dp/` |

---

## 2. Pipeline

1. Vivaan writes synthetic JSON (Roy later writes Pokémon JSON in the **same** shape).
2. Daniel’s DP reads that JSON and writes a policy.
3. Yera’s simulator plays many sessions on **identical seeds** and writes `sessions.csv`.
4. Yusif’s analysis reads the CSV and makes figures and tables.

Nobody waits for Pokémon. Synthetic data is enough to build DP, sim, and plots.

---

## 3. Frozen JSON (do not rename)

### Session

- `schema_version`
- `session_id`
- `description`
- `experiment` (`toy`, `A`, `B`, `C`, `D`, `H5`, …)
- `varied_factor`
- `varied_value`
- `budget_seconds`
- `events` (list)

### Each event

- `event_id`
- `odds_type`: `known` or `beta`
- `p` (if known)
- `alpha`, `beta` (if beta)
- `good_reward` (`g`)
- `bad_reward` (`b`)
- `retry_seconds` (`c`)
- `travel_seconds` (`f`) — last event is `0`
- `entry_cost` (`e`) — `0` for save-scumming
- `retained_failure_reward` (`h`) — `0` when a reload throws away the bad result

### Simulator CSV (`sessions.csv`)

`session_id`, `experiment`, `strategy`, `seed`, `reward`, `reloads`, `time_reloading`

### Rho baseline CSV

`session_id` first, then `event_id`, `failures`, `probability`, `marginal_reward`, `retry_seconds`, `reward_per_second`, `rho`, `action`

---

## 4. Experiments

Toy instance (first file DP and sim use):

- `T = 180` seconds
- Event 1: `p = 0.1`, `g = 10`, `b = 0`, `c = 20`
- Event 2: `p = 0.5`, `g = 8`, `c = 10`

If event 2 is still ahead, DP should refuse a third retry on event 1. Always-reload can burn the budget and miss event 2.

| Expt | What changes | Question |
|---|---|---|
| A | Budget `T = 10, 20, 30, 60, 120` minutes | When does DP beat simple rules? (H1) |
| B | `p` on **one** event, 0.01 to 0.90 | How unlikely before reloading stops paying? |
| C | Retry time on **one** event only: 5, 20, 60, 120 seconds | Does cost alone flip accept vs retry? |
| D | Early event fixed; a high-value later event added, removed, or revalued | Does the later prize kill the early reload? (H3) |
| H5 | Beta prior, e.g. Beta(1, 49) | Can a retry cap beat retry-until-success? |

---

## 5. Timeline

Week-based. Confirm Moodle if a date moves.

| Week | Dates | Milestone | Lead |
|---|---|---|---|
| 1 | 6–12 Oct | Freeze schema + toy; DP solves the toy | Daniel |
| 2 | 13–19 Oct | Simulator: 10k sessions, Never / Always / Fixed-k vs DP | Yera |
| 3 | 20–24 Oct | Interim TA meeting (~5 min); first policy-map figure | Yusif |
| 4 | 27 Oct–2 Nov | Pokémon: 4–6 events, odds table, video timings (≥3 videos each) | Roy |
| 5 | 3–4 Nov | Individual progress log; experiments A and D | Yera, Daniel, Roy |
| 6 | 5–11 Nov | Uncertain-odds + H5; freeze ethics / limitations text | Daniel, Yera, Yusif |
| 7 | 12–15 Nov | Final report (due 15 Nov) | Yusif, Vivaan |
| 8 | 17–26 Nov | 10-minute presentation | all |

---

## 6. Roles

Five people, five folders. Same workload on paper. Everyone commits.

### Daniel — Vu Q. Nguyen — `dp/`

He answers: given this event, this much time left, and this many failed rolls, reload or move on?

**Build**

- A solver that reads **any** session JSON (synthetic or Pokémon). No toy-only hardcoding.
- Fill `V(i, t, k)`, `W`, `N` from the project plan. Time in whole seconds.
- Write a **policy map**: for each event and remaining time, retry or accept. That figure is what the TA should see.
- Later: Beta / uncertain-odds. After `k` failures, use posterior mean `q = alpha / (alpha + beta + k)`. Example prior: Beta(1, 49) ≈ 2% belief.

**When**

- Week 1: toy DP works.
- Week 3: policy-map figure exists.
- Week 5: support experiments A and D.
- Week 6: Beta module and H5.

**Done when** one command on a JSON file dumps a policy, and the same command works on Roy’s files later.

He unblocks Yera (needs a policy) and Yusif (needs a figure).

---

### Yera — Yerassyl Taisarinov — `sim/`

Daniel says what a smart player *should* do. Yera actually rolls the dice.

**Build**

- Play a session event by event, spending time, following a named strategy.
- Strategies: Never, Always, Fixed-k (2, 3, 5), Reward-greedy, Efficiency-greedy, DP (read `policy.json`, do not re-solve DP).
- At least 10,000 sessions per strategy.
- **Same seeds** across strategies so the comparison is fair.
- Write `sessions.csv` with the columns in section 3.
- Check: for a simple geometric wait, average tries should sit near `1/p`. If not, the simulator is wrong.

**When**

- Week 2: toy runs, Never / Always / Fixed-k vs DP.
- Week 3: enough output that Yusif is not plotting empty air.
- Week 5: experiments A and D (report headline).
- Week 6: same engine on Beta sessions.

**Done when** one command + a seed list produces a CSV Yusif can plot without sitting next to you.

He unblocks Yusif. Roy’s experiment configs say which JSON files to run.

---

### Roy — Jihun Choi — `data/pokemon/` and `experiments/`

He turns “we mean Pokémon” into numbers the code can eat, and writes the experiment recipes.

Nobody in the group needs to own the game. Public wiki + public videos.

**Pokémon (main case)**

- 4–6 resettable events in Scarlet / Violet, fixed order.
- Odds from Bulbapedia / published tables.
- **Drop any event where a reset is not a fresh roll.**
- For each event, at least 3 public videos. Average retry time `c` and travel `f`. Last event: `travel_seconds = 0`.
- Same JSON schema as Vivaan. When these files land, the rest of the code should not care that they are “real.”

**Experiment configs**

One named factor per experiment (table in section 4). Experiment C must change retry time on **one** event only, not every event.

**When**

- Week 1: draft event list (empty timings are fine).
- Week 3: list is solid enough to say out loud in the TA meeting.
- Week 4: timings and odds table done. This is the crunch week.
- Week 5: help read A and D — what would a player actually do.

**Done when** a short note lists event, `p`, `c`, video URLs, and how you averaged them. JSON validates against the frozen schema.

Without this, the project is only a toy RNG. With it, markers can check the links.

---

### Vivaan — Vivaan Kandhari — `data/synthetic/` and `baselines/`

He unblocks the others. Fake sessions first, real Pokémon later.

Official plan also gives him the literature / research-gap write-up and the Path of Exile snapshot.

**Synthetic data (do this first)**

- Generator, JSON sessions, `manifest.json`.
- Toy numbers must match section 4.
- Folders for A, B, C, D.
- Experiment C: only one event’s retry time changes.
- One H5 JSON with `odds_type: "beta"` (example `alpha = 1`, `beta = 49`).
- `dummy_sessions.csv` using the simulator columns, even if the rows are fake, so Yusif can start.

**ρ-baseline**

- No deadline: retry event `i` if expected extra reward ≥ `ρ * retry_seconds`.
- CSV: `session_id` first, then the fields in section 3.

**Path of Exile (secondary only)**

- One dated snapshot: league, date, item list. Empty prices OK at first.
- Community drop estimates. No live scrape, no bots, no need to play.
- Not a second full case study.

**Literature (report)**

- Short note per source (keep 5–10 sources).
- Gap in one sentence: we did not find a study that allocates **one real-time budget across several sequential events**, with accept-or-retry, including a Beta belief when odds are unknown.

**When**

- Now: schema on GitHub, dummy CSV, C fix, H5 JSON — otherwise Yusif is stuck.
- Weeks 6–7: PoE snapshot; help freeze ethics text.

**Done when** someone clones, runs the generator, and never has to ask what a field is called.

---

### Yusif — Yusif Seyidov — `analysis/` plus repo glue

Markers read the report and watch the talk. They will not debug five half-broken folders. Yusif is the person who makes the course see the work.

**Code**

- Load `manifest.json` and `dummy_sessions.csv`, later Yera’s real CSV.
- Mean reward and 95% CI by `strategy` and `experiment`.
- At least one Experiment A figure **from a script**.
- README commands that reproduce that figure.
- Tests / CI so `main` stays runnable. Review other people’s PRs.

**Course**

- Week 3: ~5 min TA meeting. Need: the question, DP vs baselines, a policy-map figure, who owns what, next two weeks (Roy’s timings, Yera’s 10k runs).
- Ethics freeze: no surveys, public data only, timestamps not re-uploaded videos, no ToS bots, no moral claim about save-scumming.
- Nag the 3–4 Nov individual progress log.
- Assemble the 15 Nov report and the 10-minute presentation script.

**When**

- Week 3: meeting + first figure.
- Week 5: start stitching A/D.
- Week 6: ethics / limitations freeze.
- Week 7–8: report and talk.

**Done when** a stranger can restate the question in one sentence and reproduce one figure from the README.

---

## 7. Who talks to who

| From | To | File |
|---|---|---|
| Vivaan (later Roy) | Daniel | session JSON |
| Daniel | Yera | `policy.json` |
| Yera | Yusif | `sessions.csv` |
| Roy | everyone | experiment configs + Pokémon JSON |
| Yusif | all | deadlines, TA story, report |

---

## 8. GitHub rules

1. At least one pull request per person per week.
2. If it is not on GitHub, it does not count.
3. First commit from each person should **use** the frozen schema.
4. Reviewer from another module.
5. Do not wait for Pokémon.
6. No `__pycache__`, `.env`, or secrets.
7. Figures in the report come from `analysis/` scripts.

---

## 9. Scope we already closed

In: independent binary events; known or Beta-uncertain odds; DP vs simple rules; simulation; one primary case study (Pokémon); a small uncertain-odds test.

Out: apps, live bots, player surveys, branching paths, RNG manipulation.

Pokémon is the story. Path of Exile is a contrast. If both become full empirical studies, five people will not finish by 15 November.

---

## 10. Week 3 checklist (20–24 Oct)

| Person | Do not show up empty |
|---|---|
| Daniel | Toy DP works; policy-map screenshot |
| Yera | Sim runs on the toy, or at least reads Daniel’s policy |
| Vivaan | Synthetic JSON + dummy CSV on `main` |
| Roy | Draft 4–6 event list (timings can still be holes) |
| Yusif | 5-minute script + one figure + “next: timings and 10k runs” |
