"""Reward-per-second (rho) baseline from Section 2.3 of the project plan.

For an event, one more retry is worthwhile exactly when

    q(k) * (g - b) + h >= rho * c

where q(k) is either the documented probability p or the posterior mean after
k failures.  For known odds, the module can also find the self-consistent rho
that maximises expected session reward divided by expected session time.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Event:
    """One event's rewards, timing, and either fixed odds or a Beta prior."""

    event_id: str
    good_reward: float
    bad_reward: float
    retry_seconds: float
    travel_seconds: float = 0.0
    entry_cost: float = 0.0
    retained_failure_reward: float = 0.0
    p: float | None = None
    alpha: float | None = None
    beta: float | None = None

    def probability(self, failures: int = 0) -> float:
        """Return fixed p or the posterior mean after this many observed failures."""
        if failures < 0:
            raise ValueError("failures must be non-negative")
        if self.p is not None:
            if not 0 < self.p <= 1:
                raise ValueError(f"{self.event_id}: p must be in (0, 1]")
            return self.p
        if self.alpha is None or self.beta is None:
            raise ValueError(f"{self.event_id}: provide p or alpha and beta")
        if self.alpha <= 0 or self.beta <= 0:
            raise ValueError(f"{self.event_id}: alpha and beta must be positive")
        # A failed attempt adds one to beta; alpha is unchanged until a success.
        return self.alpha / (self.alpha + self.beta + failures)

    def marginal_reward(self, failures: int = 0) -> float:
        """Expected reward gained by buying one more attempt after a bad outcome."""
        q = self.probability(failures)
        return q * (self.good_reward - self.bad_reward) + self.retained_failure_reward

    def reward_rate(self, failures: int = 0) -> float:
        """Express the marginal retry benefit in reward units per second."""
        if self.retry_seconds <= 0:
            raise ValueError(f"{self.event_id}: retry_seconds must be positive")
        return self.marginal_reward(failures) / self.retry_seconds

    def should_retry(self, rho: float, failures: int = 0) -> bool:
        """Retry when its expected benefit covers the time's opportunity cost."""
        if rho < 0:
            raise ValueError("rho must be non-negative")
        return self.marginal_reward(failures) >= rho * self.retry_seconds

    def expected_never_reward(self) -> float:
        """Expected reward when the first result is accepted."""
        p = self.probability(0)
        return p * self.good_reward + (1 - p) * self.bad_reward - self.entry_cost

    def retry_until_success_increment(self) -> tuple[float, float]:
        """Expected (extra reward, extra seconds) versus never retrying.

        This identity follows the plan's retained-failure convention.  It is
        valid for stationary, known odds.  With p fixed, the expected number
        of paid retries after a failed first attempt is (1-p)/p.
        """
        if self.p is None:
            raise ValueError("self-consistent rho solver requires known odds")
        p = self.probability(0)
        extra_reward = (1 - p) * (
            self.good_reward
            - self.bad_reward
            + self.retained_failure_reward / p
        )
        extra_seconds = (1 - p) * self.retry_seconds / p
        return extra_reward, extra_seconds


def event_from_mapping(item: dict[str, Any]) -> Event:
    """Load fixed or uncertain odds without assuming every JSON event has p."""
    odds_type = item.get("odds_type", "known")
    if odds_type == "known":
        p = float(item["p"])
        alpha = beta = None
    elif odds_type == "beta":
        # The beta fixture intentionally omits p, so never access item['p'] here.
        p = None
        alpha = float(item["alpha"])
        beta = float(item["beta"])
    else:
        raise ValueError(f"unknown odds_type: {odds_type}")
    return Event(
        event_id=str(item["event_id"]),
        good_reward=float(item["good_reward"]),
        bad_reward=float(item["bad_reward"]),
        retry_seconds=float(item["retry_seconds"]),
        travel_seconds=float(item.get("travel_seconds", 0.0)),
        entry_cost=float(item.get("entry_cost", 0.0)),
        retained_failure_reward=float(item.get("retained_failure_reward", 0.0)),
        p=p,
        alpha=alpha,
        beta=beta,
    )


def load_events(path: Path) -> list[Event]:
    """Keep the original public loader for teammates who only need the events."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [event_from_mapping(item) for item in payload["events"]]


def evaluate(
    events: Iterable[Event], rho: float, failures: int, *, session_id: str = ""
) -> list[dict[str, Any]]:
    """Evaluate each event and retain session identity for CSV joins."""
    rows = []
    for item in events:
        probability = item.probability(failures)
        rate = item.reward_rate(failures)
        rows.append(
            {
                "session_id": session_id,
                "event_id": item.event_id,
                "failures": failures,
                "probability": probability,
                "marginal_reward": item.marginal_reward(failures),
                "retry_seconds": item.retry_seconds,
                "reward_per_second": rate,
                "rho": rho,
                "action": "retry" if item.should_retry(rho, failures) else "accept",
            }
        )
    return rows


def solve_self_consistent_rho(
    events: Iterable[Event],
    *,
    fixed_reward: float = 0.0,
    fixed_seconds: float = 0.0,
    tolerance: float = 1e-12,
    max_iterations: int = 100,
    session_id: str = "",
) -> tuple[float, list[dict[str, Any]]]:
    """Maximise expected reward/second over all-or-nothing retry choices.

    The mandatory first attempts contribute their expected rewards.  Travel
    times plus ``fixed_seconds`` provide the time that is spent regardless of
    retry choices.  Dinkelbach iterations select every retry option whose
    incremental reward minus rho times incremental time is non-negative.
    """
    event_list = list(events)
    if fixed_seconds < 0:
        raise ValueError("fixed_seconds must be non-negative")
    base_reward = fixed_reward + sum(item.expected_never_reward() for item in event_list)
    base_seconds = fixed_seconds + sum(item.travel_seconds for item in event_list)
    increments = [item.retry_until_success_increment() for item in event_list]
    if base_seconds <= 0 and not any(seconds > 0 for _, seconds in increments):
        raise ValueError("the session must contain positive expected time")

    rho = 0.0
    selected: list[bool] = [False] * len(event_list)
    for _ in range(max_iterations):
        selected = [
            extra_reward - rho * extra_seconds >= 0
            for extra_reward, extra_seconds in increments
        ]
        total_reward = base_reward + sum(
            extra_reward
            for choose, (extra_reward, _) in zip(selected, increments)
            if choose
        )
        total_seconds = base_seconds + sum(
            extra_seconds
            for choose, (_, extra_seconds) in zip(selected, increments)
            if choose
        )
        if total_seconds <= 0:
            raise ValueError(
                "zero expected session time; add travel_seconds or --fixed-seconds"
            )
        residual = total_reward - rho * total_seconds
        new_rho = total_reward / total_seconds
        rho = new_rho
        if abs(residual) <= tolerance:
            break
    else:
        raise RuntimeError("rho solver did not converge")

    rows = evaluate(event_list, rho=rho, failures=0, session_id=session_id)
    for row, choose, (extra_reward, extra_seconds) in zip(rows, selected, increments):
        row["expected_extra_reward_until_success"] = extra_reward
        row["expected_extra_seconds_until_success"] = extra_seconds
        row["action"] = "retry_until_success" if choose else "never_retry"
    return rho, rows


def print_table(rows: list[dict[str, Any]]) -> None:
    """Show compact human-readable decisions; CSV retains the full row data."""
    headings = ("event", "q(k)", "gain", "seconds", "gain/s", "rho", "action")
    print("  ".join(f"{heading:>10}" for heading in headings))
    for row in rows:
        print(
            f"{row['event_id']:>10}  "
            f"{row['probability']:>10.6f}  "
            f"{row['marginal_reward']:>10.6f}  "
            f"{row['retry_seconds']:>10.2f}  "
            f"{row['reward_per_second']:>10.6f}  "
            f"{row['rho']:>10.6f}  "
            f"{row['action']:>10}"
        )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Export the existing columns plus session_id; never rename old columns."""
    if not rows or any(not row.get("session_id") for row in rows):
        raise ValueError("CSV output requires a non-empty session_id in every row")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        # Keep line endings Git-friendly while retaining standard CSV quoting.
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    """Describe the two supported ways of supplying the opportunity-cost rate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=Path, help="synthetic session JSON")
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--rho", type=float, help="externally supplied reward per second")
    choice.add_argument(
        "--solve",
        action="store_true",
        help="solve for the self-consistent known-odds session rho",
    )
    parser.add_argument("--failures", type=int, default=0, help="failures observed at each event")
    parser.add_argument(
        "--fixed-seconds",
        type=float,
        default=0.0,
        help="time spent regardless of retry choices (used with --solve)",
    )
    parser.add_argument("--csv", type=Path, help="optional CSV output path")
    return parser


def main() -> None:
    """Read session identity once and carry it through either baseline mode."""
    args = build_parser().parse_args()
    payload = json.loads(args.session.read_text(encoding="utf-8"))
    session_id = str(payload["session_id"])
    events = [event_from_mapping(item) for item in payload["events"]]
    if args.solve:
        # Infinite-horizon self-consistency is only implemented for known odds.
        # For uncertain odds, use --rho and update --failures at each decision.
        if any(item.p is None for item in events):
            raise SystemExit("--solve requires known odds; use --rho for beta events")
        rho, rows = solve_self_consistent_rho(
            events, fixed_seconds=args.fixed_seconds, session_id=session_id
        )
        print(f"self-consistent rho = {rho:.9f} reward/second")
    else:
        rows = evaluate(events, args.rho, args.failures, session_id=session_id)
    print_table(rows)
    if args.csv:
        write_csv(args.csv, rows)


if __name__ == "__main__":
    main()
