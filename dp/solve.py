"""Finite-horizon DP for the accept-or-retry problem, and a policy.json writer.

Standard library only. Implements the recursion in the project plan
(``COMP1110_Project_Plan.tex``, section "Main setting"):

    N(i, t)    = V(i+1, t - f_i, 0) - e_{i+1}   if t >= f_i and i < n, else 0
    W(i, t, k) = max{ b_i + N(i, t),  h_i + V(i, t - c_i, k+1) }
    V(i, t, k) = q_i(k) (g_i + N(i, t)) + (1 - q_i(k)) W(i, t, k)

Session value is ``V(1, T, 0) - e_1``. Time is in whole seconds.

Two choices follow ``sim/session.py`` rather than the printed plan, so the
simulator playing this policy earns the DP's expected value:

- A retry is allowed when ``t >= c_i`` (the plan prints ``t > c_i``).
- Ties go to ``accept``.

Known odds: ``q_i(k) = p``, so the action does not depend on ``k``.
Beta odds: ``q_i(k) = alpha / (alpha + beta + k)`` after ``k`` failures.

From the repository root:

    python -B -m dp.solve data/synthetic/toy/toy_2_event_T180.json
    python -B -m dp.solve data/synthetic --out dp/out
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
# Stand-in for "any failure count" on known-odds rules.
ANY_FAILURES = 1_000_000
# Retry must beat accept by more than this to be chosen.
TIE_TOLERANCE = 1e-9


def _whole_seconds(value: float, name: str) -> int:
    if float(value) != int(value) or value < 0:
        raise ValueError(f"{name} must be a non-negative whole number of seconds, got {value!r}")
    return int(value)


def success_probability(event: dict[str, Any], failures: int) -> float:
    """``q_i(k)``: the chance the next attempt succeeds after ``failures`` failures."""
    odds_type = event.get("odds_type", "known")
    if odds_type == "known":
        return float(event["p"])
    if odds_type == "beta":
        alpha = float(event["alpha"])
        beta = float(event["beta"])
        return alpha / (alpha + beta + failures)
    raise ValueError(f"event {event.get('event_id')!r} has unsupported odds_type {odds_type!r}")


class Solution:
    """Filled DP tables for one session.

    ``value[i][k][t]`` is ``V(i, t, k)``. ``retry[i][k][t]`` is True when the
    best action after a failure at event ``i`` with ``t`` seconds left and
    ``k`` earlier failures is to retry. Known-odds events store ``k = 0`` only.
    """

    def __init__(self, session: dict[str, Any]) -> None:
        self.session = session
        self.events: list[dict[str, Any]] = session["events"]
        self.budget = _whole_seconds(session["budget_seconds"], "budget_seconds")
        self.value: list[list[list[float]]] = [[] for _ in self.events]
        self.retry: list[list[list[bool]]] = [[] for _ in self.events]
        self._solve()

    def _move_on(self, i: int) -> list[float]:
        """``N(i, t)`` for every ``t`` in ``0..T``."""
        budget = self.budget
        if i + 1 >= len(self.events):
            return [0.0] * (budget + 1)
        travel = _whole_seconds(self.events[i]["travel_seconds"], "travel_seconds")
        entry = float(self.events[i + 1]["entry_cost"])
        later = self.value[i + 1][0]
        return [later[t - travel] - entry if t >= travel else 0.0 for t in range(budget + 1)]

    def _solve(self) -> None:
        budget = self.budget
        for i in range(len(self.events) - 1, -1, -1):
            event = self.events[i]
            cost = _whole_seconds(event["retry_seconds"], "retry_seconds")
            if cost <= 0:
                raise ValueError("retry_seconds must be positive")
            g = float(event["good_reward"])
            b = float(event["bad_reward"])
            h = float(event["retained_failure_reward"])
            move_on = self._move_on(i)
            known = event.get("odds_type", "known") == "known"
            # Deepest failure count that can still pay for a retry.
            max_k = 0 if known else budget // cost

            values = [[0.0] * (budget + 1) for _ in range(max_k + 1)]
            retries = [[False] * (budget + 1) for _ in range(max_k + 1)]
            for k in range(max_k, -1, -1):
                q = success_probability(event, k)
                # Known odds: k+1 has the same value table as k.
                next_k = k if known else k + 1
                for t in range(budget + 1):
                    accept = b + move_on[t]
                    best = accept
                    if t >= cost and next_k <= max_k:
                        retry = h + values[next_k][t - cost]
                        if retry > accept + TIE_TOLERANCE:
                            best = retry
                            retries[k][t] = True
                    values[k][t] = q * (g + move_on[t]) + (1.0 - q) * best
            self.value[i] = values
            self.retry[i] = retries

    @property
    def expected_value(self) -> float:
        """``V(1, T, 0) - e_1``."""
        return self.value[0][0][self.budget] - float(self.events[0]["entry_cost"])

    def retry_map(self, i: int, failures: int = 0) -> list[bool]:
        """Retry-or-accept for every ``t`` in ``0..T`` at event ``i``."""
        table = self.retry[i]
        if self.events[i].get("odds_type", "known") == "known":
            return table[0]
        if failures >= len(table):
            return [False] * (self.budget + 1)
        return table[failures]


def _segments(row: list[bool]) -> list[tuple[int, bool]]:
    """Split a ``t -> retry`` row into ``(start_t, retry)`` runs, highest start first."""
    runs: list[tuple[int, bool]] = []
    for t, retry in enumerate(row):
        if not runs or runs[-1][1] != retry:
            runs.append((t, retry))
    return runs[::-1]


def policy_rules(solution: Solution) -> list[dict[str, Any]]:
    """Encode the retry tables as first-match rules for ``sim/policy.py``.

    For each event, rules are grouped by failure count (lowest first). Each
    group covers every ``t >= 0`` with thresholds from high to low, so the
    first rule with ``time_left >= min_time_left`` is the run holding
    ``time_left``. A group with ``max_failures = m`` is only reached by
    failure counts no earlier group caught. Consecutive failure counts with
    the same row share one group. Failure counts past the table cannot pay
    for a retry and fall through to ``default_action = accept``.
    """
    rules: list[dict[str, Any]] = []
    for i, event in enumerate(solution.events):
        table = solution.retry[i]
        known = event.get("odds_type", "known") == "known"
        groups: list[tuple[int, list[bool]]] = []
        for k, row in enumerate(table):
            if groups and groups[-1][1] == row:
                groups[-1] = (k, row)
            else:
                groups.append((k, row))
        for last_k, row in groups:
            # A trailing accept-everywhere group adds nothing over the
            # default. Earlier ones stay, or later groups would catch them.
            if not known and last_k == len(table) - 1 and not any(row):
                continue
            max_failures = ANY_FAILURES if known else last_k
            for start, retry in _segments(row):
                rules.append(
                    {
                        "event_id": event["event_id"],
                        "min_time_left": start,
                        "max_failures": max_failures,
                        "action": "retry" if retry else "accept",
                    }
                )
    return rules


def build_policy(session: dict[str, Any]) -> dict[str, Any]:
    """Solve ``session`` and return a policy dict in the ``sim/policy.py`` shape."""
    solution = Solution(session)
    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": session["session_id"],
        "default_action": "accept",
        "rules": policy_rules(solution),
        # Extra keys below are ignored by sim/policy.py.
        "solver": "dp.solve",
        "budget_seconds": solution.budget,
        "expected_value": round(solution.expected_value, 6),
    }


def load_session(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        session = json.load(handle)
    for key in ("session_id", "budget_seconds", "events"):
        if key not in session:
            raise KeyError(f"{path}: session is missing {key!r}")
    return session


def session_paths(target: Path) -> list[Path]:
    """One file, or every session JSON under a folder (skipping manifests)."""
    if target.is_file():
        return [target]
    paths = []
    for path in sorted(target.rglob("*.json")):
        with path.open(encoding="utf-8") as handle:
            if "events" in json.load(handle):
                paths.append(path)
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Solve session JSON and write policy.json files.")
    parser.add_argument("target", type=Path, help="session JSON file or folder of them")
    parser.add_argument("--out", type=Path, default=Path("dp/out"), help="output folder")
    args = parser.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    for path in session_paths(args.target):
        policy = build_policy(load_session(path))
        out_path = args.out / f"{policy['session_id']}.policy.json"
        with out_path.open("w", encoding="utf-8") as handle:
            json.dump(policy, handle, indent=2)
            handle.write("\n")
        print(f"{policy['session_id']}: E[reward] = {policy['expected_value']:.4f} -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
