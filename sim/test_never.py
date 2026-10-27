"""Seeded reload strategies on the toy session.

Run from the repository root:

    python -B -m unittest discover -s sim -p 'test_*.py' -v
"""

from __future__ import annotations

import copy
import json
import random
import unittest
from pathlib import Path

from sim.session import load_session, play_session

ROOT = Path(__file__).resolve().parents[1]
TOY = ROOT / "data" / "synthetic" / "toy" / "toy_2_event_T180.json"
STRATEGIES = ("never", "always", "fixed_k_2", "fixed_k_3", "fixed_k_5")


def _manual_never(session: dict, seed: int) -> float:
    """Replay the same rolls outside play_session."""
    rng = random.Random(seed)
    clock = session["budget_seconds"]
    reward = 0.0
    events = session["events"]
    for index, event in enumerate(events):
        reward -= event["entry_cost"]
        if rng.random() < event["p"]:
            reward += event["good_reward"]
        else:
            reward += event["bad_reward"]
        if index + 1 == len(events):
            break
        if clock < event["travel_seconds"]:
            break
        clock -= event["travel_seconds"]
    return reward


class NeverSessionTest(unittest.TestCase):
    def test_seeded_run_is_deterministic(self) -> None:
        session = load_session(TOY)
        raw = json.loads(TOY.read_text(encoding="utf-8"))
        self.assertEqual(session, raw)
        self.assertEqual(session["budget_seconds"], 180)
        self.assertEqual(session["events"][0]["entry_cost"], 0.0)
        self.assertEqual(session["events"][0]["retained_failure_reward"], 0.0)

        untouched = copy.deepcopy(session)
        # Seeds 0 and 4 are a failing pair and a pair that clears E2.
        outcomes = {}
        for seed in (0, 4):
            first = play_session(session, "never", seed)
            second = play_session(session, "never", seed)
            self.assertEqual(first, second)
            self.assertEqual(first["reloads"], 0)
            self.assertEqual(first["time_reloading"], 0.0)
            self.assertEqual(first["reward"], _manual_never(session, seed))
            self.assertEqual(
                first["reached"],
                [
                    {"event_id": "E1", "reached": True},
                    {"event_id": "E2", "reached": True},
                ],
            )
            outcomes[seed] = first
        self.assertEqual(session, untouched)
        self.assertNotEqual(outcomes[0], outcomes[4])

    def test_travel_and_entry_cost_are_applied(self) -> None:
        base = load_session(TOY)

        blocked = copy.deepcopy(base)
        blocked["events"][0]["travel_seconds"] = 181
        blocked["events"][0]["entry_cost"] = 1.5
        blocked["events"][0]["good_reward"] = 0
        blocked["events"][0]["bad_reward"] = 0
        blocked["events"][0]["retained_failure_reward"] = 99
        blocked["events"][1]["entry_cost"] = 4
        blocked["events"][1]["good_reward"] = 100
        blocked["events"][1]["bad_reward"] = 100
        blocked_result = play_session(blocked, "never", seed=3)
        self.assertEqual(blocked_result["reward"], -1.5)
        self.assertEqual(blocked_result["reloads"], 0)
        self.assertEqual(blocked_result["time_reloading"], 0.0)
        self.assertEqual(
            [row["reached"] for row in blocked_result["reached"]],
            [True, False],
        )

        exact = copy.deepcopy(base)
        exact["events"][0]["travel_seconds"] = exact["budget_seconds"]
        exact["events"][0]["entry_cost"] = 1.5
        exact["events"][0]["good_reward"] = 0
        exact["events"][0]["bad_reward"] = 0
        exact["events"][1]["entry_cost"] = 4
        exact["events"][1]["good_reward"] = 0
        exact["events"][1]["bad_reward"] = 0
        exact_result = play_session(exact, "never", seed=3)
        self.assertEqual(exact_result["reward"], -5.5)
        self.assertEqual(
            [row["reached"] for row in exact_result["reached"]],
            [True, True],
        )

        # 180 - 20 retry would leave 160, which cannot pay 170. The first
        # attempt is free, so E2 is still reached.
        free_attempt = copy.deepcopy(base)
        free_attempt["events"][0]["retry_seconds"] = 20
        free_attempt["events"][0]["travel_seconds"] = 170
        free_result = play_session(free_attempt, "never", seed=0)
        self.assertEqual(
            [row["reached"] for row in free_result["reached"]],
            [True, True],
        )

    def test_other_strategy_is_refused(self) -> None:
        session = load_session(TOY)
        with self.assertRaises(ValueError):
            play_session(session, "dp", seed=0)
        with self.assertRaises(ValueError):
            play_session(session, "fixed_k_4", seed=0)

    def test_seeded_strategies_are_deterministic(self) -> None:
        session = load_session(TOY)
        for strategy in STRATEGIES:
            for seed in (0, 4):
                self.assertEqual(
                    play_session(session, strategy, seed),
                    play_session(session, strategy, seed),
                )
        # Seed 0 fails E1's free attempt, so every reloading strategy pays
        # at least that event's retry_seconds. Travel is 0, so E2 is reached.
        never = play_session(session, "never", 0)
        self.assertEqual(never["reloads"], 0)
        self.assertEqual(never["time_reloading"], 0.0)
        for strategy in STRATEGIES[1:]:
            result = play_session(session, strategy, 0)
            self.assertGreaterEqual(result["reloads"], 1)
            self.assertGreaterEqual(result["time_reloading"], 20)
            self.assertEqual(
                [row["reached"] for row in result["reached"]],
                [True, True],
            )
        self.assertLessEqual(play_session(session, "fixed_k_2", 0)["reloads"], 2)
        self.assertLessEqual(play_session(session, "fixed_k_3", 0)["reloads"], 4)
        self.assertLessEqual(play_session(session, "fixed_k_5", 0)["reloads"], 8)

    def test_attempt_cap_time_gate_and_retained_reward(self) -> None:
        """Every roll fails. Caps and the clock decide how many retries pay h."""
        session = copy.deepcopy(load_session(TOY))
        session["budget_seconds"] = 180
        session["events"][0].update(
            {
                "p": 0,
                "good_reward": 10,
                "bad_reward": 3,
                "retained_failure_reward": 1,
                "retry_seconds": 20,
                "entry_cost": 0.5,
                "travel_seconds": 0,
            }
        )
        session["events"][1].update(
            {
                "p": 0,
                "good_reward": 8,
                "bad_reward": 0,
                "retained_failure_reward": 0,
                "retry_seconds": 10,
                "entry_cost": 0,
                "travel_seconds": 0,
            }
        )

        def played(strategy: str) -> dict:
            return play_session(session, strategy, seed=0)

        self.assertEqual(played("never")["reward"], 2.5)
        self.assertEqual(played("never")["reloads"], 0)
        self.assertEqual(played("never")["time_reloading"], 0.0)

        # E1 may retry 9 times (180 / 20). E2 then has no time left.
        always = played("always")
        self.assertEqual(always["reward"], 11.5)
        self.assertEqual(always["reloads"], 9)
        self.assertEqual(always["time_reloading"], 180)
        self.assertEqual([row["reached"] for row in always["reached"]], [True, True])

        # Retries per event are N - 1. E2's retry costs 10 and still fits
        # after E1, so each event uses its full cap.
        self.assertEqual(played("fixed_k_2")["reloads"], 2)
        self.assertEqual(played("fixed_k_2")["time_reloading"], 30)
        self.assertEqual(played("fixed_k_2")["reward"], 3.5)
        self.assertEqual(played("fixed_k_3")["reloads"], 4)
        self.assertEqual(played("fixed_k_3")["time_reloading"], 60)
        self.assertEqual(played("fixed_k_3")["reward"], 4.5)
        self.assertEqual(played("fixed_k_5")["reloads"], 8)
        self.assertEqual(played("fixed_k_5")["time_reloading"], 120)
        self.assertEqual(played("fixed_k_5")["reward"], 6.5)

        # time_left == retry_seconds still retries once, then stops.
        tight = copy.deepcopy(session)
        tight["budget_seconds"] = 20
        tight_always = play_session(tight, "always", seed=1)
        tight_fixed = play_session(tight, "fixed_k_5", seed=1)
        self.assertEqual(tight_always["reloads"], 1)
        self.assertEqual(tight_always["time_reloading"], 20)
        self.assertEqual(tight_always["reward"], 3.5)
        self.assertEqual(tight_fixed["reloads"], 1)
        self.assertEqual(tight_fixed["reward"], 3.5)

        short = copy.deepcopy(session)
        short["budget_seconds"] = 19
        short["events"][1]["retry_seconds"] = 100
        short_result = play_session(short, "always", seed=1)
        self.assertEqual(short_result["reloads"], 0)
        self.assertEqual(short_result["time_reloading"], 0.0)
        self.assertEqual(short_result["reward"], 2.5)

        # Two E1 retries leave 10 seconds, which cannot pay travel of 40.
        blocked = copy.deepcopy(session)
        blocked["budget_seconds"] = 50
        blocked["events"][0]["travel_seconds"] = 40
        blocked["events"][0]["entry_cost"] = 0
        blocked["events"][1]["entry_cost"] = 4
        blocked["events"][1]["bad_reward"] = 100
        blocked_result = play_session(blocked, "always", seed=2)
        self.assertEqual(blocked_result["reloads"], 2)
        self.assertEqual(blocked_result["time_reloading"], 40)
        self.assertEqual(blocked_result["reward"], 5)
        self.assertEqual(
            [row["reached"] for row in blocked_result["reached"]],
            [True, False],
        )


if __name__ == "__main__":
    unittest.main()
