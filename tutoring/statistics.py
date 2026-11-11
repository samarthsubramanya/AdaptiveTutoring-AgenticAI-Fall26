"""Exact descriptive statistics with explicit population/sample conventions."""

from collections import Counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
import sympy as sp

from tutoring.symbolic import expression


Metric = Literal["mean", "median", "range", "variance", "standard_deviation"]


class StatisticsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    values: list[str] = Field(min_length=1, max_length=100)
    metric: Metric = "mean"
    convention: Literal["population", "sample"] = "population"


def summarize(spec: StatisticsSpec) -> dict:
    data = [expression(v, "x", numeric=True) for v in spec.values]
    if any(not value.is_Rational or abs(value) > 1_000_000 for value in data):
        raise ValueError("Use finite rational data values between -1,000,000 and 1,000,000.")
    ordered = sorted(data)
    n = len(data)
    mean = sum(data) / n
    median = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
    divisor = n - (spec.convention == "sample")
    variance = sum((v - mean) ** 2 for v in data) / divisor if divisor else None
    if variance is None and spec.metric in {"variance", "standard_deviation"}:
        raise ValueError("Sample variance and standard deviation need at least two observations.")
    metrics = {"mean": mean, "median": median, "range": ordered[-1] - ordered[0],
               "variance": variance, "standard_deviation": sp.sqrt(variance) if variance is not None else None}
    counts = Counter(data)
    max_count = max(counts.values())
    modes = sorted(v for v, count in counts.items() if count == max_count) if max_count > 1 else []
    selected = metrics[spec.metric]
    return {"count": n, "values": [float(v) for v in data], "metric": spec.metric,
            "convention": spec.convention, "exact": str(selected), "value": float(selected),
            "metrics": {key: None if value is None else float(value) for key, value in metrics.items()},
            "modes": [str(v) for v in modes], "mode_note": "No repeated values means no mode; ties return every mode.",
            "hint": {"mean": "Add every value, then divide by the number of observations.",
                     "median": "Sort the values. Use the middle value, or average the two middle values.",
                     "range": "Subtract the smallest observation from the largest.",
                     "variance": f"Find squared distances from the mean, add them, then divide by {'n - 1' if spec.convention == 'sample' else 'n'}.",
                     "standard_deviation": "Take the square root of the variance, using the chosen population or sample convention."}[spec.metric],
            "verifier": "exact rational arithmetic", "tolerance": max(1e-8, abs(float(selected)) * 1e-6)}


def verify(spec: StatisticsSpec, answer: str) -> dict:
    result = summarize(spec)
    try:
        given = expression(answer, "x", numeric=True)
        error = abs(float(given) - result["value"])
    except (ValueError, OverflowError) as exc:
        return {**result, "status": "invalid_input", "message": str(exc)}
    correct = error <= result["tolerance"]
    return {**result, "status": "correct" if correct else "incorrect",
            "message": "Your answer matches the selected statistic." if correct else
                       "Recheck the observations and the population/sample convention.",
            "rounding_note": "Numeric checks allow max(1e-8, |expected| × 1e-6) absolute error. Fractions and numeric square roots are accepted."}
