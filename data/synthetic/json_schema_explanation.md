# What Each JSON Field Actually Means

This guide uses the `A_budget_T010min` session as a running example. It has eight events, played in order and a total time limit of 600 seconds. Rewards are made-up points; all durations are in seconds. Any number changed just to illustrate a case is labelled as hypothetical.

## 1. Getting Oriented

### 01. `schema_version = 1`

This tells us which version of the JSON format the file follows. It is about how the data is structured, not the difficulty of the game.

For instance, a program that understands format version 1 could use this field to decide how to read the file. If a version 2 format appeared later, the program might need a different parser. Our current baseline does not actually check the version, so this is a possible use of the field rather than a feature the code already has.

### 02. `session_id = "A_budget_T010min"`

This is the name of the particular session. It makes it possible to match a set of inputs to the results produced from them.

Imagine finding a results row labelled `A_budget_T010min / E3`. The first part tells you which session to look at, and E3 identifies the event. `A_budget_T030min` would be a different session. One important detail: the actual time limit comes from `budget_seconds`, not from the text in the session name.

### 03. `description = "Experiment A: only the total time budget changes."`

The description is there to help a person understand the session at a glance. It does not affect the calculations.

Here, it tells us why we are comparing the 10-minute session with the 30-minute one: we want to see what changes when players have more time, while the event settings stay the same. Rephrasing the description would not change any result.

### 04. `experiment = "A"`

This groups sessions that belong to the same experiment.

Both the 600-second and 1,800-second sessions are part of Experiment A. When we compare their results, we can focus on the effect of the time budget. The letter A is just a group label; it is not a probability or an action.

---

## 2. How the Session Is Set Up

### 05. `varied_factor = "budget_seconds"`

This names the setting we deliberately change between sessions in the experiment.

For Experiment A, we compare a 600-second budget with a 1,800-second budget while keeping the eight events the same. That way, time is the main difference. The field records what we chose to vary; it does not automatically change any values for us.

### 06. `varied_value = 600`

This records the specific value used for the setting named by `varied_factor`.

Since the varied factor here is `budget_seconds`, the value is 600. In the 30-minute version, we would set both `varied_value` and `budget_seconds` to 1800. That is an extra 1,200 seconds. In another experiment, the varied value might be a probability such as 0.10.

**Difference in available time:** 1,800 − 600 = **1,200 seconds**.

### 07. `budget_seconds = 600`

This is the actual time limit the simulator must respect.

A budget of 600 seconds gives us 10 minutes. Suppose 200 seconds have already been used. We have 400 seconds left. If we retry E3, which takes 60 seconds, we drop to 340 seconds. But if we only had 40 seconds left, we could not make that retry, even if it looked worthwhile.

**Time left after the E3 retry:** 600 − 200 − 60 = **340 seconds**.

### 08. `events = [E1, E2, ..., E8]`

This array stores all eight events in the order we encounter them. Each event has its own probabilities, rewards and time costs.

The first element is E1, the second is E2, and so on. In Python, `events[0]` retrieves E1, whose success probability is 0.65 and whose retry takes 5 seconds. The order comes from the array itself, not from sorting the `event_id` labels.

### A Quick Time-Budget Check

Add the travel times in this session:

`30 + 45 + 60 + 35 + 90 + 25 + 50 + 0 = 335 seconds`

If we travel through all eight events and pay every one of those travel costs, only 265 seconds of the 600-second budget remain for retries and anything else that takes time. The current JSON has no separate field for the duration of an initial attempt, so that time is not part of this sum.

**Remaining time:** 600 − 335 = **265 seconds**.

---

## 3. Event IDs, Chances and Rewards

### 09. `event_id = "E1"`

Every event gets its own label. Together with `session_id`, it tells us exactly which event a result refers to.

For example, `A_budget_T010min / E1` means the event with a 65% success chance and 6 reward points for a good outcome. `A_budget_T010min / E3` means the event with a 10% success chance and 25 points for a good outcome.

### 10. `odds_type = "known"`

This tells the program how the success probability is represented. A known event uses `p`; a beta event uses `alpha` and `beta`.

E1 has known odds, with `p = 0.65`. If attempts are independent, even three failures in a row do not change the next attempt's 65% chance. A hypothetical Beta event would store alpha and beta instead of p, allowing its probability estimate to change as results are observed.

### 11. `p = 0.65`

For a known-odds event, p is the chance that a single attempt produces the good outcome.

With E1, success has probability 0.65 and failure has probability 0.35. Over 100 independent attempts, we would expect roughly 65 successes and 35 failures. An expectation is an average across many possible runs, not a promise about what will happen in one run.

- **Expected successes:** 100 × 0.65 = 65.
- **Expected failures:** 100 × 0.35 = 35.

### 12. `good_reward = 6`

This is the reward for getting the good outcome. It does not increase just because earlier attempts failed.

If E1 succeeds, the good outcome gives 6 points. If the first attempt fails and we accept that result, we get 0. With a 65% success chance, the expected reward from accepting the first outcome is 3.9 points, before any entry cost.

**Expected reward:** (0.65 × 6) + (0.35 × 0) = **3.9 points**.

### 13. `bad_reward = 0`

This is what we receive if the outcome is bad and we choose to accept it rather than retry.

In the original E1 data, that is 0 points. Now imagine `bad_reward = 2` instead. The expected first-outcome reward becomes 4.6 points. With the retained-reward term set to zero, a retry after a bad outcome has an expected improvement of 2.6 points, not 3.9.

**Hypothetical case:**

- Expected first-outcome reward = (0.65 × 6) + (0.35 × 2) = **4.6**.
- Retry gain = 0.65 × (6 − 2) = **2.6**.

---

## 4. Retries, Travel Time and Other Costs

### 14. `retry_seconds = 5`

This is the extra time spent when we retry an event after a bad outcome. It does not include travelling to the next event.

Suppose E1 fails three times, and the fourth attempt succeeds. We made three retries after the first attempt, so the retry time is 3 × 5 = 15 seconds. If we made three retries at E3 instead, they would take 3 × 60 = 180 seconds. Neither calculation includes the time for the first attempt.

### 15. `travel_seconds = 30`

This is the time it takes to move from the current event to the next one. Staying at the same event to retry does not make us pay that travel time again.

After the E1 sequence just described, continuing to E2 adds 30 seconds. The three retries and onward travel therefore account for 15 + 30 = 45 seconds, not counting the initial attempt. E8 has `travel_seconds = 0`, because there is no next event.

**Three E1 retries plus travel:** (3 × 5) + 30 = **45 seconds**.

### 16. `entry_cost = 0.0`

This is a one-time cost for entering an event. It is measured in reward points, so it reduces our reward total rather than our time budget.

E1 has no entry cost, leaving its expected first-outcome reward at 3.9 points. If we hypothetically set `entry_cost = 1.5`, a success would be worth 4.5 points after the charge, and an accepted failure would be worth −1.5. The expected net reward would fall to 2.4 points. We would not pay the entry cost again every time we retry.

**Hypothetical net expected reward:** 3.9 − 1.5 = **2.4 points**.

### 17. `retained_failure_reward = 0.0`

This is the h term in the retry rule used by the current baseline:

`q × (good_reward − bad_reward) + h`

In this implementation, h is added for each purchased retry.

For E1, h is zero, so the expected gain from a retry is 0.65 × (6 − 0) = 3.9 points. Divide by the 5-second retry time to get 0.78 points per second. If h were hypothetically 0.5, the gain would be 4.4 points and the rate would become 0.88 points per second. The code adds h directly; it does not multiply h by the failure probability.

- **With h = 0:** 3.9 / 5 = 0.78 points/second.
- **With h = 0.5:** 4.4 / 5 = 0.88 points/second.

### One Distinction Worth Keeping Straight

`bad_reward` is the reward we accept when we stop after a bad outcome. `retained_failure_reward` is an extra term in the retry calculation.

If a different game awarded a bonus only when the new attempt failed, we would normally weight that bonus by the probability of failure. That is not how the current baseline formula handles h.

---

## 5. Checking That the Fields Make Sense

### Should We Retry E1?

Use the original E1 values:

| Field | Value |
|---|---:|
| `p` | 0.65 |
| `good_reward` | 6 |
| `bad_reward` | 0 |
| `retry_seconds` | 5 |
| `entry_cost` | 0 |
| `retained_failure_reward` | 0 |

Say the first attempt has failed and we still have at least five seconds available.

1. The expected additional reward from retrying is 0.65 × (6 − 0) + 0 = **3.9 points**.
2. Because the retry takes five seconds, its reward rate is 3.9 / 5 = **0.78 points per second**.
3. Suppose we use an illustrative time-value threshold **rho = 0.50**. Five seconds then cost us the equivalent of 0.50 × 5 = 2.5 points. Since 3.9 is greater than 2.5, the rule says **retry**.
4. At **rho = 0.80**, those five seconds are worth 4 points. Now 3.9 is less than 4, so the rule says **accept the bad outcome and move on**.

Rho is a reward-per-second threshold that we calculate or supply separately; it is not a field in this JSON. Travel time is paid when we move on. The entry cost is already sunk at the point when we decide whether to retry, so we do not subtract it again in this comparison.

### Does the Full Session Fit Into 10 Minutes?

Consider a run that reaches all eight events, pays every travel cost, and makes four retries at E3 but no retries anywhere else. Travel uses 335 seconds, and E3 retries use 4 × 60 = 240 seconds.

Together that is **575 seconds**, leaving **25 seconds**. A fifth E3 retry would push the accounted total to **635 seconds**, or **35 seconds over budget**.

This is only a timing example, not a recommendation or simulated result. We would also need to account for any initial-attempt time separately.

### What About Alpha and Beta?

These two fields are used when `odds_type = "beta"`. They do not appear in the known-odds E1 JSON, but they matter if we model a success chance that is learned over time.

As an example, take `alpha = 1` and `beta = 49`. The prior mean success chance is:

`1 / (1 + 49) = 2%`

After 50 observed failures, the estimate becomes:

`1 / (1 + 49 + 50) = 1%`

**Alpha** is the success-side shape parameter. If we hold beta at 49 and increase alpha from 1 to 2, the prior mean rises to 2 / 51, or about 3.92%.

**Beta** is the failure-side shape parameter. Keeping alpha at 1 and increasing beta from 49 to 99 lowers the prior mean to 1 / 100 = 1%.

The observed-failure count k is supplied separately; it is not a JSON field here.

### What These Examples Do (and Do Not) Show

The actual values come from the supplied session JSON and the baseline implementation examined for this project. The version-check and result-lookup cases explain how metadata could be used. Changes to costs, retained reward and rho are hypothetical. None of these illustrations claims to be a measured simulation result.

**Code reference:** Save-scumming repository, `vivaan/synthetic-data-rho` branch.
