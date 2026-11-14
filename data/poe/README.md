# `data/poe/` — Path of Exile contrast

Pokémon is the main case (known `p`). This folder is the **uncertain-odds contrast**.

The dated snapshot lives at
`data/synthetic/poe_github_upload/data/poe/mercenaries_3_26_snapshot_2026-11-05.json`
(regular Searing Exarch, Mercenaries 3.26.0, compiled 2026-11-05). Prices are
intentionally `null`. The 2% community estimate for **Dissolution of the Flesh**
is the prior mean.

`poe_exarch_beta.json` turns that 2% figure into a session the DP and simulator
can run: Beta(1, 49) on the rare unique, then a later known event. Retry and
travel times match H5 v2 (illustrative, not timed from PoE footage).

```
python -B experiments/run_experiment.py experiments/configs/poe.json
python -B analysis/analyze_poe.py
```
