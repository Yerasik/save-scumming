"""Write the redesigned Experiment D and H5 session files.

Daniel's DP check (dp/README.md, findings 2 and 3) showed that the synthetic
D and H5 files cannot test H3 or H5 as built:

- D: the later event had p = 0.5, c = 10 s, so it was almost always won in a
  few retries and its value never competed with the early event for time.
- H5: the Beta(1, 49) event cost 60 s per retry, so DP never retried it and a
  cap could not differ from retry-until-success.

The files here keep the frozen schema (PLAN.md section 3) and change one
named factor per experiment. Standard library only. From the repository root:

    python -B experiments/make_sessions.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "sessions"
SCHEMA_VERSION = 1


def event(event_id: str, g: float, c: int, f: int, **odds: Any) -> dict[str, Any]:
    """One event with save-scumming defaults: no entry cost, a reload discards b."""
    item: dict[str, Any] = {"event_id": event_id}
    item.update(odds)
    item.update(
        {
            "good_reward": g,
            "bad_reward": 0,
            "retry_seconds": c,
            "travel_seconds": f,
            "entry_cost": 0.0,
            "retained_failure_reward": 0.0,
        }
    )
    return item


def session(
    session_id: str,
    experiment: str,
    description: str,
    factor: str,
    value: Any,
    budget: int,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    events[-1]["travel_seconds"] = 0
    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": session_id,
        "description": description,
        "experiment": experiment,
        "varied_factor": factor,
        "varied_value": value,
        "budget_seconds": budget,
        "events": events,
    }


# Experiment D (H3). Early event fixed at the toy's E1 numbers. The later event
# is rare (p = 0.05) and slow (c = 30 s), so it needs real time to win. Only its
# good_reward changes. DP retries the early event 30 times from a full budget
# at g = 10 or 20, 18 times at g = 40, and never at g >= 80.
D_BUDGET = 600
D_LATER_REWARDS = (10, 20, 40, 80, 160)


def experiment_d() -> list[dict[str, Any]]:
    description = (
        "Experiment D v2: early event fixed; a rare, slow later event is "
        "removed or revalued (H3)."
    )
    early = dict(p=0.1, odds_type="known")
    items = [
        session(
            "D2_later_removed",
            "D",
            description,
            "later_good_reward",
            None,
            D_BUDGET,
            [event("early_target", 10, 20, 30, **early)],
        )
    ]
    for reward in D_LATER_REWARDS:
        items.append(
            session(
                f"D2_later_reward_{reward:03d}",
                "D",
                description,
                "later_good_reward",
                reward,
                D_BUDGET,
                [
                    event("early_target", 10, 20, 30, **early),
                    event("later_opportunity", reward, 30, 0, odds_type="known", p=0.05),
                ],
            )
        )
    return items


# H5. Same rare drop (prior mean 2%) with known odds or Beta priors of falling
# strength. Retry is 20 s (not 60 s) so DP actually retries. Only the prior on
# rare_drop changes. A later known event competes for the time.
H5_BUDGET = 1800
H5_PRIORS = (
    ("a20_b980", 20, 980),
    ("a1_b49", 1, 49),
    ("a0p2_b9p8", 0.2, 9.8),
)


def experiment_h5() -> list[dict[str, Any]]:
    description = (
        "H5: rare drop with prior mean 0.02, known or Beta of falling strength; "
        "a later known event competes for time."
    )

    def later() -> dict[str, Any]:
        return event("later_opportunity", 100, 30, 0, odds_type="known", p=0.05)

    items = [
        session(
            "H5_known_p0p02",
            "H5",
            description,
            "rare_drop_prior",
            "known p=0.02",
            H5_BUDGET,
            [event("rare_drop", 100, 20, 30, odds_type="known", p=0.02), later()],
        )
    ]
    for tag, alpha, beta in H5_PRIORS:
        items.append(
            session(
                f"H5_beta_{tag}",
                "H5",
                description,
                "rare_drop_prior",
                f"Beta({alpha}, {beta})",
                H5_BUDGET,
                [
                    event("rare_drop", 100, 20, 30, odds_type="beta", alpha=alpha, beta=beta),
                    later(),
                ],
            )
        )
    return items


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2) + "\n")


def main() -> int:
    for folder, items in (("D", experiment_d()), ("H5", experiment_h5())):
        for item in items:
            path = OUT / folder / f"{item['session_id']}.json"
            write_json(path, item)
            print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
