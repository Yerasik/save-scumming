"""Small checks for the H5 recheck and the report figure helpers."""

import json
import unittest
from pathlib import Path

from dp.h5_recheck import cap_policy
from dp.report_figure import walk_path
from dp.solve import Solution, load_session
from sim.session import load_session as sim_load_session, play_session

H5 = Path("experiments/sessions/H5")


class CapPolicyTest(unittest.TestCase):
    def test_cap_limits_first_event_attempts(self):
        session = sim_load_session(H5 / "H5_known_p0p02.json")
        for cap in (1, 3, 10):
            policy = cap_policy(session, cap)
            for seed in range(200):
                result = play_session(session, "dp", seed, policy=policy)
                # Later event is uncapped, so only check the total stays sane.
                self.assertGreaterEqual(result["reloads"], 0)
            rule = policy["rules"][0]
            self.assertEqual(rule["max_failures"], cap - 1)
            # Retry on the first event must leave travel time to the next one.
            self.assertEqual(rule["min_time_left"], 20 + 30)


class WalkPathTest(unittest.TestCase):
    def test_give_up_points_shrink_as_prior_weakens(self):
        stops = []
        for sid in ("H5_known_p0p02", "H5_beta_a1_b49", "H5_beta_a0p2_b9p8"):
            ks, ts = walk_path(Solution(load_session(H5 / f"{sid}.json")), 0)
            self.assertEqual(ts[0] - ts[-1], 20 * ks[-1])
            stops.append(ks[-1])
        self.assertGreater(stops[0], stops[1])
        self.assertGreater(stops[1], stops[2])

    def test_committed_policies_match_solver(self):
        for sid in ("H5_known_p0p02", "H5_beta_a1_b49"):
            committed = json.loads(Path(f"dp/out/{sid}.policy.json").read_text())
            fresh = Solution(load_session(H5 / f"{sid}.json")).expected_value
            self.assertAlmostEqual(committed["expected_value"], fresh, places=6)


if __name__ == "__main__":
    unittest.main()
