"""Draw the policy map: retry or accept for each event and time left.

One PNG per session. Each row is an event, the x axis is seconds left, and a
cell is shaded where the DP retries after a failure (first failure, k = 0).
Beta-odds events also get a second PNG with failures on the y axis.

From the repository root:

    python -B -m dp.plot_policy data/synthetic/toy/toy_2_event_T180.json
    python -B -m dp.plot_policy data/synthetic --out dp/out/figures
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from dp.solve import Solution, load_session, session_paths

ACCEPT_COLOR = "#e8e8e8"
RETRY_COLOR = "#2b6cb0"
CMAP = ListedColormap([ACCEPT_COLOR, RETRY_COLOR])


def plot_session(solution: Solution, out_dir: Path) -> list[Path]:
    """Write the policy-map figure(s) for one solved session."""
    session_id = solution.session["session_id"]
    events = solution.events
    budget = solution.budget
    grid = [[1 if retry else 0 for retry in solution.retry_map(i)] for i in range(len(events))]

    fig, ax = plt.subplots(figsize=(9, 0.45 * len(events) + 1.6))
    ax.imshow(grid, aspect="auto", cmap=CMAP, vmin=0, vmax=1, interpolation="nearest",
              extent=(-0.5, budget + 0.5, len(events) - 0.5, -0.5))
    ax.set_yticks(range(len(events)))
    ax.set_yticklabels([event["event_id"] for event in events])
    ax.set_xlabel("seconds left (at the decision, after a failure)")
    ax.set_title(f"{session_id}: DP policy after the first failure  "
                 f"(E[reward] = {solution.expected_value:.2f})", fontsize=10)
    ax.legend(handles=[Patch(color=RETRY_COLOR, label="retry"),
                       Patch(color=ACCEPT_COLOR, label="accept")],
              loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False)
    fig.tight_layout()
    paths = [out_dir / f"{session_id}.policy.png"]
    fig.savefig(paths[0], dpi=150)
    plt.close(fig)

    for i, event in enumerate(events):
        if event.get("odds_type", "known") != "beta":
            continue
        table = [[1 if retry else 0 for retry in row] for row in solution.retry[i]]
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.imshow(table, aspect="auto", origin="lower", cmap=CMAP, vmin=0, vmax=1,
                  interpolation="nearest", extent=(-0.5, budget + 0.5, -0.5, len(table) - 0.5))
        ax.set_xlabel("seconds left")
        ax.set_ylabel("failures so far (k)")
        ax.set_title(f"{session_id} / {event['event_id']}: Beta({event['alpha']}, {event['beta']}) "
                     "retry map", fontsize=10)
        fig.tight_layout()
        path = out_dir / f"{session_id}.{event['event_id']}.beta.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        paths.append(path)
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Draw DP policy maps.")
    parser.add_argument("target", type=Path, help="session JSON file or folder of them")
    parser.add_argument("--out", type=Path, default=Path("dp/out/figures"), help="output folder")
    args = parser.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    for path in session_paths(args.target):
        for written in plot_session(Solution(load_session(path)), args.out):
            print(written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
