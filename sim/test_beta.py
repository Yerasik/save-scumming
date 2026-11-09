"""Beta / uncertain-odds sessions. One latent p per event per seed.

Run from the repository root:

    python -B -m unittest discover -s sim -p 'test_*.py' -v
"""

from __future__ import annotations

import csv
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sim.session import (
    latent_success_probability,
    load_session,
    play_session,
)

ROOT = Path(__file__).resolve().parents[1]
BETA = ROOT / "data" / "synthetic" / "uncertain_odds" / "uncertain_beta_a1_b49_T030min.json"
H5 = ROOT / "experiments" / "sessions" / "H5" / "H5_beta_a1_b49.json"
TOY = ROOT / "data" / "synthetic" / "toy" / "toy_2_event_T180.json"


class BetaSessionTests(unittest.TestCase):
    def test_loader_accepts_beta_and_omits_p(self) -> None:
        session = load_session(BETA)
        raw = json.loads(BETA.read_text(encoding="utf-8"))
        self.assertEqual(session, raw)
        beta_event = next(
            event for event in session["events"] if event.get("odds_type") == "beta"
        )
        self.assertNotIn("p", beta_event)
        self.assertEqual(beta_event["alpha"], 1)
        self.assertEqual(beta_event["beta"], 49)

        with_p = copy.deepcopy(session)
        for event in with_p["events"]:
            if event.get("odds_type") == "beta":
                event["p"] = 0.02
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps(with_p), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, r"must omit p"):
                load_session(path)

    def test_latent_p_is_stable_across_strategies_and_retries(self) -> None:
        session = load_session(H5)
        event = session["events"][0]
        self.assertEqual(event["odds_type"], "beta")
        first = latent_success_probability(event, seed=7)
        second = latent_success_probability(event, seed=7)
        other_seed = latent_success_probability(event, seed=8)
        other_event = copy.deepcopy(event)
        other_event["event_id"] = "other"
        other_id = latent_success_probability(other_event, seed=7)
        self.assertEqual(first, second)
        self.assertGreaterEqual(first, 0.0)
        self.assertLessEqual(first, 1.0)
        self.assertNotEqual(first, other_seed)
        self.assertNotEqual(first, other_id)

        always = play_session(session, "always", seed=7)
        never = play_session(session, "never", seed=7)
        again = play_session(session, "always", seed=7)
        self.assertEqual(always, again)
        self.assertEqual(never["reloads"], 0)
        self.assertGreaterEqual(always["reloads"], never["reloads"])

    def test_always_reload_mean_attempts_match_one_over_prior_mean(self) -> None:
        """Mixture of geometrics: E[attempts] = (alpha + beta - 1) / (alpha - 1)
        is undefined for alpha=1. For Beta(2, 2), mean p is 0.5 so 1/E[p] is 2,
        but E[1/p] is larger. Check Beta(5, 5): E[p]=0.5, E[1/p]=(a+b-1)/(a-1)=2.25.
        """
        session = {
            "schema_version": 1,
            "session_id": "beta_geom",
            "experiment": "geom",
            "budget_seconds": 10**9,
            "events": [
                {
                    "event_id": "E1",
                    "odds_type": "beta",
                    "alpha": 5,
                    "beta": 5,
                    "good_reward": 1,
                    "bad_reward": 0,
                    "retry_seconds": 1,
                    "travel_seconds": 0,
                    "entry_cost": 0.0,
                    "retained_failure_reward": 0.0,
                }
            ],
        }
        n_seeds = 20_000
        attempts = []
        for seed in range(n_seeds):
            result = play_session(session, "always", seed)
            attempts.append(result["reloads"] + 1)
        mean_attempts = sum(attempts) / len(attempts)
        # E[1/p] for Beta(5,5) = (5+5-1)/(5-1) = 2.25
        expected = 2.25
        self.assertLessEqual(abs(mean_attempts - expected), 0.08)

    def test_cli_plays_beta_session(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "h5.csv"
            completed = subprocess.run(
                [
                    sys.executable, "-B", "-m", "sim.run",
                    "--session", str(H5),
                    "--strategies", "never,always,fixed_k_5",
                    "--seeds", "5",
                    "--out", str(output),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            with output.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 15)
        self.assertEqual(rows[0]["session_id"], "H5_beta_a1_b49")
        self.assertEqual({row["strategy"] for row in rows}, {"never", "always", "fixed_k_5"})

    def test_known_odds_toy_is_unchanged(self) -> None:
        session = load_session(TOY)
        first = play_session(session, "always", seed=0)
        second = play_session(session, "always", seed=0)
        self.assertEqual(first, second)
        self.assertNotIn("beta", {event.get("odds_type", "known") for event in session["events"]})


if __name__ == "__main__":
    unittest.main()
