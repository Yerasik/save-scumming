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
* **Statistical Summary:** Prints a formatted summary table to the terminal containing strategy names, sample counts ($n = 10,000$), mean rewards, standard deviations, standard errors, and 95% confidence interval margins.
* **Figure Asset:** Saves the rendered visualization to `analysis/experiment_a_chart.png`.