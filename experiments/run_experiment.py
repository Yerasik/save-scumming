"""Run one experiment config end to end: DP policy, then the simulator.

For each session in the config this writes

    dp/out/<session_id>.policy.json
    sim/out/<experiment>/<session_id>.csv

using the same seeds 0 .. N-1 for every strategy. Sessions with Beta odds get a
policy but are not simulated until the simulator supports Beta (week 6).

From the repository root:

    python -B experiments/run_experiment.py experiments/configs/D_future_opportunity.json
    python -B experiments/run_experiment.py experiments/configs/A_budget.json --seeds 2000
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dp.solve import build_policy, load_session  # noqa: E402
from sim import run as sim_run  # noqa: E402

REQUIRED_KEYS = ("experiment", "question", "varied_factor", "sessions", "strategies", "seeds")


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        config = json.load(handle)
    missing = [key for key in REQUIRED_KEYS if key not in config]
    if missing:
        raise SystemExit(f"{path}: config is missing {missing}")
    return config


def has_beta(session: dict[str, Any]) -> bool:
    return any(event.get("odds_type", "known") == "beta" for event in session["events"])


def run(config: dict[str, Any], seeds: int, policy_dir: Path, sim_dir: Path) -> None:
    sim_out = sim_dir / str(config["experiment"])
    policy_dir.mkdir(parents=True, exist_ok=True)
    strategies = ",".join(config["strategies"])
    for relative in config["sessions"]:
        session_path = ROOT / relative
        session = load_session(session_path)
        session_id = session["session_id"]

        policy = build_policy(session)
        policy_path = policy_dir / f"{session_id}.policy.json"
        with policy_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(policy, handle, indent=2)
            handle.write("\n")
        print(f"{session_id}: DP E[reward] = {policy['expected_value']:.4f}")

        if has_beta(session):
            print("  skipped simulation: Beta odds not supported by sim/ yet")
            continue
        csv_path = sim_out / f"{session_id}.csv"
        sim_run.main(
            [
                "--session", str(session_path),
                "--policy", str(policy_path),
                "--strategies", strategies,
                "--seeds", str(seeds),
                "--out", str(csv_path),
            ]
        )
        print(f"  {seeds} seeds x {len(config['strategies'])} strategies -> {csv_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one experiment config.")
    parser.add_argument("config", type=Path, help="experiments/configs/<name>.json")
    parser.add_argument("--seeds", type=int, help="override the config's seed count")
    parser.add_argument("--policy-dir", type=Path, default=ROOT / "dp" / "out")
    parser.add_argument("--sim-dir", type=Path, default=ROOT / "sim" / "out")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    seeds = args.seeds if args.seeds is not None else int(config["seeds"])
    print(f"Experiment {config['experiment']}: {config['question']}")
    run(config, seeds, args.policy_dir, args.sim_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
