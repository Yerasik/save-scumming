"""Load a session JSON file and play one reload strategy.

Standard library only. This module does not solve a dynamic program and does
not read a policy file. Field names are the ones already stored in the JSON.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from sim.policy import lookup_action

# Keys are required as written. They are not renamed to g, b, c, f, e, or h.
_SESSION_KEYS = ("budget_seconds", "events")
_EVENT_KEYS = (
    "event_id",
    "p",
    "good_reward",
    "bad_reward",
    "retry_seconds",
    "travel_seconds",
    "entry_cost",
    "retained_failure_reward",
)

# None means no attempt cap. Limits count the free first attempt.
_ATTEMPT_LIMITS: dict[str, int | None] = {
    "never": 1,
    "always": None,
    "fixed_k_2": 2,
    "fixed_k_3": 3,
    "fixed_k_5": 5,
}
_GREEDY_STRATEGIES = frozenset({"reward_greedy", "efficiency_greedy"})
DEFAULT_REWARD_TOP_M = 1
DEFAULT_KAPPA = 0.10


def load_session(path: str | Path) -> dict[str, Any]:
    """Read one session file and leave its field names unchanged."""
    with Path(path).open(encoding="utf-8") as handle:
        session = json.load(handle)
    missing = [key for key in _SESSION_KEYS if key not in session]
    if missing:
        raise KeyError(f"session is missing {missing}")
    events = session["events"]
    if not isinstance(events, list):
        raise TypeError("events must be a list")
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise TypeError(f"events[{index}] must be an object")
        odds_type = event.get("odds_type", "known")
        if odds_type == "beta":
            raise ValueError("Beta is week 6")
        if odds_type != "known":
            raise ValueError(
                f"events[{index}] has odds_type {odds_type!r}; "
                "play_session supports known odds"
            )
        missing_event = [key for key in _EVENT_KEYS if key not in event]
        if missing_event:
            event_id = event.get("event_id", index)
            raise KeyError(f"event {event_id} is missing {missing_event}")
    return session


def _success(event: dict[str, Any], failures: int, rng: random.Random) -> bool:
    """Draw one attempt. Known odds stay at ``p`` as failures increase."""
    if failures < 0:
        raise ValueError("failures must be non-negative")
    return rng.random() < event["p"]


def remaining_travel(events: list[dict[str, Any]], index: int) -> float:
    """Travel still required after this event to reach the last event."""
    return float(sum(event["travel_seconds"] for event in events[index:-1]))


def top_m_event_ids(events: list[dict[str, Any]], m: int) -> set[str]:
    """Event ids with the largest ``good_reward - bad_reward``, file order on ties."""
    if m < 1:
        raise ValueError("reward-top-m must be at least 1")
    ranked = sorted(
        range(len(events)),
        key=lambda index: (
            -(events[index]["good_reward"] - events[index]["bad_reward"]),
            index,
        ),
    )
    return {events[index]["event_id"] for index in ranked[:m]}


def efficiency_rate(event: dict[str, Any]) -> float:
    """Known-odds reward per retry second: p * (g - b) / c."""
    retry_seconds = event["retry_seconds"]
    if retry_seconds <= 0:
        raise ValueError("retry_seconds must be positive")
    return event["p"] * (event["good_reward"] - event["bad_reward"]) / retry_seconds


def _can_retry(attempts: int, limit: int | None, clock: float, retry_seconds: float) -> bool:
    """Return whether another paid attempt is allowed.

    ``fixed_k_N`` stops at N attempts including the first. ``always`` has no
    attempt cap. Every strategy retries only while ``clock >= retry_seconds``.
    """
    if limit is not None and attempts >= limit:
        return False
    if retry_seconds <= 0:
        raise ValueError("retry_seconds must be positive")
    return clock >= retry_seconds


def _has_route_reserve(clock: float, retry_seconds: float, travel_left: float) -> bool:
    """Retry only if the paid attempt still leaves travel to the last event."""
    if retry_seconds <= 0:
        raise ValueError("retry_seconds must be positive")
    return clock >= retry_seconds + travel_left


def _should_retry(
    *,
    strategy: str,
    event: dict[str, Any],
    clock: float,
    attempts: int,
    failures: int,
    limit: int | None,
    policy: dict[str, Any] | None,
    travel_left: float,
    greedy_ids: set[str] | None,
    kappa: float,
) -> bool:
    """Decide whether to pay for another attempt after a failure."""
    retry_seconds = event["retry_seconds"]
    if strategy == "dp":
        if policy is None:
            raise ValueError("strategy 'dp' requires a policy")
        action = lookup_action(policy, event["event_id"], clock, failures)
        if action != "retry":
            return False
        # A retry that the clock cannot pay is treated as accept.
        if retry_seconds <= 0:
            raise ValueError("retry_seconds must be positive")
        return clock >= retry_seconds
    if strategy == "reward_greedy":
        if greedy_ids is None or event["event_id"] not in greedy_ids:
            return False
        return _has_route_reserve(clock, retry_seconds, travel_left)
    if strategy == "efficiency_greedy":
        if efficiency_rate(event) < kappa:
            return False
        return _has_route_reserve(clock, retry_seconds, travel_left)
    return _can_retry(attempts, limit, clock, retry_seconds)


def _play_event(
    event: dict[str, Any],
    rng: random.Random,
    clock: float,
    limit: int | None,
    *,
    strategy: str,
    policy: dict[str, Any] | None,
    travel_left: float,
    greedy_ids: set[str] | None,
    kappa: float,
) -> tuple[float, int, float, float]:
    """Play one reached event. Return reward, reloads, reload time, and clock."""
    reward = -float(event["entry_cost"])
    reloads = 0
    time_reloading = 0.0
    failures = 0
    attempts = 0
    while True:
        attempts += 1
        if _success(event, failures, rng):
            reward += event["good_reward"]
            break
        if _should_retry(
            strategy=strategy,
            event=event,
            clock=clock,
            attempts=attempts,
            failures=failures,
            limit=limit,
            policy=policy,
            travel_left=travel_left,
            greedy_ids=greedy_ids,
            kappa=kappa,
        ):
            reward += event["retained_failure_reward"]
            clock -= event["retry_seconds"]
            time_reloading += event["retry_seconds"]
            reloads += 1
            failures += 1
            continue
        reward += event["bad_reward"]
        break
    return reward, reloads, time_reloading, clock


def play_session(
    session: dict[str, Any],
    strategy: str,
    seed: int,
    policy: dict[str, Any] | None = None,
    reward_top_m: int = DEFAULT_REWARD_TOP_M,
    kappa: float = DEFAULT_KAPPA,
) -> dict[str, Any]:
    """Play one session.

    ``budget_seconds`` is the clock. The first attempt at each reached event
    is free. A success adds ``good_reward``. An accepted failure adds
    ``bad_reward``. A retry adds ``retained_failure_reward``, subtracts
    ``retry_seconds``, increments the failure count, and rolls again.
    ``reloads`` counts retries only.

    ``never`` accepts the first roll. ``fixed_k_2``, ``fixed_k_3``, and
    ``fixed_k_5`` allow that many attempts, including the first, and also
    stop when the clock cannot pay ``retry_seconds``. ``always`` retries
    while ``time_left >= retry_seconds``. ``dp`` reads a supplied policy
    after each failure; it does not solve a dynamic program. The first
    matching rule wins. No match uses ``default_action``. A ``retry``
    action is accepted instead when ``time_left < retry_seconds``.
    ``reward_greedy`` retries the top ``reward_top_m`` events by
    ``good_reward - bad_reward`` until success, while
    ``time_left >= retry_seconds`` plus remaining travel to the last event.
    ``efficiency_greedy`` retries while
    ``p * (good_reward - bad_reward) / retry_seconds >= kappa`` and the
    same travel reserve holds. Both greedy rules are known-odds only.

    ``entry_cost`` is paid on entry. ``travel_seconds`` is paid when moving
    on. If the clock cannot cover that travel, every later event is unreached.

    Returns ``reward``, ``reloads``, ``time_reloading``, and ``reached``
    (one ``{event_id, reached}`` row per event, in file order).
    """
    events = session["events"]
    for event in events:
        if event.get("odds_type", "known") == "beta":
            raise ValueError("Beta is week 6")

    if strategy == "dp":
        if policy is None:
            raise ValueError("strategy 'dp' requires a policy")
        if policy.get("session_id") != session.get("session_id"):
            raise ValueError("policy session_id does not match the session")
        limit = None
        greedy_ids: set[str] | None = None
    elif strategy in _GREEDY_STRATEGIES:
        limit = None
        greedy_ids = top_m_event_ids(events, reward_top_m)
    elif strategy in _ATTEMPT_LIMITS:
        limit = _ATTEMPT_LIMITS[strategy]
        greedy_ids = None
    else:
        raise ValueError(f"unsupported strategy: {strategy!r}")

    rng = random.Random(seed)
    clock = session["budget_seconds"]
    reward = 0.0
    reloads = 0
    time_reloading = 0.0
    reached: list[dict[str, Any]] = []

    for index, event in enumerate(events):
        event_reward, event_reloads, event_time, clock = _play_event(
            event,
            rng,
            clock,
            limit,
            strategy=strategy,
            policy=policy,
            travel_left=remaining_travel(events, index),
            greedy_ids=greedy_ids,
            kappa=kappa,
        )
        reward += event_reward
        reloads += event_reloads
        time_reloading += event_time
        reached.append({"event_id": event["event_id"], "reached": True})

        if index + 1 == len(events):
            break
        travel_seconds = event["travel_seconds"]
        if clock < travel_seconds:
            for later in events[index + 1 :]:
                reached.append({"event_id": later["event_id"], "reached": False})
            break
        clock -= travel_seconds

    return {
        "reward": reward,
        "reloads": reloads,
        "time_reloading": time_reloading,
        "reached": reached,
    }
