"""Analytical models, sampling invariants, and bounded input handling."""

import random
from collections import Counter

import pytest

from math_lab.probability import run_probability_experiment


@pytest.mark.parametrize("experiment,options", [
    ("coin_heads", {}), ("coin_heads", {"coin_tosses": 20, "heads_probability": 0.2}),
    ("dice_sum", {}),
])
def test_distributions_and_convergence_match_the_actual_counts(experiment, options):
    result = run_probability_experiment(experiment, trials=9999, seed=123, **options)
    distribution = result["distribution"]
    assert sum(row["count"] for row in distribution) == 9999
    assert sum(row["observed_probability"] for row in distribution) == pytest.approx(1)
    assert sum(row["theoretical_probability"] for row in distribution) == pytest.approx(1)
    observed_mean = sum(row["outcome"] * row["count"] for row in distribution) / 9999
    assert result["summary"]["observed_mean"] == observed_mean
    assert result["summary"]["max_probability_gap"] == max(
        abs(row["observed_probability"] - row["theoretical_probability"]) for row in distribution
    )
    convergence = result["convergence"]
    assert 2 <= len(convergence) <= 101
    assert convergence[0]["trial"] == 1
    assert convergence[-1]["trial"] == 9999
    assert convergence[-1]["observed_mean"] == observed_mean
    assert all(point["theoretical_mean"] == result["summary"]["theoretical_mean"] for point in convergence)
    assert [point["trial"] for point in convergence] == sorted({point["trial"] for point in convergence})


def test_coin_theory_matches_known_binomial_probabilities_and_tails():
    fair = run_probability_experiment("coin_heads", coin_tosses=4)
    assert [row["theoretical_probability"] for row in fair["distribution"]] == [1/16, 4/16, 6/16, 4/16, 1/16]
    biased = run_probability_experiment("coin_heads", coin_tosses=3, heads_probability=0.25)
    assert [row["theoretical_probability"] for row in biased["distribution"]] == [27/64, 27/64, 9/64, 1/64]
    assert biased["summary"]["theoretical_mean"] == 0.75
    tails = run_probability_experiment("coin_heads", trials=1, coin_tosses=20)
    assert [tails["distribution"][index]["theoretical_probability"] for index in (0, -1)] == [1/2**20] * 2
    assert len(tails["distribution"]) == 21
    assert sum(row["count"] == 0 for row in tails["distribution"]) == 20


@pytest.mark.parametrize("probability,outcome", [(0, 0), (1, 10)])
def test_degenerate_coin_probabilities_keep_zero_probability_outcomes(probability, outcome):
    result = run_probability_experiment("coin_heads", trials=5, heads_probability=probability)
    assert len(result["distribution"]) == 11
    for row in result["distribution"]:
        assert row["count"] == (5 if row["outcome"] == outcome else 0)
        assert row["theoretical_probability"] == (1 if row["outcome"] == outcome else 0)
    assert result["summary"] == {"observed_mean": outcome, "theoretical_mean": outcome, "max_probability_gap": 0}


def test_dice_theory_is_the_exact_ordered_pair_distribution():
    result = run_probability_experiment("dice_sum")
    assert [row["outcome"] for row in result["distribution"]] == list(range(2, 13))
    assert [row["theoretical_probability"] for row in result["distribution"]] == [
        count / 36 for count in (1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1)
    ]
    assert result["distribution"][5]["theoretical_probability"] == 1/6
    assert result["summary"]["theoretical_mean"] == 7
    assert result["parameters"] == {"trials": 1000, "seed": 42}


@pytest.mark.parametrize("experiment", ["coin_heads", "dice_sum"])
def test_reproducible_local_rng_does_not_change_global_random_state(experiment):
    state = random.getstate()
    first = run_probability_experiment(experiment, trials=500, seed=12)
    assert random.getstate() == state
    assert first == run_probability_experiment(experiment, trials=500, seed=12)
    assert first["distribution"] != run_probability_experiment(experiment, trials=500, seed=13)["distribution"]
    assert random.getstate() == state


@pytest.mark.parametrize("trials", [1, 2, 100, 101, 199, 10000])
def test_trial_boundaries_include_first_and_final_convergence_points(trials):
    result = run_probability_experiment("dice_sum", trials=trials, seed=2**32-1)
    assert result["convergence"][0]["trial"] == 1
    assert result["convergence"][-1]["trial"] == trials
    assert len(result["convergence"]) <= 101
    assert sum(row["count"] for row in result["distribution"]) == trials


@pytest.mark.parametrize("field,bad", [
    ("trials", 0), ("trials", 10001), ("trials", True), ("trials", 1.5), ("trials", "10"),
    ("seed", -1), ("seed", 2**32), ("seed", False), ("seed", 1.0), ("seed", "42"),
    ("coin_tosses", 0), ("coin_tosses", 21), ("coin_tosses", True), ("coin_tosses", 2.0),
    ("heads_probability", -0.1), ("heads_probability", 1.1), ("heads_probability", float("nan")),
    ("heads_probability", float("inf")), ("heads_probability", -float("inf")),
    ("heads_probability", True), ("heads_probability", "0.5"), ("heads_probability", 10**1000),
])
def test_invalid_values_fail_before_simulation(field, bad):
    with pytest.raises(ValueError):
        run_probability_experiment("coin_heads", **{field: bad})


@pytest.mark.parametrize("options", [{"coin_tosses": 10}, {"heads_probability": 0.5},
                                     {"coin_tosses": False}, {"heads_probability": 0}])
def test_dice_rejects_coin_only_options(options):
    with pytest.raises(ValueError, match="Coin options"):
        run_probability_experiment("dice_sum", **options)


@pytest.mark.parametrize("experiment", ["", "coin", "__import__('os')", None, False, [], {}])
def test_unknown_experiments_are_rejected(experiment):
    with pytest.raises(ValueError):
        run_probability_experiment(experiment)


def test_dice_event_uses_the_same_trials_as_the_distribution():
    settings = {"experiment": "dice_sum", "trials": 1000, "seed": 42}
    baseline = run_probability_experiment(**settings)
    result = run_probability_experiment(**settings, event_operator="gte", event_value=9)
    event = result.pop("event")
    assert result == baseline
    assert event["outcomes"] == [9, 10, 11, 12]
    assert event["theoretical_probability"] == pytest.approx(10 / 36)

    rng = random.Random(42)
    rolls = [rng.randint(1, 6) + rng.randint(1, 6) for _ in range(1000)]
    assert event["count"] == sum(Counter(rolls)[value] for value in range(9, 13)) == 300
    assert event["observed_probability"] == 0.3
    assert event["confidence_interval"] == pytest.approx({
        "level": 0.95, "lower": 0.272407, "upper": 0.329124,
    }, abs=0.000001)
    assert [point["trial"] for point in event["convergence"]] == [
        point["trial"] for point in result["convergence"]
    ]
    for point in event["convergence"]:
        trial = point["trial"]
        assert point["observed_probability"] == sum(roll >= 9 for roll in rolls[:trial]) / trial
        assert point["theoretical_probability"] == pytest.approx(10 / 36)


@pytest.mark.parametrize("operator,cutoff,outcomes,probability", [
    ("eq", 2, [2], 6 / 16), ("lte", 1, [0, 1], 5 / 16), ("gte", 3, [3, 4], 5 / 16),
    ("gte", 0, [0, 1, 2, 3, 4], 1.0),
])
def test_coin_events_sum_the_matching_binomial_probabilities(operator, cutoff, outcomes, probability):
    event = run_probability_experiment(
        "coin_heads", coin_tosses=4, event_operator=operator, event_value=cutoff,
    )["event"]
    assert event["outcomes"] == outcomes
    assert event["theoretical_probability"] == pytest.approx(probability)


@pytest.mark.parametrize("event", [
    {"event_operator": "gte"}, {"event_value": 9}, {"event_operator": "gt", "event_value": 9},
    {"event_operator": "eq", "event_value": True}, {"event_operator": "eq", "event_value": "9"},
    {"event_operator": "lte", "event_value": 1}, {"event_operator": "gte", "event_value": 13},
])
def test_invalid_dice_events_are_rejected(event):
    with pytest.raises(ValueError, match="event"):
        run_probability_experiment("dice_sum", **event)


def test_coin_event_cutoff_cannot_exceed_the_number_of_tosses():
    with pytest.raises(ValueError, match="0 to 4"):
        run_probability_experiment("coin_heads", coin_tosses=4, event_operator="gte", event_value=5)


@pytest.mark.parametrize("heads_probability,expected_interval", [
    (0.0, {"level": 0.95, "lower": 0.0, "upper": 0.27753280}),
    (1.0, {"level": 0.95, "lower": 0.72246720, "upper": 1.0}),
])
def test_wilson_interval_stays_bounded_with_zero_or_all_hits(heads_probability, expected_interval):
    event = run_probability_experiment(
        "coin_heads", trials=10, coin_tosses=1, heads_probability=heads_probability,
        event_operator="eq", event_value=1,
    )["event"]
    assert event["confidence_interval"] == pytest.approx(expected_interval)
