"""Recheck H5 after the Beta simulator landed.

Two checks, from the repository root:

    python -B -m dp.h5_recheck --seeds 10000

1. The DP policy's ``expected_value`` should match the simulator's mean reward
   for strategy ``dp`` (the sim draws one latent ``p`` per seed from the Beta
   prior, which is the same model the DP's posterior mean assumes).
2. A fair cap test. The sim's ``fixed_k_N`` caps *every* event at N attempts,
   so with p = 0.02 it barely uses the budget and loses by default. Here the cap
   is on ``rare_drop`` only; ``later_opportunity`` still retries until success.
   We sweep the cap N and compare the best cap with ``always`` and ``dp``.

Writes ``dp/out/h5_recheck.csv`` (one row per session x strategy).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import tempfile
from pathlib import Path

from sim.policy import load_policy
from sim.session import load_session, play_session

SESSIONS = [
    "H5_known_p0p02",
    "H5_beta_a20_b980",
    "H5_beta_a1_b49",
    "H5_beta_a0p2_b9p8",
]
SESSION_DIR = Path("experiments/sessions/H5")
POLICY_DIR = Path("dp/out")
CAPS = [1, 2, 3, 5, 10, 15, 20, 25, 30, 40, 50, 60, 75, 90]
UNCAPPED = 1_000_000


def cap_policy(session: dict, cap: int) -> dict:
    """At most ``cap`` attempts on the first event; later events retry until success.

    Every retry on the first event keeps enough time to travel on, so the cap
    is the only thing that differs from retry-until-success.
    """
    first, *rest = session["events"]
    # travel_seconds is the walk *after* an event, so the route left is every
    # event's travel except the last one's.
    travel_after = sum(float(e["travel_seconds"]) for e in session["events"][:-1])
    rules = [{
        "event_id": first["event_id"],
        "min_time_left": float(first["retry_seconds"]) + travel_after,
        "max_failures": cap - 1,
        "action": "retry",
    }]
    for event in rest:
        rules.append({
            "event_id": event["event_id"],
            "min_time_left": float(event["retry_seconds"]),
            "max_failures": UNCAPPED,
            "action": "retry",
        })
    return {
        "schema_version": 1,
        "session_id": session["session_id"],
        "default_action": "accept",
        "rules": rules,
    }


def mean_se(values: list[float]) -> tuple[float, float]:
    n = len(values)
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return mean, math.sqrt(var / n)


def run(session: dict, strategy: str, policy: dict | None, seeds: int) -> list[float]:
    rewards = []
    for seed in range(seeds):
        result = play_session(session, strategy, seed, policy=policy)
        rewards.append(float(result["reward"]))
    return rewards


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seeds", type=int, default=10000)
    parser.add_argument("--out", default="dp/out/h5_recheck.csv")
    args = parser.parse_args(argv)

    rows = []
    for sid in SESSIONS:
        session = load_session(SESSION_DIR / f"{sid}.json")
        policy_path = POLICY_DIR / f"{sid}.policy.json"
        policy = load_policy(policy_path)
        ev = json.loads(policy_path.read_text())["expected_value"]

        dp_mean, dp_se = mean_se(run(session, "dp", policy, args.seeds))
        always_mean, always_se = mean_se(run(session, "always", None, args.seeds))
        z = (dp_mean - ev) / dp_se
        print(f"\n{sid}: DP exact {ev:.2f}, sim {dp_mean:.2f} +/- {dp_se:.2f} (z = {z:+.2f}); "
              f"always {always_mean:.2f} +/- {always_se:.2f}")
        rows.append([sid, "dp", "", ev, dp_mean, dp_se])
        rows.append([sid, "always", "", "", always_mean, always_se])

        best = None
        for cap in CAPS:
            m, se = mean_se(run(session, "dp", cap_policy(session, cap), args.seeds))
            rows.append([sid, "cap_first_event", cap, "", m, se])
            if best is None or m > best[1]:
                best = (cap, m, se)
        cap, m, se = best
        print(f"  best cap on rare_drop: {cap} attempts -> {m:.2f} +/- {se:.2f} "
              f"({m - always_mean:+.2f} vs always)")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["session_id", "strategy", "cap_attempts", "dp_expected_value",
                         "mean_reward", "se"])
        writer.writerows(rows)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
