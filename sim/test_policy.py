"""Read a written policy; do not solve a dynamic program.

Run from the repository root:

    python -B -m unittest discover -s sim -p 'test_*.py' -v
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sim.policy import load_policy, lookup_action
from sim.session import load_session, play_session

ROOT = Path(__file__).resolve().parents[1]
TOY = ROOT / "data" / "synthetic" / "toy" / "toy_2_event_T180.json"
POLICY = ROOT / "sim" / "fixtures" / "toy_policy.json"


class PolicyReaderTests(unittest.TestCase):
    def test_fixture_schema_and_first_matching_rule(self) -> None:
        raw = json.loads(POLICY.read_text(encoding="utf-8"))
        policy = load_policy(POLICY)
        self.assertEqual(policy, raw)
        self.assertEqual(policy["session_id"], "toy_2_event_T180")
        self.assertEqual(policy["default_action"], "accept")
        # Failures 0 and 1 retry E1; the third retry (failures == 2) does not.
        self.assertEqual(lookup_action(policy, "E1", 180, 0), "retry")
        self.assertEqual(lookup_action(policy, "E1", 180, 1), "retry")
        self.assertEqual(lookup_action(policy, "E1", 180, 2), "accept")
        self.assertEqual(lookup_action(policy, "E2", 180, 0), "accept")

    def test_dp_refuses_third_e1_retry_while_e2_is_ahead(self) -> None:
        session = copy.deepcopy(load_session(TOY))
        policy = load_policy(POLICY)
        session["events"][0]["p"] = 0
        session["events"][1]["p"] = 0
        result = play_session(session, "dp", seed=0, policy=policy)
        self.assertEqual(result["reloads"], 2)
        self.assertEqual(result["time_reloading"], 40)
        self.assertEqual(
            [row["reached"] for row in result["reached"]],
            [True, True],
        )

        tight = copy.deepcopy(session)
        tight["budget_seconds"] = 19
        tight_result = play_session(tight, "dp", seed=0, policy=policy)
        self.assertEqual(tight_result["reloads"], 0)
        self.assertEqual(tight_result["time_reloading"], 0.0)

    def test_cli_policy_writes_dp_strategy_name(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "dp.csv"
            subprocess.run(
                [
                    sys.executable, "-B", "-m", "sim.run",
                    "--session", str(TOY),
                    "--strategies", "dp",
                    "--policy", str(POLICY),
                    "--seeds", "3",
                    "--out", str(output),
                ],
                check=True,
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            lines = output.read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                lines[0],
                "session_id,experiment,strategy,seed,reward,reloads,time_reloading",
            )
            self.assertEqual(len(lines), 4)
            for line in lines[1:]:
                self.assertIn(",dp,", line)


if __name__ == "__main__":
    unittest.main()
