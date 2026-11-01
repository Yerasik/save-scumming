"""Checks that every experiment config points at valid sessions and that the
redesigned D and H5 files still show the behaviour they were built for.

    python -B -m unittest discover -s experiments -p 'test_*.py' -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data" / "pokemon"))
sys.path.insert(0, str(HERE))

import make_sessions  # noqa: E402
from build_session import validate  # noqa: E402
from dp.solve import Solution  # noqa: E402

CONFIGS = sorted((HERE / "configs").glob("*.json"))


def retries_from_full_budget(session: dict, event_index: int = 0) -> int:
    """How many failures in a row DP retries the event when it starts at time T."""
    solution = Solution(session)
    cost = session["events"][event_index]["retry_seconds"]
    t, k = session["budget_seconds"], 0
    while t >= cost and solution.retry_map(event_index, k)[t]:
        t -= cost
        k += 1
    return k


def load(relative: str) -> dict:
    with (ROOT / relative).open(encoding="utf-8") as handle:
        return json.load(handle)


class ConfigTests(unittest.TestCase):
    def test_configs_exist(self) -> None:
        names = {path.stem.split("_")[0] for path in CONFIGS}
        self.assertTrue({"toy", "A", "B", "C", "D", "H5"} <= names, names)

    def test_every_session_exists_and_validates(self) -> None:
        for config_path in CONFIGS:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            for relative in config["sessions"]:
                with self.subTest(config=config_path.name, session=relative):
                    session = load(relative)
                    self.assertEqual(validate(session), [])
                    self.assertEqual(session["experiment"], config["experiment"])

    def test_one_factor_per_experiment(self) -> None:
        for config_path in CONFIGS:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            factors = {load(r)["varied_factor"] for r in config["sessions"]}
            with self.subTest(config=config_path.name):
                self.assertEqual(len(factors), 1, factors)

    def test_c_changes_one_event_only(self) -> None:
        config = json.loads((HERE / "configs" / "C_retry_cost.json").read_text(encoding="utf-8"))
        sessions = [load(r) for r in config["sessions"]]
        changed = set()
        for a, b in zip(sessions, sessions[1:]):
            for ea, eb in zip(a["events"], b["events"]):
                if ea != eb:
                    changed.add(ea["event_id"])
        self.assertEqual(len(changed), 1, changed)


class RedesignTests(unittest.TestCase):
    def test_generated_files_match_checked_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original = make_sessions.OUT
            make_sessions.OUT = Path(tmp)
            try:
                make_sessions.main()
            finally:
                make_sessions.OUT = original
            for path in Path(tmp).rglob("*.json"):
                checked_in = HERE / "sessions" / path.relative_to(tmp)
                self.assertEqual(path.read_bytes(), checked_in.read_bytes(), checked_in.name)

    def test_d_later_reward_stops_early_retries(self) -> None:
        """H3 setup: early retries fall as the later reward rises, reaching zero."""
        counts = [retries_from_full_budget(load(f"experiments/sessions/D/{name}.json"))
                  for name in ("D2_later_reward_010", "D2_later_reward_040", "D2_later_reward_080")]
        self.assertGreater(counts[0], counts[1])
        self.assertGreater(counts[1], 0)
        self.assertEqual(counts[2], 0)

    def test_h5_weaker_prior_retries_less(self) -> None:
        names = ("H5_known_p0p02", "H5_beta_a20_b980", "H5_beta_a1_b49", "H5_beta_a0p2_b9p8")
        counts = [retries_from_full_budget(load(f"experiments/sessions/H5/{n}.json")) for n in names]
        self.assertGreater(counts[-1], 0)
        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertGreater(counts[0], counts[-1])


if __name__ == "__main__":
    unittest.main()
