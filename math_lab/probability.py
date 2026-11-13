"""Seeded finite probability experiments compared with exact analytical models."""

import math
import random
from operator import eq, ge, le
from statistics import NormalDist


EVENT_OPERATORS = {"eq": eq, "gte": ge, "lte": le}
WILSON_95_Z = NormalDist().inv_cdf(0.975)


def _wilson_interval(count: int, trials: int) -> dict[str, float]:
    rate = count / trials
    z_squared = WILSON_95_Z**2
    scale = 1 + z_squared / trials
    center = (rate + z_squared / (2 * trials)) / scale
    margin = WILSON_95_Z * math.sqrt(rate * (1 - rate) / trials + z_squared / (4 * trials**2)) / scale
    return {
        "level": 0.95,
        "lower": 0.0 if count == 0 else center - margin,
        "upper": 1.0 if count == trials else center + margin,
    }


def run_probability_experiment(
    experiment: str,
    trials: int = 1000,
    seed: int = 42,
    coin_tosses: int | None = None,
    heads_probability: float | None = None,
    event_operator: str | None = None,
    event_value: int | None = None,
) -> dict:
    """Simulate binomial heads counts or two-dice sums without changing global randomness."""
    if experiment not in ("coin_heads", "dice_sum"):
        raise ValueError("Choose coin_heads or dice_sum.")
    if type(trials) is not int or not 1 <= trials <= 10_000:
        raise ValueError("Trials must be an integer from 1 to 10000.")
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("Seed must be an integer from 0 to 4294967295.")
    parameters = {"trials": trials, "seed": seed}
    if experiment == "coin_heads":
        n = 10 if coin_tosses is None else coin_tosses
        p = 0.5 if heads_probability is None else heads_probability
        if type(n) is not int or not 1 <= n <= 20:
            raise ValueError("Coin tosses must be an integer from 1 to 20.")
        if type(p) not in (int, float) or not 0 <= p <= 1 or not math.isfinite(p):
            raise ValueError("Heads probability must be a finite number from 0 to 1.")
        p = float(p)
        parameters.update(coin_tosses=n, heads_probability=p)
        outcomes = range(n + 1)
        theoretical = {k: math.comb(n, k) * p**k * (1 - p)**(n - k) for k in outcomes}
        theoretical_mean = n * p
        title = "Heads in independent coin tosses"
        explanation = (
            "Theory uses the binomial model: P(K=k) = C(n,k) p^k (1-p)^(n-k) "
            "for n independent tosses with heads probability p. "
        )
    else:
        if coin_tosses is not None or heads_probability is not None:
            raise ValueError("Coin options do not apply to dice_sum.")
        outcomes = range(2, 13)
        theoretical = {k: (6 - abs(7 - k)) / 36 for k in outcomes}
        theoretical_mean = 7.0
        title = "Sum of two fair six-sided dice"
        explanation = (
            "Theory counts the 36 equally likely ordered pairs of two independent fair dice. "
            "A sum of 7 occurs in six pairs, so its theoretical probability is 1/6. "
        )
    event = None
    matching_outcomes = set()
    if event_operator is not None or event_value is not None:
        if not isinstance(event_operator, str) or event_operator not in EVENT_OPERATORS:
            raise ValueError("Choose an event operator: eq, gte, or lte.")
        if type(event_value) is not int or event_value not in outcomes:
            raise ValueError(f"The event cutoff must be an integer from {outcomes.start} to {outcomes.stop - 1}.")
        matches = EVENT_OPERATORS[event_operator]
        matching_outcomes = {outcome for outcome in outcomes if matches(outcome, event_value)}
        theoretical_probability = (
            1.0 if matching_outcomes == set(outcomes)
            else min(1.0, math.fsum(theoretical[outcome] for outcome in matching_outcomes))
        )
        event = {
            "operator": event_operator,
            "value": event_value,
            "outcomes": sorted(matching_outcomes),
            "theoretical_probability": theoretical_probability,
            "convergence": [],
        }

    rng = random.Random(seed)
    counts = dict.fromkeys(outcomes, 0)
    convergence = []
    total = 0
    event_count = 0
    interval = math.ceil(trials / 100)
    for trial in range(1, trials + 1):
        if experiment == "coin_heads":
            outcome = sum(rng.random() < p for _ in range(n))
        else:
            outcome = rng.randint(1, 6) + rng.randint(1, 6)
        counts[outcome] += 1
        total += outcome
        if outcome in matching_outcomes:
            event_count += 1
        if trial == 1 or trial % interval == 0 or trial == trials:
            convergence.append({"trial": trial, "observed_mean": total / trial,
                                "theoretical_mean": theoretical_mean})
            if event is not None:
                event["convergence"].append({
                    "trial": trial,
                    "count": event_count,
                    "observed_probability": event_count / trial,
                    "theoretical_probability": event["theoretical_probability"],
                    "confidence_interval": _wilson_interval(event_count, trial),
                })
    distribution = [
        {"outcome": outcome, "count": counts[outcome],
         "observed_probability": counts[outcome] / trials,
         "theoretical_probability": theoretical[outcome]}
        for outcome in outcomes
    ]
    result = {
        "experiment": experiment, "title": title, "parameters": parameters,
        "distribution": distribution, "convergence": convergence,
        "summary": {
            "observed_mean": total / trials, "theoretical_mean": theoretical_mean,
            "max_probability_gap": max(abs(row["observed_probability"] - row["theoretical_probability"])
                                       for row in distribution),
        },
        "explanation": explanation + (
            "Observed frequencies and cumulative means come from this finite, seeded simulation. "
            "Sampling variation can produce differences from theory. More trials need not make "
            "every gap decrease, and the cumulative mean need not approach theory monotonically."
        ),
    }
    if event is not None:
        final_sample = event["convergence"][-1]
        event.update(
            count=final_sample["count"],
            observed_probability=final_sample["observed_probability"],
            confidence_interval=final_sample["confidence_interval"],
        )
        result["event"] = event
    return result
