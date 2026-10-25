"""Regression checks for Vivaan's data and baseline contributions.

Run from the repository root:
    python -B -m unittest discover -s baselines -p 'test_*.py' -v

Tests live in the assigned baselines folder to avoid changing team-owned code.
"""

from __future__ import annotations

import contextlib
import csv
import io
import itertools
import json
import math
import subprocess
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

from baselines import rho_baseline
from data.synthetic import generate_synthetic as generator

# Resolve paths from this file, not from the caller's working directory.
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "synthetic"
SESSION_FIELDS = {"session_id", "experiment", "budget_seconds", "events"}
EVENT_FIELDS = {"good_reward", "bad_reward", "retry_seconds", "travel_seconds"}
RHO_COLUMNS = [
    "session_id", "event_id", "failures", "probability", "marginal_reward",
    "retry_seconds", "reward_per_second", "rho", "action",
]


def load_json(path: Path) -> dict:
    """Read a fixture without modifying it."""
    return json.loads(path.read_text(encoding="utf-8"))


class SyntheticInputTests(unittest.TestCase):
    """Protect the stable schema, single-variable sweeps, and fixture provenance."""

    @staticmethod
    def load_sessions(directory: str) -> list[dict]:
        """Use a stable filename order to make comparisons reproducible."""
        return [load_json(path) for path in sorted((DATA / directory).glob("*.json"))]

    def test_manifest_and_frozen_fields(self) -> None:
        """All 24 referenced sessions exist and satisfy the agreed loader contract."""
        manifest = load_json(DATA / "manifest.json")
        self.assertEqual(manifest["session_count"], 24)
        self.assertEqual(len(manifest["sessions"]), 24)
        identifiers = set()
        for entry in manifest["sessions"]:
            payload = load_json(DATA / entry["path"])
            generator.validate_session(payload)
            self.assertTrue(SESSION_FIELDS.issubset(payload))
            self.assertEqual(payload["session_id"], entry["session_id"])
            self.assertNotIn(payload["session_id"], identifiers)
            identifiers.add(payload["session_id"])
            self.assertEqual(len(payload["events"]), entry["event_count"])
            self.assertEqual(payload["events"][-1]["travel_seconds"], 0)
            for event in payload["events"]:
                self.assertTrue(EVENT_FIELDS.issubset(event))
                if event["odds_type"] == "known":
                    self.assertIn("p", event)

    def test_toy_parameters_match_plan(self) -> None:
        """Keep the team's original two-event sanity-check instance unchanged."""
        payload = load_json(DATA / "toy" / "toy_2_event_T180.json")
        self.assertEqual(payload["budget_seconds"], 180)
        self.assertEqual([event["p"] for event in payload["events"]], [0.1, 0.5])
        self.assertEqual([event["good_reward"] for event in payload["events"]], [10, 8])
        self.assertEqual([event["retry_seconds"] for event in payload["events"]], [20, 10])

    def test_a_changes_only_budget(self) -> None:
        """A holds all event parameters fixed while sweeping the time budget."""
        sessions = self.load_sessions("experiment_A_budget")
        self.assertEqual([item["budget_seconds"] for item in sessions],
                         [600, 1200, 1800, 3600, 7200])
        self.assertTrue(all(item["events"] == generator.BASE_EVENTS for item in sessions))

    def test_b_changes_only_e3_probability(self) -> None:
        """Compare every field against the reference, not just two variants."""
        sessions = self.load_sessions("experiment_B_probability")
        self.assertEqual(len(sessions), 8)
        for item in sessions:
            expected = json.loads(json.dumps(generator.BASE_EVENTS))
            expected[2]["p"] = item["varied_value"]
            self.assertEqual(item["events"], expected)
            self.assertEqual(item["budget_seconds"], 1800)

    def test_c_changes_only_e3_retry_time(self) -> None:
        """Catch the previous mistake of changing every event's retry time."""
        sessions = self.load_sessions("experiment_C_retry_cost")
        self.assertEqual([item["varied_value"] for item in sessions], [5, 20, 60, 120])
        for item in sessions:
            expected = json.loads(json.dumps(generator.BASE_EVENTS))
            expected[2]["retry_seconds"] = item["varied_value"]
            self.assertEqual(item["events"], expected)
            self.assertEqual(item["varied_factor"], "E3.retry_seconds")
            self.assertEqual(item["budget_seconds"], 1800)

    def test_d_keeps_other_events_fixed(self) -> None:
        """Only the later opportunity may be removed or revalued."""
        sessions = self.load_sessions("experiment_D_future_opportunity")
        reference = [event for event in sessions[0]["events"]
                     if event["event_id"] != "later_opportunity"]
        for item in sessions:
            other_events = [event for event in item["events"]
                            if event["event_id"] != "later_opportunity"]
            self.assertEqual(other_events, reference)
            self.assertEqual(item["budget_seconds"], 600)

    def test_beta_event_has_no_p(self) -> None:
        """A real missing-p fixture prevents loaders from silently assuming p exists."""
        payload = self.load_sessions("uncertain_odds")[0]
        event = payload["events"][2]
        self.assertEqual(event["odds_type"], "beta")
        self.assertNotIn("p", event)
        self.assertEqual((event["alpha"], event["beta"]), (1, 49))

    def test_dummy_header_groups_and_units(self) -> None:
        """Fake plotting data has five independent seed labels per plotting group."""
        with (DATA / "dummy_sessions.csv").open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            self.assertEqual(reader.fieldnames, list(generator.DUMMY_COLUMNS))
            rows = list(reader)
        self.assertEqual(len(rows), 40)
        groups = defaultdict(list)
        for row in rows:
            groups[(row["session_id"], row["experiment"], row["strategy"])].append(row)
            self.assertTrue(math.isfinite(float(row["reward"])))
            self.assertEqual(float(row["time_reloading"]), int(row["reloads"]) * 20)
            if row["strategy"] == "never_reload":
                self.assertEqual(int(row["reloads"]), 0)
        self.assertEqual(len(groups), 8)
        self.assertTrue(all({int(row["seed"]) for row in group} == set(range(5))
                            for group in groups.values()))
        # Nonconstant rewards ensure CI plotting sees a nonzero spread.
        self.assertTrue(all(len({float(row["reward"]) for row in group}) > 1
                            for group in groups.values()))
        sessions = {entry["session_id"]: entry
                    for entry in load_json(DATA / "manifest.json")["sessions"]}
        for row in rows:
            session = sessions[row["session_id"]]
            self.assertEqual(row["experiment"], session["experiment"])
            self.assertLessEqual(float(row["time_reloading"]), session["budget_seconds"])
        metadata = load_json(DATA / "dummy_sessions.metadata.json")
        self.assertIs(metadata["is_dummy"], True)
        self.assertEqual(metadata["row_count"], len(rows))

    def test_regeneration_matches_checked_in_outputs(self) -> None:
        """Regenerate in a temporary directory; never overwrite working fixtures."""
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary)
            with patch.object(generator, "OUTPUT_DIR", output_dir):
                with contextlib.redirect_stdout(io.StringIO()):
                    generator.main()
                first_run = {path.relative_to(output_dir): path.read_bytes()
                             for path in output_dir.rglob("*") if path.is_file()}
                with contextlib.redirect_stdout(io.StringIO()):
                    generator.main()
                for relative, expected in first_run.items():
                    self.assertEqual((output_dir / relative).read_bytes(), expected)
                    self.assertEqual((DATA / relative).read_bytes(), expected)


class RhoBaselineTests(unittest.TestCase):
    """Test threshold arithmetic, uncertain-odds loading, and CSV compatibility."""

    def test_toy_threshold_actions(self) -> None:
        """At rho=.10, E1's .05 rate loses to time cost and E2's .40 rate wins."""
        payload = load_json(DATA / "toy" / "toy_2_event_T180.json")
        events = [rho_baseline.event_from_mapping(item) for item in payload["events"]]
        rows = rho_baseline.evaluate(events, 0.10, 0, session_id=payload["session_id"])
        self.assertEqual([row["action"] for row in rows], ["accept", "retry"])
        self.assertAlmostEqual(rows[0]["reward_per_second"], 0.05)
        self.assertAlmostEqual(rows[1]["reward_per_second"], 0.40)
        self.assertTrue(all(row["session_id"] == payload["session_id"] for row in rows))

    def test_beta_loader_and_learning_flip(self) -> None:
        """Missing p loads successfully, and accumulating failures can change action."""
        path = DATA / "uncertain_odds" / "uncertain_beta_a1_b49_T030min.json"
        event = rho_baseline.load_events(path)[2]
        self.assertIsNone(event.p)
        self.assertAlmostEqual(event.probability(0), 0.02)
        self.assertAlmostEqual(event.probability(50), 0.01)
        self.assertTrue(event.should_retry(0.006, 0))
        self.assertFalse(event.should_retry(0.006, 50))

    def test_solver_rejects_uncertain_odds(self) -> None:
        """Do not disguise the known-odds solver as a Bayesian optimiser."""
        path = DATA / "uncertain_odds" / "uncertain_beta_a1_b49_T030min.json"
        with self.assertRaisesRegex(ValueError, "requires known odds"):
            rho_baseline.solve_self_consistent_rho(rho_baseline.load_events(path))

    def test_self_consistent_rho_against_exhaustive_search(self) -> None:
        """Independently enumerate all 256 policies to verify the rate optimum."""
        path = DATA / "experiment_A_budget" / "A_budget_T030min.json"
        events = rho_baseline.load_events(path)
        rho, rows = rho_baseline.solve_self_consistent_rho(events)
        rates = []
        for choices in itertools.product((False, True), repeat=len(events)):
            reward = seconds = 0.0
            for event, retry in zip(events, choices):
                # This independent calculation uses the geometric retry mean.
                p = event.p
                seconds += event.travel_seconds
                if retry:
                    reward += event.good_reward - event.entry_cost
                    seconds += (1 - p) * event.retry_seconds / p
                else:
                    reward += p * event.good_reward + (1 - p) * event.bad_reward - event.entry_cost
            rates.append(reward / seconds)
        self.assertAlmostEqual(rho, max(rates))
        for event, row in zip(events, rows):
            self.assertEqual(row["action"] == "retry_until_success",
                             event.reward_rate() >= rho)

    def test_csv_headers_and_identity(self) -> None:
        """session_id is additive: all original rho column names remain intact."""
        csv_names = ("toy_rho_0p10.csv", "base_session_rho_policy.csv",
                     "beta_rho_prior.csv", "beta_rho_50_failures.csv")
        manifest_ids = {item["session_id"] for item in load_json(DATA / "manifest.json")["sessions"]}
        for name in csv_names:
            with (ROOT / "baselines" / name).open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                expected = RHO_COLUMNS.copy()
                if name == "base_session_rho_policy.csv":
                    expected += ["expected_extra_reward_until_success",
                                 "expected_extra_seconds_until_success"]
                self.assertEqual(reader.fieldnames, expected)
                rows = list(reader)
                self.assertTrue(rows)
                self.assertTrue(all(row["session_id"] in manifest_ids for row in rows))

    def test_csv_export_requires_session_identity(self) -> None:
        """Fail early instead of creating rows that cannot be joined to sessions."""
        rows = [{"event_id": "E1"}]
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "session_id"):
                rho_baseline.write_csv(Path(temporary) / "bad.csv", rows)

    def test_cli_preserves_beta_session_id(self) -> None:
        """Exercise the actual CLI, not only in-process helper calls."""
        path = DATA / "uncertain_odds" / "uncertain_beta_a1_b49_T030min.json"
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "policy.csv"
            subprocess.run([
                sys.executable, "-B", str(ROOT / "baselines" / "rho_baseline.py"),
                str(path), "--rho", "0.006", "--failures", "50", "--csv", str(output),
            ], check=True, capture_output=True, text=True)
            self.assertEqual(output.read_bytes(),
                             (ROOT / "baselines" / "beta_rho_50_failures.csv").read_bytes())


if __name__ == "__main__":
    # Also allow direct execution once the repository root is on PYTHONPATH.
    unittest.main()
