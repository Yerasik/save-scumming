"""Geometric wait plus toy CSV checks for the Monte Carlo runner.

Run from the repository root:
    python -B -m unittest discover -s sim -p 'test_*.py' -v

Tests live in the assigned sim folder and use the standard library only.
"""

from __future__ import annotations

import csv
import math
import subprocess
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

from sim import run
from sim.session import load_session, play_session

ROOT = Path(__file__).resolve().parents[1]
TOY = ROOT / "data" / "synthetic" / "toy" / "toy_2_event_T180.json"
DUMMY = ROOT / "data" / "synthetic" / "dummy_sessions.csv"
STRATEGIES = ("never", "always", "fixed_k_2", "fixed_k_3", "fixed_k_5")
TOY_SEED_COUNT = 400


def geometric_session(p: float = 0.25, budget_seconds: int = 10**9) -> dict:
    """One event, no travel, so always-reload is a pure geometric wait."""
    return {
        "schema_version": 1,
        "session_id": "geom_p025",
        "description": "Geometric waiting-time check for the simulator.",
        "experiment": "geom",
        "varied_factor": "none",
        "varied_value": None,
        "budget_seconds": budget_seconds,
        "events": [
            {
                "event_id": "E1",
                "odds_type": "known",
                "p": p,
                "good_reward": 1,
                "bad_reward": 0,
                "retry_seconds": 1,
                "travel_seconds": 0,
                "entry_cost": 0.0,
                "retained_failure_reward": 0.0,
            }
        ],
    }


def play_toy(n_seeds: int = TOY_SEED_COUNT) -> list[dict]:
    """Replay the toy session on a shared seed prefix for every strategy."""
    payload = load_session(TOY)
    return run.iter_rows(payload, list(STRATEGIES), n_seeds)


class GeometricWaitTests(unittest.TestCase):
    """The engine is wrong if retry-until-success does not match 1/p."""

    def test_always_reload_mean_attempts_match_one_over_p(self) -> None:
        """p=0.25 and a huge budget: mean (reloads+1) is within 1% of 4."""
        p = 0.25
        n_seeds = 50_000
        payload = geometric_session(p=p)
        attempts = []
        for seed in range(n_seeds):
            result = play_session(payload, "always", seed)
            self.assertGreaterEqual(result["reloads"], 0)
            self.assertGreaterEqual(result["time_reloading"], 0)
            attempts.append(result["reloads"] + 1)
        self.assertGreaterEqual(len(attempts), 20_000)
        mean_attempts = sum(attempts) / len(attempts)
        expected = 1.0 / p
        self.assertLessEqual(abs(mean_attempts - expected), 0.01 * expected)


class ToySessionTests(unittest.TestCase):
    """Prompt 1/2 toy checks, on a few hundred shared seeds rather than 10k."""

    def test_header_identity_counts_and_nonnegatives(self) -> None:
        """CSV contract, session identity, reused seeds, and no negative fields."""
        rows = play_toy()
        self.assertEqual(len(rows), len(STRATEGIES) * TOY_SEED_COUNT)
        self.assertEqual(list(rows[0].keys()), list(run.COLUMNS))
        by_strategy = defaultdict(list)
        for row in rows:
            self.assertEqual(row["session_id"], "toy_2_event_T180")
            self.assertEqual(row["experiment"], "toy")
            self.assertIn(row["strategy"], STRATEGIES)
            self.assertGreaterEqual(float(row["reward"]), 0)
            self.assertGreaterEqual(int(row["reloads"]), 0)
            self.assertGreaterEqual(float(row["time_reloading"]), 0)
            self.assertTrue(math.isfinite(float(row["reward"])))
            self.assertTrue(math.isfinite(float(row["time_reloading"])))
            self.assertLessEqual(float(row["time_reloading"]), 180)
            by_strategy[row["strategy"]].append(row)
        self.assertEqual(set(by_strategy), set(STRATEGIES))
        for strategy, group in by_strategy.items():
            seeds = [int(row["seed"]) for row in group]
            self.assertEqual(seeds, list(range(TOY_SEED_COUNT)), strategy)

    def test_never_and_fixed_k_caps_on_shared_seeds(self) -> None:
        """Never never reloads; fixed-k is at most (k-1) extra rolls per event."""
        payload = load_session(TOY)
        n_events = len(payload["events"])
        rows = play_toy()
        grouped = defaultdict(dict)
        for row in rows:
            grouped[int(row["seed"])][row["strategy"]] = row
        self.assertEqual(len(grouped), TOY_SEED_COUNT)
        for seed, by_name in grouped.items():
            self.assertEqual(set(by_name), set(STRATEGIES), seed)
            never = by_name["never"]
            self.assertEqual(int(never["reloads"]), 0)
            self.assertEqual(float(never["time_reloading"]), 0)
            for name, cap in (("fixed_k_2", 2), ("fixed_k_3", 3), ("fixed_k_5", 5)):
                self.assertLessEqual(int(by_name[name]["reloads"]), (cap - 1) * n_events)
            if float(never["reward"]) == 18:
                for name in STRATEGIES:
                    self.assertEqual(float(by_name[name]["reward"]), 18)
                    self.assertEqual(int(by_name[name]["reloads"]), 0)

    def test_cli_writes_requested_csv_not_dummy(self) -> None:
        """Exercise the CLI; two runs match; dummy plotting fixture stays put."""
        dummy_before = DUMMY.read_bytes()
        payload = load_session(TOY)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "toy_sessions.csv"
            command = [
                sys.executable, "-B", "-m", "sim.run",
                "--session", str(TOY),
                "--strategies", ",".join(STRATEGIES),
                "--seeds", str(TOY_SEED_COUNT),
                "--out", str(output),
            ]
            subprocess.run(command, check=True, cwd=ROOT, capture_output=True, text=True)
            first = output.read_bytes()
            subprocess.run(command, check=True, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(output.read_bytes(), first)
            with output.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, list(run.COLUMNS))
                rows = list(reader)
            self.assertEqual(len(rows), len(STRATEGIES) * TOY_SEED_COUNT)
            self.assertEqual(rows[0]["session_id"], payload["session_id"])
            self.assertEqual(rows[0]["experiment"], payload["experiment"])
        self.assertEqual(DUMMY.read_bytes(), dummy_before)

    def test_write_csv_refuses_dummy_sessions(self) -> None:
        """The plotting fixture is not an output path for the simulator."""
        with self.assertRaises(SystemExit):
            run.write_csv(DUMMY, [])


if __name__ == "__main__":
    unittest.main()
