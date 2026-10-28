"""Checks for the DP solver and the policy.json it writes.

Run from the repository root:

    python -B -m unittest discover -s dp -p 'test_*.py' -v
"""

from __future__ import annotations

import copy
import json
import statistics
import tempfile
import unittest
from functools import lru_cache
from pathlib import Path

from dp.solve import Solution, build_policy, load_session, main, success_probability
from sim.policy import load_policy, lookup_action
from sim.session import play_session

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = ROOT / "data" / "synthetic"
TOY = SYNTHETIC / "toy" / "toy_2_event_T180.json"
D_DIR = SYNTHETIC / "experiment_D_future_opportunity"
BETA = SYNTHETIC / "uncertain_odds" / "uncertain_beta_a1_b49_T030min.json"


def _event(event_id: str, p: float, g: float, c: int, f: int = 0, **extra: float) -> dict:
    event = {
        "event_id": event_id,
        "odds_type": "known",
        "p": p,
        "good_reward": g,
        "bad_reward": 0,
        "retry_seconds": c,
        "travel_seconds": f,
        "entry_cost": 0.0,
        "retained_failure_reward": 0.0,
    }
    event.update(extra)
    return event


def _session(budget: int, *events: dict) -> dict:
    return {"session_id": "test", "budget_seconds": budget, "events": list(events)}


def _brute_force_value(session: dict) -> float:
    """Session value by plain memoised recursion, independent of the table fill."""
    events = session["events"]
    n = len(events)

    @lru_cache(maxsize=None)
    def value(i: int, t: int, k: int) -> float:
        event = events[i]
        if i + 1 < n and t >= event["travel_seconds"]:
            move_on = value(i + 1, t - event["travel_seconds"], 0) - events[i + 1]["entry_cost"]
        else:
            move_on = 0.0
        q = success_probability(event, k)
        best = event["bad_reward"] + move_on
        if t >= event["retry_seconds"]:
            best = max(best, event["retained_failure_reward"]
                       + value(i, t - event["retry_seconds"], k + 1))
        return q * (event["good_reward"] + move_on) + (1 - q) * best

    return value(0, session["budget_seconds"], 0) - events[0]["entry_cost"]


def _cutoff(solution: Solution, i: int) -> int:
    """Lowest t above which the DP always retries."""
    row = solution.retry_map(i)
    t = len(row) - 1
    while t > 0 and row[t - 1]:
        t -= 1
    return t


class SolverTests(unittest.TestCase):
    def test_single_event_matches_geometric_closed_form(self) -> None:
        # Alone, retrying is always worth it: V = g (1 - (1-p)^(floor(T/c) + 1)).
        solution = Solution(_session(95, _event("E1", 0.3, 10, 20)))
        self.assertAlmostEqual(solution.expected_value, 10 * (1 - 0.7 ** 5))
        self.assertEqual(solution.retry_map(0), [t >= 20 for t in range(96)])

    def test_tables_match_brute_force_recursion(self) -> None:
        session = _session(
            240,
            _event("E1", 0.1, 10, 20, f=15, entry_cost=1.0),
            _event("E2", 0.5, 8, 10, f=30, retained_failure_reward=0.5),
            _event("E3", 0.25, 30, 25, bad_reward=2, entry_cost=2.0),
        )
        self.assertAlmostEqual(Solution(session).expected_value, _brute_force_value(session))

    def test_beta_tables_match_brute_force_recursion(self) -> None:
        session = _session(
            200,
            {**_event("E1", 0.0, 25, 15, f=20), "odds_type": "beta", "alpha": 1, "beta": 4},
            _event("E2", 0.4, 10, 20),
        )
        self.assertAlmostEqual(Solution(session).expected_value, _brute_force_value(session))

    def test_beta_posterior_mean(self) -> None:
        event = {"odds_type": "beta", "alpha": 1, "beta": 49}
        self.assertAlmostEqual(success_probability(event, 0), 0.02)
        self.assertAlmostEqual(success_probability(event, 50), 0.01)

    def test_retry_allowed_when_time_left_equals_retry_seconds(self) -> None:
        # Matches sim/session.py: retry while time_left >= retry_seconds.
        solution = Solution(_session(20, _event("E1", 0.5, 10, 20)))
        self.assertTrue(solution.retry_map(0)[20])
        self.assertFalse(solution.retry_map(0)[19])

    def test_unreachable_next_event_is_worth_nothing(self) -> None:
        session = _session(50, _event("E1", 0.5, 1, 10, f=60), _event("E2", 1.0, 100, 10))
        self.assertAlmostEqual(Solution(session).expected_value, _brute_force_value(session))
        self.assertLess(Solution(session).expected_value, 1.0)


class FindingsTests(unittest.TestCase):
    def test_toy_retries_first_event_until_forty_seconds_left(self) -> None:
        solution = Solution(load_session(TOY))
        self.assertEqual(_cutoff(solution, 0), 40)
        self.assertFalse(solution.retry_map(0)[39])

    def test_experiment_d_cutoff_moves_once_but_not_with_reward(self) -> None:
        removed = Solution(load_session(D_DIR / "D_future_removed.json"))
        self.assertEqual(_cutoff(removed, 0), 275)
        rows = [Solution(load_session(D_DIR / f"D_future_reward_{r:02d}.json")).retry_map(0)
                for r in (8, 20, 40, 80)]
        self.assertEqual(_cutoff(Solution(load_session(D_DIR / "D_future_reward_08.json")), 0), 325)
        for row in rows[1:]:
            self.assertEqual(row, rows[0])

    def test_h5_session_never_retries_beta_event(self) -> None:
        solution = Solution(load_session(BETA))
        index = next(i for i, e in enumerate(solution.events) if e.get("odds_type") == "beta")
        self.assertFalse(any(any(row) for row in solution.retry[index]))


class PolicyFileTests(unittest.TestCase):
    def test_rules_reproduce_retry_tables_through_sim_reader(self) -> None:
        for path in (TOY, D_DIR / "D_future_reward_80.json", BETA):
            session = load_session(path)
            # Make the Beta event worth retrying so its k-groups are exercised.
            for event in session["events"]:
                if event.get("odds_type") == "beta":
                    event["alpha"], event["beta"], event["retry_seconds"] = 2, 8, 30
            solution = Solution(session)
            policy = build_policy(session)
            for i, event in enumerate(solution.events):
                for k in range(len(solution.retry[i]) + 2):
                    expected = solution.retry_map(i, k)
                    for t in range(solution.budget + 1):
                        action = lookup_action(policy, event["event_id"], t, k)
                        self.assertEqual(action == "retry", expected[t], (path.name, i, k, t))

    def test_cli_writes_policy_the_simulator_loads_and_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            main([str(TOY), "--out", tmp])
            policy = load_policy(Path(tmp) / "toy_2_event_T180.policy.json")
        session = json.loads(TOY.read_text(encoding="utf-8"))
        rewards = [play_session(copy.deepcopy(session), "dp", seed, policy=policy)["reward"]
                   for seed in range(4000)]
        mean = statistics.fmean(rewards)
        se = statistics.stdev(rewards) / len(rewards) ** 0.5
        self.assertLess(abs(mean - policy["expected_value"]), 4 * se)


if __name__ == "__main__":
    unittest.main()
