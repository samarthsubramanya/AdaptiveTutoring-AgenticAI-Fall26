"""Explore sampling variation against exact probability distributions."""

import json
import os

import httpx
import pandas as pd
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
EXPERIMENTS = {"Coin heads": "coin_heads", "Sum of two fair dice": "dice_sum"}
EVENT_OPERATORS = {"Exactly": "eq", "At least": "gte", "At most": "lte"}
EVENT_SYMBOLS = {"eq": "=", "gte": "≥", "lte": "≤"}


def clear_result():
    st.session_state.probability_result = None
    st.session_state.pop("probability_compare_trial", None)


def run_experiment(parameters):
    try:
        response = httpx.post(
            f"{API_BASE_URL}/math/probability/experiments",
            json=parameters,
            timeout=10.0,
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict) or not all(
            name in result for name in ("experiment", "title", "parameters", "distribution", "convergence", "summary", "explanation")
        ):
            raise ValueError("Unexpected experiment response")
        return result
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 422:
            st.error("Check the settings: 1–10,000 trials, a seed from 0 to 4,294,967,295, and valid coin settings.")
        else:
            st.error("The probability service could not complete this experiment. Please try again.")
    except httpx.HTTPError:
        st.error("Could not reach the probability service. Start the KernelAI API and try again.")
    except ValueError:
        st.error("The probability service returned an unexpected response. Check API_BASE_URL and restart the API.")
    return None


@st.fragment
def compare_sample_sizes(event, trials):
    earlier = {
        point["trial"]: point
        for point in event["convergence"]
        if point["trial"] < trials and "count" in point and "confidence_interval" in point
    }
    if not earlier:
        return

    sizes = sorted(earlier)
    default = min(sizes, key=lambda size: abs(size - trials / 10))
    with st.expander("Compare sample sizes"):
        st.caption("The earlier sample is the first set of trials from this same run. As trials accumulate, the observed rate can move closer to or farther from theory.")
        selected = st.selectbox(
            "Earlier sample (trials)", sizes, index=sizes.index(default), key="probability_compare_trial",
        )
        theory = event["theoretical_probability"]
        interval_level = event["confidence_interval"]["level"]
        comparison = {"Measure": [
            "Event hits", "Observed rate", "Difference from theory (pp)",
            f"{interval_level:.0%} Wilson interval", "Interval width (pp)",
        ]}
        for label, size, sample in (("Earlier", selected, earlier[selected]), ("Full run", trials, event)):
            observed = sample["observed_probability"]
            lower = sample["confidence_interval"]["lower"]
            upper = sample["confidence_interval"]["upper"]
            unit = "trial" if size == 1 else "trials"
            comparison[f"{label} · {size:,} {unit}"] = [
                f"{sample['count']:,}", f"{observed:.2%}", f"{100 * (observed - theory):+.2f}",
                f"{lower:.2%} to {upper:.2%}", f"{100 * (upper - lower):.2f}",
            ]
        st.table(comparison, hide_index=True, border="horizontal")
        st.caption(f"Difference is the observed rate minus {theory:.2%} theory, in percentage points.")


st.set_page_config(page_title="Probability Lab · KernelAI", page_icon="🎲", layout="centered")
st.title("Probability Lab")
st.caption("Prototype · Seeded experiments · Observed results and theory")
st.write("Compare a random sample with its theoretical distribution. More trials usually reduce sampling variation, but a particular run can move closer to or farther from theory along the way.")
st.caption("The same seed and settings reproduce the same run. No model or database credentials are needed.")

if "probability_result" not in st.session_state:
    clear_result()

experiment_name = st.selectbox(
    "Experiment", list(EXPERIMENTS), key="probability_experiment", on_change=clear_result,
)
experiment = EXPERIMENTS[experiment_name]
track_event = st.checkbox("Track an event", key="probability_track_event")

with st.form("probability_settings"):
    trial_column, seed_column = st.columns(2)
    trials = trial_column.number_input(
        "Number of trials", min_value=1, max_value=10000, value=1000, step=1, key="probability_trials",
    )
    seed = seed_column.number_input(
        "Random seed", min_value=0, max_value=4294967295, value=42, step=1, key="probability_seed",
    )
    parameters = {"experiment": experiment, "trials": trials, "seed": seed}
    if experiment == "coin_heads":
        coin_column, chance_column = st.columns(2)
        parameters["coin_tosses"] = coin_column.slider(
            "Coin tosses per trial", min_value=1, max_value=20, value=4, key="probability_coin_tosses",
        )
        parameters["heads_probability"] = chance_column.slider(
            "Chance of heads (0–1)", min_value=0.0, max_value=1.0, value=0.5, step=0.05,
            key="probability_heads_probability",
        )
        st.caption("One trial counts the heads in this many independent coin tosses.")
    else:
        st.caption("One trial rolls two independent, fair six-sided dice and adds their faces.")
    if track_event:
        condition_column, cutoff_column = st.columns(2)
        condition = condition_column.selectbox(
            "Event condition", list(EVENT_OPERATORS), key="probability_event_condition",
        )
        coin = experiment == "coin_heads"
        cutoff = cutoff_column.number_input(
            "Heads cutoff" if coin else "Dice sum cutoff",
            min_value=0 if coin else 2, max_value=20 if coin else 12,
            value=1 if coin else 7, step=1, key=f"probability_event_value_{experiment}",
        )
        if coin:
            st.caption("The heads cutoff can be at most the number of tosses per trial.")
        parameters["event_operator"] = EVENT_OPERATORS[condition]
        parameters["event_value"] = cutoff
    submitted = st.form_submit_button("Run experiment", type="primary")

if submitted:
    clear_result()
    if track_event and experiment == "coin_heads" and cutoff > parameters["coin_tosses"]:
        st.error(f"Choose a heads cutoff from 0 to {parameters['coin_tosses']} for this run.")
    else:
        with st.spinner("Running experiment…"):
            st.session_state.probability_result = run_experiment(parameters)

result = st.session_state.probability_result
if result is None:
    st.info("Choose the settings and run an experiment to see the sample alongside theory.")
    st.stop()

st.subheader(result["title"])
actual = result["parameters"]
settings = f"{actual['trials']:,} trials · Seed {actual['seed']}"
if result["experiment"] == "coin_heads":
    settings += f" · {actual['coin_tosses']} tosses per trial · P(heads) = {actual['heads_probability']:g}"
st.caption("Displayed run: " + settings)
st.caption("Edit the settings and run again to replace these results.")

event = result.get("event")
if event is not None:
    st.subheader("Event probability")
    outcome = "Heads" if result["experiment"] == "coin_heads" else "Dice sum"
    st.write(f"**{outcome} {EVENT_SYMBOLS[event['operator']]} {event['value']}**")
    st.caption("Matched outcomes · " + ", ".join(map(str, event["outcomes"])))
    observed_event, theoretical_event = st.columns(2)
    observed_event.metric("Observed event rate", f"{event['observed_probability']:.2%}")
    theoretical_event.metric("Theoretical event probability", f"{event['theoretical_probability']:.2%}")
    st.caption(f"Observed in {event['count']:,} of {actual['trials']:,} trials.")
    interval = event["confidence_interval"]
    st.write(
        f"**{interval['level']:.0%} confidence interval (Wilson)** "
        f"· {interval['lower']:.2%} to {interval['upper']:.2%}"
    )
    st.caption("The interval estimates the event probability from the observed hits. The 95% level refers to coverage across repeated samples.")
    event_convergence = pd.DataFrame(event["convergence"])
    st.line_chart(
        pd.DataFrame({
            "Trial": event_convergence["trial"],
            "Observed rate": 100 * event_convergence["observed_probability"],
            "Theoretical probability": 100 * event_convergence["theoretical_probability"],
        }),
        x="Trial", y=["Observed rate", "Theoretical probability"],
        x_label="Completed trials", y_label="Event probability (%)",
    )
    compare_sample_sizes(event, actual["trials"])

summary = result["summary"]
observed_column, expected_column = st.columns(2)
observed_column.metric("Observed mean", f"{summary['observed_mean']:.3f}")
expected_column.metric("Theoretical mean", f"{summary['theoretical_mean']:.3f}")
mean_unit = "Heads per trial" if result["experiment"] == "coin_heads" else "Sum per trial"
st.caption("Mean units: " + mean_unit.lower() + ".")
st.metric(
    "Largest probability gap", f"{100 * summary['max_probability_gap']:.2f} pp",
    help="The largest absolute difference between an observed and theoretical outcome probability, in percentage points.",
)

st.subheader("Observed outcomes and theory")
distribution = pd.DataFrame(result["distribution"])
chart_data = pd.DataFrame({
    "Outcome": distribution["outcome"],
    "Observed": 100 * distribution["observed_probability"],
    "Theoretical": 100 * distribution["theoretical_probability"],
})
st.bar_chart(
    chart_data, x="Outcome", y=["Observed", "Theoretical"], stack=False,
    x_label="Number of heads" if result["experiment"] == "coin_heads" else "Sum of two dice",
    y_label="Probability (%)",
)
st.caption("Bars show percentages; the gap above is measured in percentage points (pp).")

st.subheader("How the sample mean changes")
convergence = pd.DataFrame(result["convergence"]).rename(columns={
    "trial": "Trial", "observed_mean": "Observed mean", "theoretical_mean": "Theoretical mean",
})
st.line_chart(
    convergence, x="Trial", y=["Observed mean", "Theoretical mean"],
    x_label="Completed trials", y_label=mean_unit,
)
st.write(result["explanation"])

with st.expander("Outcome counts and probabilities"):
    st.dataframe(distribution, hide_index=True)

st.download_button(
    "Download this run (JSON)", data=json.dumps(result, indent=2, allow_nan=False),
    file_name=f"probability-{result['experiment']}-seed-{actual['seed']}.json",
    mime="application/json", on_click="ignore",
)
