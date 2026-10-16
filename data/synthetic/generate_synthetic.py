"""Generate deterministic synthetic sessions for the COMP1110 project.

The generated JSON files are inputs, not Monte Carlo results.  Each experiment
changes one named factor while keeping the other event fields fixed.

Run from the repository root:

    python data/synthetic/generate_synthetic.py
"""

from __future__ import annotations

import copy
import csv
import json
import math
import random
from pathlib import Path
from typing import Any


OUTPUT_DIR = Path(__file__).resolve().parent
SCHEMA_VERSION = 1
# These names are a shared interface: do not rename them when adding examples.
DUMMY_COLUMNS = (
    "session_id", "experiment", "strategy", "seed", "reward", "reloads",
    "time_reloading",
)


def event(
    event_id: str,
    p: float,
    good_reward: float,
    bad_reward: float,
    retry_seconds: int,
    travel_seconds: int,
    *,
    entry_cost: float = 0.0,
    retained_failure_reward: float = 0.0,
) -> dict[str, Any]:
    """Return one known-odds event using the notation in the project plan."""
    return {
        "event_id": event_id,
        "odds_type": "known",
        "p": p,
        "good_reward": good_reward,
        "bad_reward": bad_reward,
        "retry_seconds": retry_seconds,
        "travel_seconds": travel_seconds,
        "entry_cost": entry_cost,
        "retained_failure_reward": retained_failure_reward,
    }


def session(
    session_id: str,
    description: str,
    budget_seconds: int,
    events: list[dict[str, Any]],
    *,
    experiment: str,
    varied_factor: str,
    varied_value: Any,
) -> dict[str, Any]:
    """Wrap event parameters in the session fields expected by the team loader."""
    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": session_id,
        "description": description,
        "experiment": experiment,
        "varied_factor": varied_factor,
        "varied_value": varied_value,
        "budget_seconds": budget_seconds,
        "events": events,
    }


# A common reference sequence lets each experiment change just one factor.
# Each call below is (id, probability, good reward, bad reward, retry s, travel s).
BASE_EVENTS = [
    event("E1", 0.65, 6, 0, 5, 30),
    event("E2", 0.25, 12, 0, 20, 45),
    event("E3", 0.10, 25, 0, 60, 60),
    event("E4", 0.40, 10, 0, 20, 35),
    event("E5", 0.05, 60, 0, 120, 90),
    event("E6", 0.75, 5, 0, 5, 25),
    event("E7", 0.20, 30, 0, 60, 50),
    event("E8", 0.50, 16, 0, 20, 0),
]


def toy_session() -> dict[str, Any]:
    """Keep the plan's two-event parameters; unspecified travel defaults to zero."""
    return session(
        "toy_2_event_T180",
        "Two-event plan example used to validate DP and simulator behaviour.",
        180,
        [
            event("E1", 0.10, 10, 0, 20, 0),
            event("E2", 0.50, 8, 0, 10, 0),
        ],
        experiment="toy",
        varied_factor="none",
        varied_value=None,
    )


def experiment_a() -> list[dict[str, Any]]:
    """Budget sweep: T = 10, 20, 30, 60, and 120 minutes."""
    return [
        session(
            f"A_budget_T{minutes:03d}min",
            "Experiment A: only the total time budget changes.",
            minutes * 60,
            copy.deepcopy(BASE_EVENTS),
            experiment="A",
            varied_factor="budget_seconds",
            varied_value=minutes * 60,
        )
        for minutes in (10, 20, 30, 60, 120)
    ]


def experiment_c() -> list[dict[str, Any]]:
    """Vary only E3's retry time; all other event parameters stay fixed."""
    sessions = []
    for retry_seconds in (5, 20, 60, 120):
        events = copy.deepcopy(BASE_EVENTS)
        # A deep copy prevents this sweep from altering A/B or the reference.
        events[2]["retry_seconds"] = retry_seconds
        sessions.append(
            session(
                f"C_retry_cost_c{retry_seconds:03d}s",
                "Experiment C: only E3's retry time changes.",
                30 * 60,
                events,
                experiment="C",
                varied_factor="E3.retry_seconds",
                varied_value=retry_seconds,
            )
        )
    return sessions


def future_opportunity_events(later_reward: float | None) -> list[dict[str, Any]]:
    """Return a small sequence with a fixed early event and optional later event."""
    events = [
        event("early_target", 0.10, 10, 0, 20, 35),
        event("bridge_1", 0.60, 5, 0, 10, 40),
        event("bridge_2", 0.35, 9, 0, 20, 45),
        event("bridge_3", 0.70, 4, 0, 5, 30),
    ]
    if later_reward is not None:
        events.append(event("later_opportunity", 0.50, later_reward, 0, 10, 35))
    events.append(event("final_event", 0.40, 12, 0, 20, 0))
    return events


def experiment_d() -> list[dict[str, Any]]:
    """Future-opportunity sweep to investigate an early accept/retry flip."""
    variants: tuple[tuple[str, float | None], ...] = (
        ("removed", None),
        ("reward_08", 8),
        ("reward_20", 20),
        ("reward_40", 40),
        ("reward_80", 80),
    )
    return [
        session(
            f"D_future_{label}",
            "Experiment D: the early target is fixed while a later opportunity is removed or revalued.",
            10 * 60,
            future_opportunity_events(reward),
            experiment="D",
            varied_factor="later_good_reward",
            varied_value=reward,
        )
        for label, reward in variants
    ]


def experiment_b() -> list[dict[str, Any]]:
    """Probability sweep for E3 with all other fields held fixed."""
    sessions = []
    for probability in (0.01, 0.02, 0.05, 0.10, 0.20, 0.40, 0.60, 0.90):
        events = copy.deepcopy(BASE_EVENTS)
        events[2]["p"] = probability
        probability_label = f"{probability:.2f}".replace(".", "p")
        sessions.append(
            session(
                f"B_probability_p{probability_label}",
                "Experiment B: only E3's success probability changes.",
                30 * 60,
                events,
                experiment="B",
                varied_factor="E3.p",
                varied_value=probability,
            )
        )
    return sessions


def uncertain_odds_session() -> dict[str, Any]:
    """Supply a mixed known/Beta fixture; the unknown event deliberately has no p."""
    events = copy.deepcopy(BASE_EVENTS)
    # Beta(1, 49) starts at mean 2%; 50 failures lower the mean to 1%.
    # Do not include a point-estimate p: loaders must branch on odds_type.
    uncertain_event = events[2]
    uncertain_event.pop("p")
    uncertain_event.update(odds_type="beta", alpha=1, beta=49)
    return session(
        "uncertain_beta_a1_b49_T030min",
        "Synthetic loader/learning example; not measured Path of Exile data.",
        30 * 60,
        events,
        experiment="uncertain_odds",
        varied_factor="E3.odds_type",
        varied_value="beta",
    )


def validate_session(item: dict[str, Any]) -> None:
    """Check the frozen interface and branch before looking for p."""
    required_session = {"session_id", "experiment", "budget_seconds", "events"}
    if not required_session.issubset(item):
        raise ValueError("missing required session field")
    events = item["events"]
    if item["budget_seconds"] <= 0:
        raise ValueError(f"{item['session_id']}: budget must be positive")
    if item["experiment"] != "toy" and not 5 <= len(events) <= 10:
        raise ValueError(f"{item['session_id']}: expected 5-10 events")
    if item["experiment"] == "toy" and len(events) != 2:
        raise ValueError("toy session must have exactly two events")
    identifiers = [entry["event_id"] for entry in events]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("event_id must be unique within a session")
    for event_item in events:
        required_event = {
            "good_reward", "bad_reward", "retry_seconds", "travel_seconds",
        }
        if not required_event.issubset(event_item):
            raise ValueError("missing required event field")
        # Unknown odds use positive prior parameters, never a fabricated p.
        odds_type = event_item.get("odds_type", "known")
        if odds_type == "known":
            if not 0 < event_item["p"] <= 1:
                raise ValueError(f"{item['session_id']}: probability out of range")
        elif odds_type == "beta":
            if "p" in event_item:
                raise ValueError("beta events must omit p")
            for key in ("alpha", "beta"):
                if not math.isfinite(event_item[key]) or event_item[key] <= 0:
                    raise ValueError("Beta prior parameters must be positive and finite")
        else:
            raise ValueError(f"unsupported odds_type: {odds_type}")
        if event_item["good_reward"] <= event_item["bad_reward"]:
            raise ValueError(f"{item['session_id']}: good reward must exceed bad reward")
        if event_item["retry_seconds"] <= 0 or event_item["travel_seconds"] < 0:
            raise ValueError(f"{item['session_id']}: invalid time field")


def write_json(path: Path, payload: Any) -> None:
    """Write stable formatting so regeneration produces reviewable Git diffs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Match the checked-in LF fixtures even when generating on Windows.
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_dummy_results(sessions: list[dict[str, Any]]) -> None:
    """Create 40 deliberately FAKE rows for developing plots, not evaluation."""
    # Five seeds per group allow confidence-interval code to be exercised.
    # These values are arbitrary fixture values; no policy or game is simulated.
    strategies = ("never_reload", "always_reload", "fixed_retry_3", "rho")
    rows = []
    for session_index, item in enumerate(sessions):
        for strategy_index, strategy in enumerate(strategies):
            for seed in range(5):
                # Separate local generators keep output reproducible and avoid
                # altering the global random state of a future simulator.
                rng = random.Random(1000 * session_index + 100 * strategy_index + seed)
                reloads = 0 if strategy == "never_reload" else rng.randint(1, 15)
                rows.append({
                    "session_id": item["session_id"],
                    "experiment": item["experiment"],
                    "strategy": strategy,
                    "seed": seed,
                    "reward": round(rng.uniform(10, 80), 2),
                    "reloads": reloads,
                    "time_reloading": reloads * 20,
                })
    with (OUTPUT_DIR / "dummy_sessions.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        # Explicit LF line endings avoid Git whitespace warnings on any OS.
        writer = csv.DictWriter(handle, fieldnames=DUMMY_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    # Keep provenance outside the CSV so its exact requested header is intact.
    write_json(OUTPUT_DIR / "dummy_sessions.metadata.json", {
        "file": "dummy_sessions.csv",
        "is_dummy": True,
        "purpose": "Plotting/mean/CI development ONLY; NOT simulator results.",
        "row_count": len(rows),
        "time_unit": "seconds",
        "warning": "Do not use these fabricated rows as project findings.",
    })


def main() -> None:
    """Regenerate every session, the discovery manifest, and plotting fixtures."""
    collections = {
        "toy": [toy_session()],
        "experiment_A_budget": experiment_a(),
        "experiment_C_retry_cost": experiment_c(),
        "experiment_D_future_opportunity": experiment_d(),
        "experiment_B_probability": experiment_b(),
        "uncertain_odds": [uncertain_odds_session()],
    }

    manifest_entries = []
    for directory_name, sessions in collections.items():
        for item in sessions:
            validate_session(item)
            relative_path = Path(directory_name) / f"{item['session_id']}.json"
            write_json(OUTPUT_DIR / relative_path, item)
            manifest_entries.append(
                {
                    "session_id": item["session_id"],
                    "experiment": item["experiment"],
                    "path": relative_path.as_posix(),
                    "event_count": len(item["events"]),
                    "budget_seconds": item["budget_seconds"],
                }
            )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generator": "data/synthetic/generate_synthetic.py",
        "session_count": len(manifest_entries),
        "sessions": manifest_entries,
    }
    write_json(OUTPUT_DIR / "manifest.json", manifest)
    # Use actual session IDs from A and C so plotting joins can be tested.
    write_dummy_results([collections["experiment_A_budget"][2],
                         collections["experiment_C_retry_cost"][1]])
    print(f"Generated {len(manifest_entries)} validated sessions in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
