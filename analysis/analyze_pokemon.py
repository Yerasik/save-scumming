"""Bar chart for the Pokémon Scarlet/Violet main session.

    python -B analysis/analyze_pokemon.py
"""
from __future__ import annotations

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CSV = "sim/out/pokemon/pokemon_sv_main.csv"
OUTPUT = "analysis/experiment_pokemon_chart.png"

ORDER = ["dp", "always", "fixed_k_5", "efficiency_greedy", "reward_greedy", "never"]
LABELS = {
    "dp": "DP",
    "always": "Always-reload",
    "fixed_k_5": "Cap k=5",
    "efficiency_greedy": "Efficiency-greedy",
    "reward_greedy": "Reward-greedy",
    "never": "Never-reload",
}


def main() -> None:
    if not os.path.exists(CSV):
        raise FileNotFoundError(
            f"{CSV} missing. Run:\n"
            "  python -B experiments/run_experiment.py experiments/configs/pokemon.json"
        )
    df = pd.read_csv(CSV)
    grouped = df.groupby("strategy")["reward"].agg(mean="mean", std="std", n="count")
    grouped["se"] = grouped["std"].fillna(0) / np.sqrt(grouped["n"].replace(0, 1))
    grouped["ci"] = 1.96 * grouped["se"]
    print("=== POKÉMON (pokemon_sv_main) ===")
    print(grouped.loc[[s for s in ORDER if s in grouped.index]].to_string())

    present = [s for s in ORDER if s in grouped.index]
    x = np.arange(len(present))
    means = grouped.loc[present, "mean"]
    cis = grouped.loc[present, "ci"]
    plt.figure(figsize=(9, 5.5))
    plt.bar(x, means, yerr=cis, capsize=4, color="steelblue", ecolor="black")
    plt.xticks(x, [LABELS[s] for s in present], rotation=20, ha="right")
    plt.ylabel("Mean total reward")
    plt.title("Pokémon SV route: DP vs simple habits (10k seeds)")
    plt.grid(True, axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    os.makedirs("analysis", exist_ok=True)
    plt.savefig(OUTPUT, dpi=300)
    plt.close()
    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    main()
