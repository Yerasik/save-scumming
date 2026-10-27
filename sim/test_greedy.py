"""Reward-greedy and efficiency-greedy rules. Known odds only.

Run from the repository root:

    python -B -m unittest discover -s sim -p 'test_*.py' -v
"""

from __future__ import annotations

import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sim.session import (
    efficiency_rate,
    load_session,
    play_session,
    remaining_travel,
    top_m_event_ids,
)

ROOT = Path(__file__).resolve().parents[1]
TOY = ROOT / "data" / "synthetic" / "toy" / "toy_2_event_T180.json"
BETA = ROOT / "data" / "synthetic" / "uncertain_odds" / "uncertain_beta_a1_b49_T030min.json"


class GreedyStrategyTests(unittest.TestCase):
    def test_reward_greedy_retries_only_top_m(self) -> None:
        session = copy.deepcopy(load_session(TOY))
        session["events"][0]["p"] = 0
        session["events"][1]["p"] = 0
        self.assertEqual(top_m_event_ids(session["events"], 1), {"E1"})
        # E1 spread is 10, E2 is 8. m=1 retries E1 until the clock is spent;
        # travel is 0, so E2 is still reached and then accepted.
        top_one = play_session(session, "reward_greedy", seed=0, reward_top_m=1)
        self.assertEqual(top_one["reloads"], 9)
        self.assertEqual(top_one["time_reloading"], 180)
        self.assertEqual([row["reached"] for row in top_one["reached"]], [True, True])
        top_two = play_session(session, "reward_greedy", seed=0, reward_top_m=2)
        self.assertEqual(top_two["reloads"], 9)

    def test_efficiency_greedy_uses_kappa_and_reserve(self) -> None:
        session = load_session(TOY)
        # E1: 0.1*10/20 = 0.05; E2: 0.5*8/10 = 0.40
        self.assertAlmostEqual(efficiency_rate(session["events"][0]), 0.05)
        self.assertAlmostEqual(efficiency_rate(session["events"][1]), 0.40)
        # Seed 0 fails E1's free attempt. kappa=0.10 skips E1 (rate 0.05)
        # and only E2 (c=10) may reload.
        always = play_session(session, "always", seed=0)
        efficient = play_session(session, "efficiency_greedy", seed=0, kappa=0.10)
        self.assertGreaterEqual(always["time_reloading"], 20)
        self.assertEqual(efficient["time_reloading"] % 10, 0)
        self.assertLess(efficient["reloads"], always["reloads"])

        reserved = copy.deepcopy(load_session(TOY))
        reserved["events"][0]["p"] = 0
        reserved["events"][1]["p"] = 0
        reserved["events"][0]["travel_seconds"] = 160
        # E1 is top-1. Retry needs 20 + 160 travel. Budget 180 allows one
        # retry; a second would leave only 140, which cannot reach E2.
        one = play_session(reserved, "reward_greedy", seed=0, reward_top_m=1)
        self.assertEqual(one["reloads"], 1)
        self.assertEqual(one["time_reloading"], 20)
        self.assertEqual(remaining_travel(reserved["events"], 0), 160)
        self.assertEqual([row["reached"] for row in one["reached"]], [True, True])

    def test_beta_is_week_six(self) -> None:
        with self.assertRaisesRegex(ValueError, r"^Beta is week 6$"):
            load_session(BETA)
        with tempfile.TemporaryDirectory() as temporary:
            completed = subprocess.run(
                [
                    sys.executable, "-B", "-m", "sim.run",
                    "--session", str(BETA),
                    "--strategies", "reward_greedy",
                    "--seeds", "1",
                    "--out", str(Path(temporary) / "out.csv"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Beta is week 6", completed.stderr)


if __name__ == "__main__":
    unittest.main()
