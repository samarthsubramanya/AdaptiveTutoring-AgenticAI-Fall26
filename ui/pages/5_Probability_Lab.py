"""Explore sampling variation against exact probability distributions."""

import json
import os

import httpx
import pandas as pd
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
EXPERIMENTS = {"Coin heads": "coin_heads", "Sum of two fair dice": "dice_sum"}


def clear_result():
    st.session_state.probability_result = None


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
    submitted = st.form_submit_button("Run experiment", type="primary")

if submitted:
    clear_result()
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
