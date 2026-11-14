Code and session files: https://github.com/Yerasik/save-scumming

# Why the experiments are named H1, H3 and H5

We report three tests, named after the hypotheses in the project plan rather than the folder letters A–D.

- **H1** asks whether looking ahead helps most when the clock is tight but not empty.
- **H3** asks whether a valuable later event can make retrying an earlier one a mistake.
- **H5** asks whether, when the odds are unknown, a retry cap can beat retrying until success.

The repository also has probability and retry-cost sweeps (B and C); they are not in this report, because they do not test those three claims. There is no H2 or H4 here: those were never lead hypotheses. Naming the runs H1, H3 and H5 keeps each table tied to a claim instead of a file name.

---

## 3.4 Datasets

The solver and the simulator take the same session files. Three kinds of session appear in this report.

**Synthetic factor sweeps.** H1 is an 8-event session whose only changing field is the time budget `T`. H3 is a two-event session whose only changing field is the later event's good reward (or that event is removed). H5 is a two-event session whose only changing field is the prior on the first event. These files exist so that one named factor can be moved at a time.

**Pokémon Scarlet / Violet (main case).** A four-shrine postgame route with known odds. Each shrine is a nature hunt at `p = 0.08` (2 natures out of 25). Retry and travel times are means from public videos. Budget `T = 60` minutes. Rewards are stated preferences `(20, 30, 20, 30)`, not market prices.

**Path of Exile contrast.** A session named after the regular Searing Exarch encounter. The rare unique is given a `Beta(1, 49)` belief (2% mean, from a dated community snapshot). Retry and travel times match the H5 sessions; they are not measured from Path of Exile footage. This file is an illustration of unknown odds, not a farming calculator.

Every result below is 10,000 Monte Carlo sessions per strategy. Seeds are 0 through 9,999 and are reused across strategies. Mean reward is reported with a 95% interval (mean ± 1.96 SE). When two strategies are compared, the difference is paired on those shared seeds.

## Methodology (experiment list)

Each experiment changes one factor and keeps everything else fixed. We name them H1, H3 and H5 after the three lead hypotheses, not A, B, C, D after the config folders:

- **H1 (time budget).** An 8-event session played with `T = 10, 20, 30, 60` and `120` minutes. Is the DP's advantage largest at moderate time pressure, and near zero if the budget is tiny or huge?
- **H3 (later prize).** An early event (`p = 0.1`, `g = 10`) followed by a rare, slow later event (`p = 0.05`) that is either removed or worth `10, 20, 40, 80` or `160`. Is there a later reward large enough that the DP stops retrying the early event?
- **H5 (unknown odds).** A rare drop with the same 2% average chance in every session, either known or held as `Beta(20, 980)`, `Beta(1, 49)` or `Beta(0.2, 9.8)`, followed by a later known event. When the odds are unknown, can a retry cap beat retrying until success? Because the simulator's `fixed-k` rule caps every event, we also tested caps on the rare drop alone (1 to 90 attempts), so that the comparison is about uncertainty and not about giving up on the later event too.

---

## 4. Simulation engine and experiment results

### 4.1 How a session is played

The simulator walks the event list in order and spends a shared clock, starting at `T` seconds. It does not solve a dynamic program. For the DP strategy it only looks up the written policy file after each failure.

The first attempt at a reached event is free. A success adds `g_i` and the player pays travel `f_i` to the next event. A failure is then a choice: take `b_i` and move on, or pay `c_i` seconds, throw away the bad roll (retained failure reward is 0 in every session here), and roll again. If the clock cannot pay `f_i`, later events are never reached and score 0. If the clock cannot pay `c_i`, a retry is treated as accept.

Named strategies, after a failed roll:

- never: always accept.
- always: retry while `time_left ≥ c_i`.
- `fixed_k_2`, `fixed_k_3`, `fixed_k_5`: at most `k` attempts on every event, counting the free first attempt, and also stop when the clock cannot pay `c_i`.
- reward_greedy: retry only the highest-reward event, and only if the retry still leaves travel time to the last event.
- efficiency_greedy: retry while `p(g − b)/c` is above a cutoff (0.10 in these runs), with the same travel reserve. For Beta events this rate uses the prior mean, not the hidden `p`.
- dp: follow the policy map for this event, time left, and failure count.

Known-odds events use the published `p` on every roll. Beta events draw one hidden success chance per `(seed, event)` from `Beta(α, β)` and keep that chance for every retry of that seed. Strategies that share a seed therefore face the same luck and the same hidden `p`. That is what makes “DP beat always by X” a statement about the rule, not about a luckier sample.

Each row of the output CSV is one (session, strategy, seed) playthrough: total reward, number of reloads, and seconds spent reloading.

### 4.2 Checks

Before the tables, three checks. The simulated mean of the DP policy matched the solver's predicted value in every H5 session (z between +0.23 and +1.17 at 10,000 seeds). On a simple geometric wait, average tries sit near `1/p`. Automated tests on the simulator, the policy lookup, and the session files pass.

### 4.3 H1: time budget

Question: when does looking ahead beat a simple habit? Only `T` changes: 10, 20, 30, 60, and 120 minutes. The eight events stay fixed.

H1 says the DP's edge over the best simple rule is largest at moderate pressure and near zero if the budget is tiny or huge.

Table 1. H1, 10,000 shared seeds. Mean reward ± 95% CI. The last column is the paired difference DP minus the best simple rule.

| Budget | Best simple rule | DP | Best simple | DP − best |
|---|---|---|---|---|
| 10 min | efficiency-greedy | 67.0 ± 0.5 | 66.9 ± 0.5 | 0.1 ± 0.2 |
| 20 min | efficiency-greedy | 91.5 ± 0.5 | 82.8 ± 0.3 | 8.6 ± 0.5 |
| 30 min | fixed-k = 5 | 107.5 ± 0.6 | 88.7 ± 0.6 | 18.7 ± 0.6 |
| 60 min | always | 137.9 ± 0.7 | 127.8 ± 1.0 | 10.1 ± 0.5 |
| 120 min | always | 158.5 ± 0.4 | 156.4 ± 0.5 | 2.1 ± 0.2 |

That is what H1 predicts. At 10 minutes there is almost no room to spend extra retries, so efficiency-greedy already matches DP (the 0.1 gap is inside the interval). At 30 minutes the gap is 18.7. At 120 minutes always-reload is almost as good, because later events are no longer at risk.

The best simple rule also changes with `T`: efficiency-greedy when time is tight, a retry cap in the middle, always-reload when time is loose. No single habit wins every budget. The DP switches between those habits by itself.

(Figure: `analysis/experiment_a_chart.png` — Yusif.)

### 4.4 H3: a later prize

Question: is there a later reward large enough that the DP stops retrying an earlier event?

The first files for this sweep could not answer this. The later event had `p = 0.5` and a 10-second retry, so it was almost always won in a few tries. Raising its reward from 8 to 80 did not change the early policy. The rebuilt H3 sessions keep the hard early event from the toy (`p = 0.1`, `g = 10`, `c = 20` s) and make the later event rare and slow (`p = 0.05`, `c = 30` s), with `T = 600` s. Only the later good reward changes: removed, 10, 20, 40, 80, 160.

From a full budget, the DP's planned retries on the early event are:

| Later reward | removed | 10 | 20 | 40 | 80 | 160 |
|---|---|---|---|---|---|---|
| Early retries (DP) | 30 | 30 | 30 | 18 | 0 | 0 |

At 80 and 160 the policy gives up on the early event entirely. That is H3 on the policy map.

Table 2. H3, 10,000 shared seeds. Mean reward.

| Later reward | removed | 10 | 20 | 40 | 80 | 160 |
|---|---|---|---|---|---|---|
| DP | 9.6 | 14.5 | 19.4 | 29.2 | 52.7 | 104.2 |
| Always reload | 9.6 | 14.5 | 19.4 | 29.1 | 48.5 | 87.4 |
| Reward-greedy | 9.6 | 10.0 | 14.0 | 26.9 | 52.7 | 104.2 |

While the later prize is small, DP and always-reload are the same: keep retrying the early event. Once the later prize is 80 or more, DP matches reward-greedy instead, and always-reload loses 4.1 (80) and 16.8 (160) because it burns the clock on the early 10-point event. No single simple rule wins the whole sweep. The DP is the rule that switches.

(Figure: `analysis/experiment_d_chart.png` — Yusif.)

### 4.5 H5: unknown odds

Question: when the odds are unknown, can a retry cap beat retry-until-success?

Four sessions share the same 2% mean on a rare drop, then a later known event that competes for the same 30-minute clock. The four beliefs are: known `p = 0.02`, `Beta(20, 980)` (strong), `Beta(1, 49)`, and `Beta(0.2, 9.8)` (weak). Retry time is 20 seconds. An earlier file used 60 seconds, and the DP never retried, so a cap and always-reload would have looked the same for the wrong reason.

The simulator's `fixed-k = 2, 3, 5` rule is not a fair test here. It caps every event. At `p = 0.02` those caps barely use the budget and score about 13–32 against about 150. That gap is “gave up on the later event too,” not “handled uncertainty.” The comparison that belongs in this section caps only the rare drop, keeps travel to the next event, lets the later event retry until success, and sweeps the cap from 1 to 90 attempts (`dp/out/h5_recheck.csv`).

Table 3. H5, 10,000 seeds. Always-reload vs the best cap on the rare drop only vs DP. The “cap − always” column is paired.

| Belief | Always | Best cap (attempts) | Cap − always | DP (sim) |
|---|---|---|---|---|
| Known p = 0.02 | 152.0 | 153.8 (75) | +1.8 | 153.8 |
| Beta(20, 980) | 149.1 | 151.6 (75) | +2.5 | 151.6 |
| Beta(1, 49) | 118.1 | 133.6 (60) | +15.6 | 134.1 |
| Beta(0.2, 9.8) | 69.4 | 114.1 (30) | +44.7 | 114.1 |

A cap helps a little when the odds are known, because the later event still needs time: always-reload keeps hitting the 2% drop until the clock forces it out (H3 again). A cap helps a lot when the odds are uncertain, and the extra gain grows as the prior gets weaker (+2.5, then +15.6, then +44.7, against +1.8 when `p` is known). The best cap also shortens (75 → 60 → 30), which is where the DP gives up on the policy map.

On this one-uncertain-event setup, the best fixed cap is as good as the DP (within 0.5). The DP's value is that it finds that `N` from the belief. A player who picks `N` by hand has to already know roughly how unsure they are.

(Figure: `analysis/experiment_h5_chart.png`, and the H5 policy map in `dp/out/figures/` — Yusif / Daniel.)

### 4.6 Two game sessions on the same engine

Pokémon Scarlet / Violet, 60-minute shrine route, known `p = 0.08`. Odds and timings are Roy's; the numbers below are the same 10,000-seed run of that file.

| Strategy | Mean reward |
|---|---|
| DP | 56.36 ± 0.53 |
| Always reload | 56.36 ± 0.53 |
| Fixed-k = 5 | 33.84 ± 0.47 |
| Reward-greedy | 32.00 ± 0.29 |
| Never / efficiency-greedy | 8.14 ± 0.27 |

DP equals always-reload on every seed. All four shrines have the same odds and similar reward per second, and travel (~5.5 min) costs more than a reset (~1.5–2.5 min), so moving on early never pays. This is H1's “near-zero edge” case on a real route: the simple habit is already the policy. The synthetic sweeps are where looking ahead matters.

Path of Exile Exarch contrast, `Beta(1, 49)` on the 2% unique, timings copied from the H5 sessions.

| Strategy | Mean reward |
|---|---|
| DP | 133.64 ± 1.37 |
| Efficiency-greedy | 119.11 ± 1.78 |
| Always reload | 118.03 ± 1.79 |
| Reward-greedy | 69.97 ± 1.03 |
| Fixed-k = 5 (every event) | 31.32 ± 1.00 |
| Never | 6.91 ± 0.51 |

DP beats always-reload by about 15.6, which is the H5 `Beta(1, 49)` result with Path of Exile names. Fixed-k = 5 here again caps every event, so it is not the H5 test; Table 3 is.

### 4.7 What H1, H3 and H5 say together

Look ahead when time is limited and the next event is valuable enough (H1, H3), or when a failure should make you doubt the odds (H5). A constant cap is often enough if someone else has already chosen `N`. The DP is the method that produces `N`, and that switches `N` when the later prize or the belief changes.

---

Suggested contribution-table row (section 7)

| Name | UID | Contribution |
|---|---|---|
| Yerassyl Taisarinov (Yera) | 3036459776 | Monte Carlo simulator (`sim/`): session playback, named strategies, shared seeds, Beta hidden-p draws, `sessions.csv`. Ran H1, H3, H5, Pokémon, and Path of Exile (10,000 seeds). Wrote the simulation-engine and experiment-result sections. |
