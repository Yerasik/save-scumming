# Analysis Module

**Owner:** Yusif Seyidov (Sector 3 Analysis Lead)  

This module processes simulation session logs from the `save-scumming` pipeline, calculates descriptive statistics (mean reward and 95% confidence intervals), and generates standardized visualization assets for evaluation experiments.

---

## Prerequisites & Dependencies

Ensure you have the required Python data science libraries installed in your environment before running the analysis script:

```bash
pip install pandas numpy matplotlib
```

---

## Rebuilding Instructions & Commands

The analysis script (`analyze.py`) supports command-line arguments to switch dynamically between synthetic dummy data and real Monte Carlo simulation outputs.

### 1. Rebuilding with Dummy Data (Initial Pipeline Verification)
To verify the analytical pipeline using the provided synthetic dummy dataset and generate the dummy visualization asset, execute:

```bash
python analysis/analyze.py --csv data/synthetic/dummy_sessions.csv --manifest data/synthetic/manifest.json
```

### 2. Rebuilding with Real Simulation Data (Production Phase)
Once Monte Carlo simulator output (`sim/out/toy_sessions.csv`) is generated and synced in the repository, rebuild the statistical summary table and generate the final production chart using:

```bash
python analysis/analyze.py --csv sim/out/toy_sessions.csv --manifest data/synthetic/manifest.json
```

---

## Generated Outputs
* **Statistical Summary:** Prints a formatted summary table to the terminal containing strategy names, sample counts (n = 10,000), mean rewards, standard deviations, standard errors, and 95% confidence interval margins.
* **Figure Asset:** Saves the rendered visualization to `analysis/experiment_a_chart.png`.

---

## Experiment figures (report)

From the repository root, with pandas / numpy / matplotlib installed:

```
python -B analysis/analyze_h5.py        # analysis/experiment_h5_chart.png
python -B analysis/analyze_pokemon.py   # analysis/experiment_pokemon_chart.png
python -B analysis/analyze_poe.py       # analysis/experiment_poe_chart.png
```

**H5.** `analyze_h5.py` reads `dp/out/h5_recheck.csv`, not `sim/out/H5`. The simulator's `fixed_k_N` caps every event, which is not a fair H5 test at p = 0.02. The recheck caps only `rare_drop` and lets the later event retry until success. The chart shows DP, always-reload, and the best rare-drop-only cap (N annotated).

**Pokémon / PoE.** Bar charts from `sim/out/pokemon/pokemon_sv_main.csv` and `sim/out/poe/poe_exarch_beta.csv` after:

```
python -B experiments/run_experiment.py experiments/configs/pokemon.json
python -B experiments/run_experiment.py experiments/configs/poe.json
```