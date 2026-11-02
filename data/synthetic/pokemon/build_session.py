"""Turn the Pokémon event list and video timings into a session JSON.

Inputs (this folder):

- ``events.csv``  one row per event, in play order: odds ``p`` and rewards.
- ``timings.csv`` one row per public video and event. Timestamps are ``m:ss``
  or ``h:mm:ss`` as shown on the video player.
    - ``retry_start`` -> ``retry_end``: one full reset cycle (close the game,
      reload, redo the encounter, see the result).
    - ``travel_start`` -> ``travel_end``: moving on from this event to the
      next one. Leave blank for the last event.

``retry_seconds`` and ``travel_seconds`` are the mean over videos, rounded to
whole seconds (the DP needs whole seconds). Every event needs at least
``MIN_VIDEOS`` retry timings, and every event but the last at least
``MIN_TRAVEL_VIDEOS`` travel timings (team decision, 2 Nov). ``--draft`` fills missing timings with placeholder
guesses so the pipeline can run before the videos are timed; the output is
then named ``pokemon_sv_draft`` and must not be reported as data.

From the repository root:

    python -B data/pokemon/build_session.py            # real file, needs timings
    python -B data/pokemon/build_session.py --draft    # placeholder timings
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any

HERE = Path(__file__).resolve().parent
MIN_VIDEOS = 3
MIN_TRAVEL_VIDEOS = 2
SCHEMA_VERSION = 1

# Placeholder guesses for --draft only. Not measured.
DRAFT_RETRY_SECONDS = {"default": 240}
DRAFT_TRAVEL_SECONDS = 180

SESSION_KEYS = (
    "schema_version", "session_id", "description", "experiment",
    "varied_factor", "varied_value", "budget_seconds", "events",
)
EVENT_KEYS = (
    "event_id", "odds_type", "good_reward", "bad_reward", "retry_seconds",
    "travel_seconds", "entry_cost", "retained_failure_reward",
)


def to_seconds(stamp: str) -> int:
    """``"1:02:03"`` -> 3723, ``"4:05"`` -> 245."""
    total = 0
    for part in stamp.strip().split(":"):
        total = total * 60 + int(part)
    return total


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.DictReader(handle) if any(v.strip() for v in row.values() if v)]


def average_timings(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    """Per event: video count, mean retry and mean travel in seconds."""
    retry: dict[str, list[int]] = {}
    travel: dict[str, list[int]] = {}
    for row in rows:
        event_id = row["event_id"].strip()
        if row.get("retry_start", "").strip() and row.get("retry_end", "").strip():
            span = to_seconds(row["retry_end"]) - to_seconds(row["retry_start"])
            if span <= 0:
                raise ValueError(f"{event_id} {row['video_url']}: retry_end is not after retry_start")
            retry.setdefault(event_id, []).append(span)
        if row.get("travel_start", "").strip() and row.get("travel_end", "").strip():
            span = to_seconds(row["travel_end"]) - to_seconds(row["travel_start"])
            if span < 0:
                raise ValueError(f"{event_id} {row['video_url']}: travel_end is before travel_start")
            travel.setdefault(event_id, []).append(span)
    summary = {}
    for event_id in set(retry) | set(travel):
        summary[event_id] = {
            "retry_videos": len(retry.get(event_id, [])),
            "travel_videos": len(travel.get(event_id, [])),
            "retry_seconds": round(mean(retry[event_id])) if event_id in retry else None,
            "travel_seconds": round(mean(travel[event_id])) if event_id in travel else None,
        }
    return summary


def build(events: list[dict[str, str]], timings: dict[str, dict[str, Any]], budget: int, draft: bool) -> dict[str, Any]:
    ordered = sorted(events, key=lambda row: int(row["order"]))
    problems = []
    built = []
    for index, row in enumerate(ordered):
        event_id = row["event_id"].strip()
        last = index == len(ordered) - 1
        timing = timings.get(event_id, {})

        retry = timing.get("retry_seconds")
        if timing.get("retry_videos", 0) < MIN_VIDEOS:
            if not draft:
                problems.append(f"{event_id}: {timing.get('retry_videos', 0)} retry timings, need {MIN_VIDEOS}")
            retry = DRAFT_RETRY_SECONDS.get(event_id, DRAFT_RETRY_SECONDS["default"])

        travel = 0
        if not last:
            travel = timing.get("travel_seconds")
            if timing.get("travel_videos", 0) < MIN_TRAVEL_VIDEOS:
                if not draft:
                    problems.append(f"{event_id}: {timing.get('travel_videos', 0)} travel timings, need {MIN_TRAVEL_VIDEOS}")
                travel = DRAFT_TRAVEL_SECONDS

        built.append(
            {
                "event_id": event_id,
                "odds_type": "known",
                "p": float(row["p"]),
                "good_reward": float(row["good_reward"]),
                "bad_reward": float(row["bad_reward"]),
                "retry_seconds": retry,
                "travel_seconds": travel,
                "entry_cost": 0.0,
                "retained_failure_reward": 0.0,
            }
        )
    if problems:
        raise SystemExit("not enough video timings (use --draft for placeholders):\n  " + "\n  ".join(problems))

    if draft:
        session_id = "pokemon_sv_draft"
        description = "DRAFT Pokemon Scarlet/Violet route with PLACEHOLDER timings. Not data; do not report."
    else:
        session_id = "pokemon_sv_main"
        description = (
            "Pokemon Scarlet/Violet postgame route: the four Treasures of Ruin, target natures. "
            f"Retry times are means over >= {MIN_VIDEOS} public videos per event, travel over >= "
            f"{MIN_TRAVEL_VIDEOS} (data/pokemon/timings.csv)."
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": session_id,
        "description": description,
        "experiment": "pokemon",
        "varied_factor": "none",
        "varied_value": None,
        "budget_seconds": budget,
        "events": built,
    }


def validate(session: dict[str, Any]) -> list[str]:
    """Check a session against the frozen schema (PLAN.md section 3)."""
    errors = [f"missing session key {key!r}" for key in SESSION_KEYS if key not in session]
    if errors:
        return errors
    budget = session["budget_seconds"]
    if not isinstance(budget, int) or budget <= 0:
        errors.append("budget_seconds must be a positive whole number")
    events = session["events"]
    if not events:
        errors.append("events is empty")
    for index, event in enumerate(events):
        name = event.get("event_id", index)
        errors += [f"{name}: missing {key!r}" for key in EVENT_KEYS if key not in event]
        odds = event.get("odds_type")
        if odds == "known":
            p = event.get("p")
            if not isinstance(p, (int, float)) or not 0 < p <= 1:
                errors.append(f"{name}: p must be in (0, 1]")
        elif odds == "beta":
            for key in ("alpha", "beta"):
                if not isinstance(event.get(key), (int, float)) or event[key] <= 0:
                    errors.append(f"{name}: {key} must be positive")
        else:
            errors.append(f"{name}: odds_type must be 'known' or 'beta'")
        for key in ("retry_seconds", "travel_seconds"):
            value = event.get(key)
            if not isinstance(value, int) or value < 0:
                errors.append(f"{name}: {key} must be a non-negative whole number")
        if event.get("retry_seconds") == 0:
            errors.append(f"{name}: retry_seconds must be positive")
    if events and events[-1].get("travel_seconds") != 0:
        errors.append("last event must have travel_seconds = 0")
    return errors


def write_summary(path: Path, events: list[dict[str, str]], timings: dict[str, dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["event_id", "retry_videos", "mean_retry_seconds", "travel_videos", "mean_travel_seconds"])
        for row in sorted(events, key=lambda r: int(r["order"])):
            t = timings.get(row["event_id"], {})
            writer.writerow([row["event_id"], t.get("retry_videos", 0), t.get("retry_seconds", ""),
                             t.get("travel_videos", 0), t.get("travel_seconds", "")])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Pokemon session JSON.")
    parser.add_argument("--draft", action="store_true", help="fill missing timings with placeholders")
    parser.add_argument("--budget-minutes", type=int, default=60)
    parser.add_argument("--events", type=Path, default=HERE / "events.csv")
    parser.add_argument("--timings", type=Path, default=HERE / "timings.csv")
    parser.add_argument("--out-dir", type=Path, default=HERE)
    args = parser.parse_args(argv)

    events = read_csv(args.events)
    timings = average_timings(read_csv(args.timings))
    session = build(events, timings, args.budget_minutes * 60, args.draft)
    errors = validate(session)
    if errors:
        print("schema errors:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / f"{session['session_id']}.json"
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(session, indent=2, ensure_ascii=False) + "\n")
    write_summary(args.out_dir / "timings_summary.csv", events, timings)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
