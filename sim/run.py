"""Monte Carlo session runner.

Play one JSON session event by event under named strategies, using the same
seed list for every strategy so comparisons stay aligned.

From the repository root:

    python -B -m sim.run --session data/synthetic/toy/toy_2_event_T180.json \\
      --strategies never,always,fixed_k_2,fixed_k_3,fixed_k_5 \\
      --seeds 10000 --out sim/out/toy_sessions.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from sim.policy import load_policy
from sim.session import (
    DEFAULT_KAPPA,
    DEFAULT_REWARD_TOP_M,
    _ATTEMPT_LIMITS,
    _GREEDY_STRATEGIES,
    load_session,
    play_session,
)

_NAMED_STRATEGIES = frozenset(_ATTEMPT_LIMITS) | _GREEDY_STRATEGIES | {"dp"}

# Frozen output contract (PLAN.md). Do not rename these columns.
COLUMNS = (
    "session_id",
    "experiment",
    "strategy",
    "seed",
    "reward",
    "reloads",
    "time_reloading",
)

ROOT = Path(__file__).resolve().parents[1]
DUMMY_SESSIONS = (ROOT / "data" / "synthetic" / "dummy_sessions.csv").resolve()


def csv_number(value: float | int) -> int | float:
    """Write whole numbers without a trailing .0 so reruns match byte-for-byte."""
    if isinstance(value, bool):
        raise TypeError("boolean is not a numeric CSV field")
    as_float = float(value)
    if as_float.is_integer():
        return int(as_float)
    return as_float


def parse_strategies(text: str) -> list[str]:
    names = [part.strip() for part in text.split(",") if part.strip()]
    if not names:
        raise ValueError("at least one strategy is required")
    for name in names:
        if name not in _NAMED_STRATEGIES:
            raise ValueError(f"unsupported strategy: {name!r}")
    return names


def iter_rows(
    payload: dict[str, Any],
    strategies: list[str],
    n_seeds: int,
    policy: dict[str, Any] | None = None,
    reward_top_m: int = DEFAULT_REWARD_TOP_M,
    kappa: float = DEFAULT_KAPPA,
) -> list[dict[str, Any]]:
    """Build every (strategy, seed) row with seeds 0 .. n_seeds-1 reused in order."""
    if "dp" in strategies and policy is None:
        raise ValueError("strategy 'dp' requires a policy")
    session_id = str(payload["session_id"])
    experiment = str(payload["experiment"])
    rows: list[dict[str, Any]] = []
    for strategy in strategies:
        for seed in range(n_seeds):
            result = play_session(
                payload,
                strategy,
                seed,
                policy=policy,
                reward_top_m=reward_top_m,
                kappa=kappa,
            )
            rows.append(
                {
                    "session_id": session_id,
                    "experiment": experiment,
                    "strategy": strategy,
                    "seed": seed,
                    "reward": csv_number(result["reward"]),
                    "reloads": result["reloads"],
                    "time_reloading": csv_number(result["time_reloading"]),
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write LF-terminated CSV so a second run is byte-identical on any OS."""
    resolved = path.resolve()
    if resolved == DUMMY_SESSIONS:
        raise SystemExit("refusing to overwrite data/synthetic/dummy_sessions.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COLUMNS), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True, help="session JSON")
    parser.add_argument(
        "--strategies",
        required=True,
        help="comma-separated strategy names (never, always, fixed_k_2, ...)",
    )
    parser.add_argument(
        "--seeds",
        type=int,
        required=True,
        help="use seeds 0 .. N-1 for every strategy",
    )
    parser.add_argument("--out", type=Path, required=True, help="output sessions.csv")
    parser.add_argument(
        "--policy",
        type=Path,
        help="policy JSON for strategy dp; the simulator does not solve DP",
    )
    parser.add_argument(
        "--reward-top-m",
        type=int,
        default=DEFAULT_REWARD_TOP_M,
        help="reward_greedy: how many top (g-b) events to retry (default 1)",
    )
    parser.add_argument(
        "--kappa",
        type=float,
        default=DEFAULT_KAPPA,
        help="efficiency_greedy: minimum p*(g-b)/c (default 0.10)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.seeds < 0:
        raise SystemExit("--seeds must be non-negative")
    if args.reward_top_m < 1:
        raise SystemExit("--reward-top-m must be at least 1")
    try:
        payload = load_session(args.session)
    except ValueError as exc:
        if str(exc) == "Beta is week 6":
            raise SystemExit("Beta is week 6") from None
        raise
    strategies = parse_strategies(args.strategies)
    policy = load_policy(args.policy) if args.policy is not None else None
    if "dp" in strategies and policy is None:
        raise SystemExit("strategy 'dp' requires --policy")
    rows = iter_rows(
        payload,
        strategies,
        args.seeds,
        policy=policy,
        reward_top_m=args.reward_top_m,
        kappa=args.kappa,
    )
    write_csv(args.out, rows)


if __name__ == "__main__":
    main()
