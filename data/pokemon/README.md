# `data/pokemon/` — Roy (Jihun Choi)

Pokémon Scarlet / Violet case study (known odds). Same session JSON shape as `data/synthetic/`. Nobody needs to own the game: odds from public documentation, timings from public videos (timestamps only, no footage re-uploaded).

**Status (2 Nov): final.** `pokemon_sv_main.json` is built from 12 retry timings (3 per event, 7 public videos) and 6 travel timings (2 per leg), and validates against the frozen schema.

| `event_id` | Retry (mean of 3) | Travel to next shrine (mean of 2) | `good_reward` |
|---|---|---|---|
| `wo_chien` | 93 s | 320 s | 20 |
| `chien_pao` | 108 s | 324 s | 30 |
| `ting_lu` | 110 s | 336 s | 20 |
| `chi_yu` | 141 s | 0 (last) | 30 |

Budget 60 min. `bad_reward = 0`. DP expected reward: 56.4.

## Pokémon note: event, p, c, videos

Summary for the report (issue #3). `p` for every event comes from the nature mechanic: 25 natures, each equally likely ([Bulbapedia: Nature](https://bulbapedia.bulbagarden.net/wiki/Nature)), so a target of 2 natures gives p = 2/25 = 0.08. A soft reset rerolls the nature ([Game8](https://game8.co/games/Pokemon-Scarlet-Violet/archives/393246)).

| # | Event | Target | `p` | Retry `c` | Travel `f` (to next shrine) | Videos (retry) | Videos (travel) |
|---|---|---|---|---|---|---|---|
| 1 | Wo-Chien | Bold or Calm | 0.08 | 93 s | 320 s (to Chien-Pao) | [Hooligan](https://www.youtube.com/watch?v=WxlYVDS5pfA) 9:36-11:14 (98 s)<br>[MunchingOrange](https://www.youtube.com/watch?v=q3LJGon1Fp4&t=430s) 11:02-12:32 (90 s)<br>[YTSunny](https://www.youtube.com/watch?v=Opk_JlROo8g&t=1098s) 18:16-19:46 (90 s) | [MunchingOrange](https://www.youtube.com/watch?v=q3LJGon1Fp4&t=430s) 13:24-19:34 (370 s)<br>[YTSunny](https://www.youtube.com/watch?v=Opk_JlROo8g&t=1098s) 20:27-24:58 (271 s) |
| 2 | Chien-Pao | Jolly or Adamant | 0.08 | 108 s | 324 s (to Ting-Lu) | [YTSunny](https://www.youtube.com/watch?v=Opk_JlROo8g&t=1499s) 25:22-26:47 (85 s)<br>[MunchingOrange](https://www.youtube.com/watch?v=q3LJGon1Fp4&t=430s) 20:53-22:30 (97 s)<br>[iStarlyTV](https://www.youtube.com/watch?v=QvtZD_aSk54) 15:43-18:06 (143 s) | [YTSunny](https://www.youtube.com/watch?v=Opk_JlROo8g&t=1499s) 0:00-4:20 (260 s, approx.: start point not shown)<br>[MunchingOrange](https://www.youtube.com/watch?v=q3LJGon1Fp4&t=430s) 25:11-31:38 (387 s) |
| 3 | Ting-Lu | Careful or Impish | 0.08 | 110 s | 336 s (to Chi-Yu) | [AbdahllaSmash](https://www.youtube.com/watch?v=DwDlN8c1C8E) 15:31-17:41 (130 s)<br>[YTSunny](https://www.youtube.com/watch?v=Opk_JlROo8g&t=1098s) 4:45-6:22 (97 s)<br>[MunchingOrange](https://www.youtube.com/watch?v=q3LJGon1Fp4&t=430s) 34:04-35:47 (103 s) | [YTSunny](https://www.youtube.com/watch?v=Opk_JlROo8g&t=1098s) 6:55-11:44 (289 s)<br>[MunchingOrange](https://www.youtube.com/watch?v=q3LJGon1Fp4&t=430s) 36:18-42:40 (382 s) |
| 4 | Chi-Yu | Timid or Modest | 0.08 | 141 s | 0 (last event) | [Hooligan](https://www.youtube.com/watch?v=QP-HRF2DUYs) 15:41-19:19 (218 s)<br>[YTSunny](https://www.youtube.com/watch?v=Opk_JlROo8g&t=1098s) 12:20-14:19 (119 s)<br>[MunchingOrange](https://www.youtube.com/watch?v=q3LJGon1Fp4&t=430s) 43:29-44:54 (85 s) | - |

**How the times were averaged.** Each timing is `end - start`, read off the video player. Retry runs from the start of the shrine battle to the catch / nature screen; travel runs from leaving one shrine to arriving at the next shrine's door, and is recorded on the row of the shrine being left. Stake hunting is excluded because it is a one-time setup. For each event, `c` is the plain mean of its 3 retry timings and `f` the mean of its 2 travel timings, rounded to whole seconds (`build_session.py`). Raw timestamps and notes are in `timings.csv`.

## Route

Postgame, fixed order. Before each shrine, the eight stakes are already pulled and the game is saved with autosave off. One reset cycle = close the game, reload, walk in, battle, catch, check the nature.

| # | `event_id` | Pokémon | Location | Target | `p` |
|---|---|---|---|---|---|
| 1 | `wo_chien` | Wo-Chien | South Province (Area One) | Bold or Calm | 2/25 = 0.08 |
| 2 | `chien_pao` | Chien-Pao | West Province (Area One) | Jolly or Adamant | 0.08 |
| 3 | `ting_lu` | Ting-Lu | Socarrat Trail | Careful or Impish | 0.08 |
| 4 | `chi_yu` | Chi-Yu | North Province (Area Two) | Timid or Modest | 0.08 |

- **Why nature, not shiny.** Static encounters and gifts in Scarlet/Violet are shiny-locked, so a shiny reset is not a fresh roll. Nature is rolled per encounter, each of the 25 equally likely.
- **Targets** are the usual competitive natures (Smogon / VGC). They are stated preferences, so `good_reward` / `bad_reward` are too. The team should agree on them and test sensitivity.
- **Fresh roll:** the plan drops an event only if documentation shows a reset is not a fresh roll. Guides document that nature and IVs are generated per encounter and rerolled by a soft reset (Game8, Pokestats; see Sources), and none of these four is nature-locked, so all four are kept. Per-video proof is not required.

## Dropped or not used

| Candidate | Why |
|---|---|
| Shiny resets on any static / gift | Shiny-locked in Scarlet/Violet: never a fresh roll |
| Bloodmoon Ursaluna, Pecharunt (DLC) | Nature fixed (Timid): reset is not a fresh roll for nature |
| Starter nature (Sprigatito / Fuecoco / Quaxly) | Fresh roll, but it is at story start, not in the same play session as the postgame route |
| Koraidon / Miraidon | Not checked yet. Add as event 5 only if docs show its nature is random |

## Files

| File | What |
|---|---|
| `events.csv` | Event list, odds, rewards |
| `timings.csv` | One row per (event, video): links, timestamps, notes |
| `build_session.py` | Averages timings, writes and validates the session JSON |
| `timings_summary.csv` | Written by the builder: video count and means per event |
| `pokemon_sv_main.json` | The session, written by the builder |
| `test_build_session.py` | Builder tests |

## Timing a video

For each event, find at least 3 public videos for retries (2 for travel) (YouTube, Twitch VODs) of someone resetting that encounter. In `timings.csv` add one row per video:

- `retry_start` / `retry_end`: from the start of the shrine battle to the catch / nature screen. Stake hunting is excluded (one-time setup). If a video shows several cycles, time one typical cycle, or several and note it.
- `travel_start` / `travel_end`: from leaving this shrine (opening the map) to arriving in front of the next shrine. It goes on the row of the shrine being **left**. Blank for the last event (`chi_yu`).
- Timestamps as shown on the player: `m:ss` or `h:mm:ss`. Fill `video_url`, `channel`, `video_date`.

Then:

```
python -B data/pokemon/build_session.py                 # needs 3 retry + 2 travel timings per event
python -B -m unittest discover -s data/pokemon -p 'test_*.py' -v
python -B -m dp.solve data/pokemon/pokemon_sv_main.json --out dp/out
python -B experiments/run_experiment.py experiments/configs/pokemon.json
python -B analysis/analyze_pokemon.py
```

Outputs: `dp/out/pokemon_sv_main.policy.json`, `sim/out/pokemon/pokemon_sv_main.csv`, `analysis/experiment_pokemon_chart.png`.

Means are rounded to whole seconds. The builder refuses to write `pokemon_sv_main.json` until every event has 3 retry timings and every event but the last has 2 travel timings (team decision, 2 Nov).

## Limitations

- Retry times run from battle start to catch. None of the timed videos show closing and reopening the game, so the real cost of a reset is somewhat higher.
- One Chien-Pao -> Ting-Lu travel timing (YTSunny, 0:00-4:20) opens already travelling to Ting-Lu; its start point is not shown to be Chien-Pao. It is used as an approximation and flagged in `timings.csv`.
- Rewards are stated preferences. See the sensitivity check below.

## Results (10,000 seeds; CSV in `sim/out/pokemon/`)

| Strategy | Stated rewards (20/30/20/30) | All rewards 25 |
|---|---|---|
| DP | 56.36 ± 0.53 | 58.8 ± 0.5 |
| Always reload | 56.36 ± 0.53 | 58.8 ± 0.5 |
| Fixed-k = 5 | 33.84 ± 0.47 | 33.9 ± 0.5 |
| Reward-greedy | 32.00 ± 0.29 | 28.8 ± 0.3 |
| Never reload | 8.14 ± 0.27 | 8.2 ± 0.3 |

- **Sensitivity:** with all four rewards set to 25, the DP policy is unchanged (each event: retry while at least one retry still fits), so the result does not depend on the exact reward values.
- **DP = always reload** on this route, at every budget tried (10, 15, 20, 30, 60 min; 5,000 seeds each, DP minus always within ±0.3). All four events have the same odds (0.08) and similar reward per second, and travel (~5.5 min) costs more than a reset (~1.5-2.5 min), so moving on early never pays. This is the H1 "near zero" case: real Pokémon resets are a route where the simple habit is already optimal. The synthetic experiments (A, D) show when it is not.

## Sources

- Shiny locks in Scarlet/Violet: [Serebii — Shiny Pokémon](https://serebii.net/scarletviolet/shinypokemon.shtml), [Prima Games](https://primagames.com/tips/all-shiny-locked-pokemon-in-pokemon-scarlet-and-violet)
- Shiny odds (context only): [Rotom Labs — SV shiny rates](https://rotomlabs.net/scarlet-violet/shiny-rates)
- Soft resetting rerolls nature and IVs: [Game8 — soft reset](https://game8.co/games/Pokemon-Scarlet-Violet/archives/393246), [Pokestats — soft resetting](https://pokestats.gg/shiny-hunting-hub/methods/soft-reset)
- Ting-Lu location and catch rate: [Serebii — Ting-Lu](https://www.serebii.net/pokedex-sv/ting-lu/)
- Natures (25, uniform): Bulbapedia "Nature" (cite in the report; it blocked automated access)
