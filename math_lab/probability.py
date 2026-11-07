"""Seeded finite probability experiments compared with exact analytical models."""

import math
import random


def run_probability_experiment(
    experiment: str,
    trials: int = 1000,
    seed: int = 42,
    coin_tosses: int | None = None,
    heads_probability: float | None = None,
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
    rng = random.Random(seed)
    counts = dict.fromkeys(outcomes, 0)
    convergence = []
    total = 0
    interval = math.ceil(trials / 100)
    for trial in range(1, trials + 1):
        if experiment == "coin_heads":
            outcome = sum(rng.random() < p for _ in range(n))
        else:
            outcome = rng.randint(1, 6) + rng.randint(1, 6)
        counts[outcome] += 1
        total += outcome
        if trial == 1 or trial % interval == 0 or trial == trials:
            convergence.append({"trial": trial, "observed_mean": total / trial,
                                "theoretical_mean": theoretical_mean})
    distribution = [
        {"outcome": outcome, "count": counts[outcome],
         "observed_probability": counts[outcome] / trials,
         "theoretical_probability": theoretical[outcome]}
        for outcome in outcomes
    ]
    return {
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
