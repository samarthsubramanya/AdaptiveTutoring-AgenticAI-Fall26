# Probability Lab

A work-in-progress mathematical experiment workspace. Run a simulated experiment,
compare observed frequencies with a theoretical distribution, and inspect how
the sample mean changes as trials accumulate. Each run can be downloaded as JSON.

This is a separate probability/statistics track from the algebra and linear-system
tutors. It uses the standard library and needs no model or database credentials.

## Experiments

- **Coin heads:** one trial consists of `n` independent tosses. The outcome is
  the number of heads. With heads probability `p`, the theoretical probability
  of exactly `k` heads is `C(n,k) p^k (1-p)^(n-k)` and the mean is `np`.
- **Dice sum:** one trial rolls two independent fair six-sided dice and adds
  them. There are 36 equally likely ordered pairs, so sum 7 has probability
  `6/36` and the theoretical mean is 7.

The distribution chart compares simulated relative frequencies with those model
probabilities. The convergence chart shows the cumulative average outcome, not
a forecast. A larger sample tends to stabilize estimates, but an individual run
need not move closer at every step. Probabilities use floating-point arithmetic.

## Run

With the existing requirements installed and the virtual environment active,
start the API from the repository root:

```sh
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000
```

In another terminal, start the dedicated math workspace:

```sh
python -m streamlit run ui/pages/5_Probability_Lab.py
```

The page is also available in the normal multipage app. Use `API_BASE_URL` for
another backend address. The agent can discover the `probability` skill when
the existing MCP server and model configuration are running.

## Demonstrate

1. Run 100 dice trials and inspect the observed distribution alongside theory.
2. Repeat the same settings and seed to reproduce the result.
3. Change the seed to see sampling variation, then increase the trial count.
4. Enable **Track an event**, select **At least**, and set the dice sum cutoff
   to 9. The matching sums are 9 through 12, with theoretical probability
   `(4 + 3 + 2 + 1) / 36 = 27.78%`. With 1,000 trials and seed 42, 300 trials
   meet the condition, giving an observed rate of 30.00%.
5. Read the chart to see the observed event rate as trials accumulate. The
   [95% Wilson interval](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm)
   estimates the event probability from the sample. Its confidence level
   describes the method's coverage over repeated samples.
6. Switch to coins, try a biased coin, and compare the mean with `np`.
7. Download the run to inspect its settings, counts, probabilities, sampled
   cumulative means, and event results when selected.

API example:

```sh
curl http://127.0.0.1:8000/math/probability/experiments \
  -H 'Content-Type: application/json' \
  -d '{"experiment":"dice_sum","trials":1000,"seed":42,"event_operator":"gte","event_value":9}'
```

Runs are bounded to 10,000 trials and 20 tosses per coin trial. The seed controls
a local random generator; other requests and the global generator are unaffected.
This prototype simulates known models. It does not measure physical randomness,
certify fairness, or assess student mastery.

## Validate

```sh
python -m pytest tests/test_probability_lab.py tests/test_probability_lab_api.py tests/test_probability_lab_ui.py
```
