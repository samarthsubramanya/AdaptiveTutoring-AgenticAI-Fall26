"""Agent access to the same experiments shown in Probability Lab."""

from typing import Annotated

from pydantic import Field

from math_lab.probability import run_probability_experiment as _run


async def run_probability_experiment(
    experiment: str,
    trials: Annotated[int, Field(strict=True)] = 1000,
    seed: Annotated[int, Field(strict=True)] = 42,
    coin_tosses: Annotated[int, Field(strict=True)] | None = None,
    heads_probability: Annotated[float, Field(strict=True)] | None = None,
) -> dict:
    """Simulate coin_heads or dice_sum and compare observations with theory.

    coin_heads counts heads in coin_tosses independent tosses (default 10)
    with heads_probability (default 0.5). dice_sum adds two fair six-sided dice
    and accepts no coin settings. Use 1..10000 trials and a nonnegative 32-bit
    seed. Returns actual counts, theoretical probabilities, and sample means.
    """
    return _run(experiment, trials, seed, coin_tosses, heads_probability)
