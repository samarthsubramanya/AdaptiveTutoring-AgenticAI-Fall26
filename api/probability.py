"""Bounded probability experiments, independent of the model and database."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from math_lab.probability import run_probability_experiment


router = APIRouter(prefix="/math/probability", tags=["Probability Lab"])


class ExperimentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    experiment: Literal["coin_heads", "dice_sum"]
    trials: Annotated[int, Field(strict=True, ge=1, le=10000)] = 1000
    seed: Annotated[int, Field(strict=True, ge=0, le=2**32 - 1)] = 42
    coin_tosses: Annotated[int, Field(strict=True, ge=1, le=20)] | None = None
    heads_probability: Annotated[float, Field(strict=True, ge=0, le=1, allow_inf_nan=False)] | None = None


@router.post("/experiments")
def run_experiment(body: ExperimentRequest):
    try:
        return run_probability_experiment(**body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
