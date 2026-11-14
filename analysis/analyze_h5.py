"""Experiment H5 chart from the rare-drop-only cap recheck.

The simulator's fixed_k_N caps *every* event, so at p = 0.02 a k=3 or k=5 cap
barely uses the budget and is not a fair test of H5. Daniel's recheck
(dp/out/h5_recheck.csv) caps only rare_drop and lets the later event retry
until success.

    python -B analysis/analyze_h5.py
"""
from __future__ import annotations

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RECHECK = "dp/out/h5_recheck.csv"
OUTPUT = "analysis/experiment_h5_chart.png"

SESSION_ORDER = [
    "H5_known_p0p02",
    "H5_beta_a20_b980",
    "H5_beta_a1_b49",
    "H5_beta_a0p2_b9p8",
]
SESSION_LABELS = {
    "H5_known_p0p02": "Known p=0.02",
    "H5_beta_a20_b980": "Beta(20, 980)",
    "H5_beta_a1_b49": "Beta(1, 49)",
    "H5_beta_a0p2_b9p8": "Beta(0.2, 9.8)",
}


def load_recheck(path: str = RECHECK) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. From the repo root run:\n"
            "  python -B -m dp.h5_recheck --seeds 10000"
        )
    df = pd.read_csv(path)
    df["ci_95_margin"] = 1.96 * df["se"]
    return df


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sid in SESSION_ORDER:
        block = df[df["session_id"] == sid]
        if block.empty:
            raise ValueError(f"no rows for {sid} in the recheck CSV")

        dp = block[block["strategy"] == "dp"].iloc[0]
        always = block[block["strategy"] == "always"].iloc[0]
        caps = block[block["strategy"] == "cap_first_event"]
        best = caps.loc[caps["mean_reward"].idxmax()]

        for name, row, extra in (
            ("dp", dp, ""),
            ("always", always, ""),
            ("best_cap", best, int(best["cap_attempts"])),
        ):
            rows.append({
                "session_id": sid,
                "label": SESSION_LABELS[sid],
                "sort_key": SESSION_ORDER.index(sid),
                "series": name,
                "cap_attempts": extra if extra != "" else np.nan,
                "mean_reward": row["mean_reward"],
                "ci_95_margin": row["ci_95_margin"],
            })
    return pd.DataFrame(rows)


def plot_h5(stats: pd.DataFrame, output_path: str = OUTPUT) -> None:
    plt.figure(figsize=(11, 6))
    x = np.arange(len(SESSION_ORDER))
    labels = [SESSION_LABELS[s] for s in SESSION_ORDER]

    styles = {
        "dp": {"fmt": "-o", "color": "purple", "lw": 2.5, "ms": 8, "label": "DP"},
        "always": {"fmt": "-s", "color": "crimson", "lw": 2, "ms": 7, "label": "Always-reload"},
        "best_cap": {"fmt": "-^", "color": "teal", "lw": 2, "ms": 8,
                     "label": "Best cap on rare_drop only"},
    }

    for series, cfg in styles.items():
        sub = stats[stats["series"] == series].sort_values("sort_key")
        plt.errorbar(
            x, sub["mean_reward"], yerr=sub["ci_95_margin"],
            fmt=cfg["fmt"], color=cfg["color"], capsize=5,
            linewidth=cfg["lw"], markersize=cfg["ms"], label=cfg["label"],
        )
        if series == "best_cap":
            for xi, yi, cap in zip(x, sub["mean_reward"], sub["cap_attempts"]):
                plt.annotate(
                    f"N={int(cap)}",
                    (xi, yi),
                    textcoords="offset points",
                    xytext=(0, 8),
                    ha="center",
                    fontsize=8,
                    color=cfg["color"],
                )

    plt.xticks(x, labels, fontsize=10, fontweight="bold")
    plt.xlabel("Prior on the rare drop (mean 0.02 in every panel)", fontsize=11, fontweight="bold")
    plt.ylabel("Mean total reward", fontsize=11, fontweight="bold")
    plt.title(
        "Experiment H5: rare-drop-only caps vs always-reload and DP",
        fontsize=12, fontweight="bold",
    )
    plt.ylim(0, 180)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(frameon=True, fontsize=10, loc="lower left")
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Saved Experiment H5 chart to: {output_path}")


def main() -> None:
    raw = load_recheck()
    stats = summarise(raw)
    print("=== EXPERIMENT H5 (rare-drop-only caps) ===")
    print(stats.to_string(index=False))
    plot_h5(stats)


if __name__ == "__main__":
    main()
