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
    population_size: int | None = None,
    marked_items: int | None = None,
    draws: int | None = None,
) -> dict:
    """Simulate bounded discrete experiments using a local seeded generator."""
    if experiment not in ("coin_heads", "dice_sum", "urn_draw"):
        raise ValueError("Choose coin_heads, dice_sum, or urn_draw.")
    if type(trials) is not int or not 1 <= trials <= 10_000:
        raise ValueError("Trials must be an integer from 1 to 10000.")
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("Seed must be an integer from 0 to 4294967295.")
    if experiment != "urn_draw" and any(value is not None for value in (population_size, marked_items, draws)):
        raise ValueError("Population options apply only to urn_draw.")
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
    elif experiment == "dice_sum":
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
    else:
        if coin_tosses is not None or heads_probability is not None:
            raise ValueError("Coin options do not apply to urn_draw.")
        population_size = 20 if population_size is None else population_size
        marked_items = 5 if marked_items is None else marked_items
        draws = 5 if draws is None else draws
        if type(population_size) is not int or not 2 <= population_size <= 200:
            raise ValueError("Population size must be an integer from 2 to 200.")
        if type(marked_items) is not int or not 0 <= marked_items <= population_size:
            raise ValueError("Marked items must be an integer from 0 to the population size.")
        if type(draws) is not int or not 1 <= draws <= min(20, population_size):
            raise ValueError("Draws must be an integer from 1 to the smaller of 20 and the population size.")
        parameters.update(population_size=population_size, marked_items=marked_items, draws=draws)
        outcomes = range(draws + 1)
        total_samples = math.comb(population_size, draws)
        theoretical = {
            marked: math.comb(marked_items, marked)
            * math.comb(population_size - marked_items, draws - marked) / total_samples
            for marked in outcomes
        }
        theoretical_mean = draws * marked_items / population_size
        title = "Marked items drawn without replacement"
        explanation = (
            "Each trial takes a uniform sample without replacement from the population. "
            "The outcome counts marked items in that sample. Theory uses the hypergeometric "
            "model: P(X=k) = C(K,k) C(N-K,n-k) / C(N,n), with mean nK/N. "
            "Draws within a trial depend on earlier draws. The full population is restored "
            "before the next trial, so separate trials are independent. "
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
        elif experiment == "dice_sum":
            outcome = rng.randint(1, 6) + rng.randint(1, 6)
        else:
            outcome = sum(item < marked_items for item in rng.sample(range(population_size), draws))
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
