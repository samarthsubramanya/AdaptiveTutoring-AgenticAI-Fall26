# Probability Experiments

Use `run_probability_experiment` to explore probability through simulation
and compare observed outcomes with a theoretical distribution.

Supported experiments:

- `coin_heads`: count heads in a set of independent coin tosses. The coin
  may be biased. Use `coin_tosses` and `heads_probability` to set the model.
- `dice_sum`: sum two independent, fair six-sided dice. Do not pass coin options.

For an event such as a dice sum of at least 9, use `event_operator: gte`
and `event_value: 9`. Use `eq` for exactly and `lte` for at most. Explain the
theoretical probability as the sum of the probabilities of matching outcomes.

Preserve the user's requested settings. Ask for clarification if their random
experiment differs from these assumptions. Use a stated seed to reproduce a run.
Report observed counts as simulated measurements, and theoretical probabilities
as model predictions. Explain what counts as one trial.

Sampling variation can remain even after many trials. Do not claim that a
larger sample must be closer in every run, that a short run proves fairness,
or that a random event becomes due after a streak. No live physical experiment
or student-learning evaluation is performed by this tool.

For charts, settings, and downloadable run data, direct users to Probability Lab.
