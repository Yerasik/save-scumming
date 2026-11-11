"""Report figure: the DP's retry rule for the rare drop, known odds vs Beta priors.

From the repository root:

    python -B -m dp.report_figure

Writes ``dp/out/figures/report_policy_map.png`` (and a ``.pdf`` for LaTeX).

One panel per H5 session. Each panel is a map of the rare-drop decision after a
failed roll: x is how many rolls have already failed, y is seconds left in the
session. Blue = the DP retries, grey = it accepts the miss and moves on to the
later event. The black line is the path a player actually walks from a full
30-minute budget (each retry costs 20 s); the dot is where the DP gives up.
All four priors have the same mean (2%), so any difference comes from how sure
the player is about that 2%.

The thin stripes near the bottom are real, not noise: the later event's retries
cost 30 s and the rare drop's cost 20 s, so whether one more reload eats a whole
later retry flips every 20 s. The path never goes there except at the very end.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from dp.solve import Solution, load_session

ACCEPT_COLOR = "#e8e8e8"
RETRY_COLOR = "#2b6cb0"
INK = "#1a1a1a"
MUTED = "#555555"
CMAP = ListedColormap([ACCEPT_COLOR, RETRY_COLOR])

PANELS = [
    ("H5_known_p0p02", "Known odds\np = 0.02"),
    ("H5_beta_a20_b980", "Confident prior\nBeta(20, 980)"),
    ("H5_beta_a1_b49", "Rough guess\nBeta(1, 49)"),
    ("H5_beta_a0p2_b9p8", "Very unsure\nBeta(0.2, 9.8)"),
]
SESSION_DIR = Path("experiments/sessions/H5")
MAX_K = 90


def retry_grid(solution: Solution, i: int, max_k: int) -> list[list[int]]:
    """Rows are failures k = 0..max_k, columns are seconds left 0..T."""
    return [[1 if r else 0 for r in solution.retry_map(i, k)] for k in range(max_k + 1)]


def walk_path(solution: Solution, i: int) -> tuple[list[int], list[int]]:
    """Failures and seconds left along the path from a full budget, until the DP stops."""
    cost = int(solution.events[i]["retry_seconds"])
    t, k = solution.budget, 0
    ks, ts = [k], [t]
    while t >= cost and solution.retry_map(i, k)[t]:
        t -= cost
        k += 1
        ks.append(k)
        ts.append(t)
    return ks, ts


def draw(out: Path) -> list[Path]:
    fig, axes = plt.subplots(1, len(PANELS), figsize=(12, 4.2), sharey=True)
    for ax, (sid, label) in zip(axes, PANELS):
        solution = Solution(load_session(SESSION_DIR / f"{sid}.json"))
        grid = retry_grid(solution, 0, MAX_K)
        budget = solution.budget
        cost = int(solution.events[0]["retry_seconds"])
        # Only times a player can reach at the first event: full budget minus
        # whole retries. (Other seconds just show the 1-second rounding of the DP.)
        times = list(range(budget, -1, -cost))[::-1]
        image = [[grid[k][t] for k in range(MAX_K + 1)] for t in times]
        half = cost / 2
        ax.imshow(image, origin="lower", aspect="auto", cmap=CMAP, vmin=0, vmax=1,
                  interpolation="nearest",
                  extent=(-0.5, MAX_K + 0.5, times[0] - half, times[-1] + half))

        ks, ts = walk_path(solution, 0)
        ax.plot(ks, ts, color=INK, linewidth=2)
        ax.plot(ks[-1], ts[-1], "o", color=INK, markersize=8,
                markeredgecolor="white", markeredgewidth=2)
        attempts = ks[-1] + 1
        ax.annotate(f"gives up after\n{attempts} rolls", (ks[-1], ts[-1]),
                    xytext=(-20, 14), textcoords="offset points", fontsize=9, color=INK,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.9))

        ax.set_title(f"{label}\nexpected reward {solution.expected_value:.0f}",
                     fontsize=10, color=INK)
        ax.set_xlabel("failed rolls so far", fontsize=9, color=MUTED)
        ax.set_xlim(-0.5, MAX_K + 0.5)
        ax.tick_params(labelsize=8, colors=MUTED)
        for spine in ax.spines.values():
            spine.set_visible(False)

    axes[0].set_ylabel("seconds left in the session", fontsize=9, color=MUTED)
    fig.legend(handles=[Patch(color=RETRY_COLOR, label="DP reloads"),
                        Patch(color=ACCEPT_COLOR, label="DP accepts and moves on"),
                        plt.Line2D([], [], color=INK, linewidth=2,
                                   label="path from a full 30-min budget")],
               loc="lower center", ncol=3, frameon=False, fontsize=9,
               bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("When to stop reloading a 2% rare drop: same average odds, different certainty",
                 fontsize=11, color=INK)
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))

    out.parent.mkdir(parents=True, exist_ok=True)
    paths = [out, out.with_suffix(".pdf")]
    for path in paths:
        fig.savefig(path, dpi=200)
    plt.close(fig)
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Draw the report policy-map figure.")
    parser.add_argument("--out", type=Path, default=Path("dp/out/figures/report_policy_map.png"))
    args = parser.parse_args(argv)
    for path in draw(args.out):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
