"""Checks for the Pokémon session builder. Standard library only.

    python -B -m unittest discover -s data/pokemon -p 'test_*.py' -v
"""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_session as bs  # noqa: E402

HERE = Path(__file__).resolve().parent
TIMING_FIELDS = ["event_id", "video_url", "channel", "video_date",
                 "retry_start", "retry_end", "travel_start", "travel_end", "notes"]


def write_timings(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TIMING_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


class TimestampTests(unittest.TestCase):
    def test_to_seconds(self) -> None:
        self.assertEqual(bs.to_seconds("4:05"), 245)
        self.assertEqual(bs.to_seconds("1:02:03"), 3723)
        self.assertEqual(bs.to_seconds("0:59"), 59)


class BuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.events = bs.read_csv(HERE / "events.csv")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def full_timings(self) -> list[dict[str, str]]:
        """Three fake videos per event: retry 200/210/221 s, travel 100/110/120 s."""
        rows = []
        ids = [row["event_id"] for row in sorted(self.events, key=lambda r: int(r["order"]))]
        for index, event_id in enumerate(ids):
            last = index == len(ids) - 1
            for n, (retry_end, travel_end) in enumerate((("3:20", "1:40"), ("3:30", "1:50"), ("3:41", "2:00"))):
                rows.append({
                    "event_id": event_id, "video_url": f"https://example.com/{event_id}/{n}",
                    "retry_start": "0:00", "retry_end": retry_end,
                    "travel_start": "" if last else "0:00", "travel_end": "" if last else travel_end,
                })
        return rows

    def test_event_list_is_valid(self) -> None:
        self.assertGreaterEqual(len(self.events), 4)
        for row in self.events:
            self.assertTrue(0 < float(row["p"]) <= 1, row["event_id"])

    def test_strict_build_refuses_missing_timings(self) -> None:
        with self.assertRaises(SystemExit):
            bs.build(self.events, {}, 3600, draft=False)

    def test_draft_build_validates(self) -> None:
        session = bs.build(self.events, {}, 3600, draft=True)
        self.assertEqual(session["session_id"], "pokemon_sv_draft")
        self.assertIn("PLACEHOLDER", session["description"])
        self.assertEqual(bs.validate(session), [])

    def test_means_are_rounded_whole_seconds(self) -> None:
        path = self.dir / "timings.csv"
        write_timings(path, self.full_timings())
        timings = bs.average_timings(bs.read_csv(path))
        session = bs.build(self.events, timings, 3600, draft=False)
        self.assertEqual(bs.validate(session), [])
        self.assertEqual(session["session_id"], "pokemon_sv_main")
        first, last = session["events"][0], session["events"][-1]
        self.assertEqual(first["retry_seconds"], 210)  # mean(200, 210, 221) = 210.33
        self.assertEqual(first["travel_seconds"], 110)
        self.assertEqual(last["travel_seconds"], 0)

    def test_two_videos_is_not_enough(self) -> None:
        rows = [row for row in self.full_timings() if not row["video_url"].endswith("/2")]
        path = self.dir / "timings.csv"
        write_timings(path, rows)
        with self.assertRaises(SystemExit):
            bs.build(self.events, bs.average_timings(bs.read_csv(path)), 3600, draft=False)

    def test_two_travel_videos_is_enough(self) -> None:
        rows = [row for row in self.full_timings()
                if not (row["video_url"].endswith("/2") and row["travel_start"])]
        rows += [dict(row, travel_start="", travel_end="") for row in self.full_timings()
                 if row["video_url"].endswith("/2") and row["travel_start"]]
        path = self.dir / "timings.csv"
        write_timings(path, rows)
        session = bs.build(self.events, bs.average_timings(bs.read_csv(path)), 3600, draft=False)
        self.assertEqual(bs.validate(session), [])
        self.assertEqual(session["events"][0]["retry_seconds"], 210)
        self.assertEqual(session["events"][0]["travel_seconds"], 105)  # mean(100, 110)

    def test_one_travel_video_is_not_enough(self) -> None:
        rows = [dict(row, travel_start="", travel_end="") if not row["video_url"].endswith("/0") else row
                for row in self.full_timings()]
        path = self.dir / "timings.csv"
        write_timings(path, rows)
        with self.assertRaises(SystemExit):
            bs.build(self.events, bs.average_timings(bs.read_csv(path)), 3600, draft=False)

    def test_reversed_timestamps_rejected(self) -> None:
        rows = self.full_timings()
        rows[0]["retry_start"], rows[0]["retry_end"] = "5:00", "1:00"
        path = self.dir / "timings.csv"
        write_timings(path, rows)
        with self.assertRaises(ValueError):
            bs.average_timings(bs.read_csv(path))

    def test_validate_catches_schema_breaks(self) -> None:
        session = bs.build(self.events, {}, 3600, draft=True)
        broken = json.loads(json.dumps(session))
        broken["events"][-1]["travel_seconds"] = 5
        del broken["events"][0]["p"]
        errors = bs.validate(broken)
        self.assertTrue(any("last event" in e for e in errors))
        self.assertTrue(any("p must be" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
