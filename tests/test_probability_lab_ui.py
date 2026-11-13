"""Exercise the probability page with API responses, without running services."""

from copy import deepcopy
import json
from pathlib import Path

import httpx
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest


PAGE = Path(__file__).parents[1] / "ui/pages/5_Probability_Lab.py"


def example_result(experiment):
    if experiment == "coin_heads":
        distribution = [
            {"outcome": 0, "count": 2, "observed_probability": 0.25, "theoretical_probability": 0.25},
            {"outcome": 1, "count": 3, "observed_probability": 0.375, "theoretical_probability": 0.5},
            {"outcome": 2, "count": 3, "observed_probability": 0.375, "theoretical_probability": 0.25},
        ]
        parameters = {"trials": 8, "seed": 17, "coin_tosses": 2, "heads_probability": 0.5}
        title, observed, theoretical, gap = "Heads in two coin tosses", 1.125, 1.0, 0.125
    else:
        distribution = [
            {"outcome": outcome, "count": 8 if outcome == 7 else 0,
             "observed_probability": 1.0 if outcome == 7 else 0.0,
             "theoretical_probability": (6 - abs(7 - outcome)) / 36}
            for outcome in range(2, 13)
        ]
        parameters = {"trials": 8, "seed": 17}
        title, observed, theoretical, gap = "Sum of two fair dice", 7.0, 7.0, 5 / 6
    return {
        "experiment": experiment, "title": title, "parameters": parameters,
        "distribution": distribution,
        "convergence": [{"trial": 1, "observed_mean": 0 if experiment == "coin_heads" else 7,
                         "theoretical_mean": theoretical},
                        {"trial": 8, "observed_mean": observed, "theoretical_mean": theoretical}],
        "summary": {"observed_mean": observed, "theoretical_mean": theoretical, "max_probability_gap": gap},
        "explanation": "A sample can move closer to or farther from the theoretical mean as trials accumulate.",
    }


COIN_EVENT = {
    "operator": "gte", "value": 2, "outcomes": [2], "count": 3,
    "observed_probability": 0.375, "theoretical_probability": 0.25,
    "convergence": [
        {"trial": 1, "observed_probability": 0.0, "theoretical_probability": 0.25},
        {"trial": 8, "observed_probability": 0.375, "theoretical_probability": 0.25},
    ],
    "confidence_interval": {"level": 0.95, "lower": 0.1368, "upper": 0.6943},
}


@pytest.fixture
def probability_api(monkeypatch):
    calls, exports = [], []

    def post(url, *, json, timeout):
        assert timeout == 10.0
        calls.append((url, deepcopy(json)))
        result = example_result(json["experiment"])
        if "event_operator" in json:
            result["event"] = COIN_EVENT
        return httpx.Response(200, json=result, request=httpx.Request("POST", url))

    original_download = st.download_button

    def download(*args, **kwargs):
        exports.append(json.loads(kwargs["data"]))
        return original_download(*args, **kwargs)

    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setattr(st, "download_button", download)
    return calls, exports


def run(app):
    next(button for button in app.button if button.label == "Run experiment").click().run()
    assert not app.exception


def test_coin_controls_send_settings_and_render_charts_metrics_and_export(probability_api):
    calls, exports = probability_api
    app = AppTest.from_file(str(PAGE), default_timeout=15).run()
    assert not app.exception
    assert not calls
    assert not app.metric
    assert not app.get("vega_lite_chart")
    app.number_input(key="probability_trials").set_value(8)
    app.number_input(key="probability_seed").set_value(17)
    app.slider(key="probability_coin_tosses").set_value(2)
    app.slider(key="probability_heads_probability").set_value(0.5)
    run(app)
    assert calls == [("http://127.0.0.1:8000/math/probability/experiments", {
        "experiment": "coin_heads", "trials": 8, "seed": 17, "coin_tosses": 2, "heads_probability": 0.5,
    })]
    assert [metric.value for metric in app.metric] == ["1.125", "1.000", "12.50 pp"]
    assert len(app.get("vega_lite_chart")) == 2
    assert exports[-1] == example_result("coin_heads")
    assert app.session_state["probability_result"] == exports[-1]
    assert len(app.get("download_button")) == 1


def test_displayed_run_and_export_stay_bound_to_response_when_settings_are_edited(probability_api):
    calls, exports = probability_api
    app = AppTest.from_file(str(PAGE), default_timeout=15).run()
    run(app)
    app.number_input(key="probability_trials").set_value(200)
    app.number_input(key="probability_seed").set_value(99).run()
    displayed = next(item.value for item in app.caption if item.value.startswith("Displayed run:"))
    assert "8 trials · Seed 17" in displayed
    assert "200" not in displayed and "Seed 99" not in displayed
    assert len(calls) == 1
    assert exports[-1]["parameters"] == example_result("coin_heads")["parameters"]
    assert not app.exception


def test_switching_to_dice_clears_results_and_omits_coin_parameters(probability_api):
    calls, exports = probability_api
    app = AppTest.from_file(str(PAGE), default_timeout=15).run()
    run(app)
    app.selectbox(key="probability_experiment").select("Sum of two fair dice").run()
    assert app.session_state["probability_result"] is None
    assert not app.metric
    assert not app.get("vega_lite_chart")
    assert not app.get("download_button")
    assert not app.slider
    assert len(calls) == 1
    run(app)
    assert set(calls[-1][1]) == {"experiment", "trials", "seed"}
    assert calls[-1][1]["experiment"] == "dice_sum"
    assert len(app.get("vega_lite_chart")) == 2
    assert exports[-1] == example_result("dice_sum")
    assert any("Mean units: sum per trial" in item.value for item in app.caption)


def test_event_chart_and_export_follow_the_run_as_event_settings_change(probability_api):
    calls, exports = probability_api
    app = AppTest.from_file(str(PAGE), default_timeout=15).run()
    app.checkbox(key="probability_track_event").check().run()
    assert not calls
    app.number_input(key="probability_trials").set_value(8)
    app.slider(key="probability_coin_tosses").set_value(2)
    app.selectbox(key="probability_event_condition").select("At least")
    cutoff = "probability_event_value_coin_heads"
    app.number_input(key=cutoff).set_value(2)
    run(app)

    assert calls[-1][1]["event_operator"] == "gte"
    assert calls[-1][1]["event_value"] == 2
    assert [metric.value for metric in app.metric][:2] == ["37.50%", "25.00%"]
    assert len(app.get("vega_lite_chart")) == 3
    assert any(item.value == "**Heads ≥ 2**" for item in app.markdown)
    assert any("95% confidence interval (Wilson)" in item.value for item in app.markdown)
    assert any("Observed in 3 of 8 trials" in item.value for item in app.caption)
    assert any("Matched outcomes · 2" == item.value for item in app.caption)
    assert exports[-1]["event"] == COIN_EVENT

    app.selectbox(key="probability_event_condition").select("At most")
    app.number_input(key=cutoff).set_value(1).run()
    assert len(calls) == 1
    assert any(item.value == "**Heads ≥ 2**" for item in app.markdown)
    assert exports[-1]["event"] == COIN_EVENT

    app.checkbox(key="probability_track_event").uncheck().run()
    run(app)
    assert "event_operator" not in calls[-1][1]
    assert "event_value" not in calls[-1][1]
    assert "event" not in exports[-1]
    assert len(app.get("vega_lite_chart")) == 2


def test_coin_event_cutoff_validates_against_submitted_toss_count(probability_api):
    calls, exports = probability_api
    app = AppTest.from_file(str(PAGE), default_timeout=15).run()
    app.checkbox(key="probability_track_event").check().run()
    app.slider(key="probability_coin_tosses").set_value(2)
    app.number_input(key="probability_event_value_coin_heads").set_value(3)
    run(app)

    assert not calls
    assert not exports
    assert app.error[0].value == "Choose a heads cutoff from 0 to 2 for this run."
    assert app.session_state["probability_result"] is None

    app.selectbox(key="probability_experiment").select("Sum of two fair dice").run()
    dice_cutoff = app.number_input(key="probability_event_value_dice_sum")
    assert (dice_cutoff.min, dice_cutoff.max, dice_cutoff.value) == (2, 12, 7)


@pytest.mark.parametrize("failure,message", [
    ("offline", "Could not reach the probability service."),
    ("invalid", "Check the settings:"),
    ("malformed", "The probability service returned an unexpected response."),
])
def test_failed_rerun_clears_previous_report(probability_api, monkeypatch, failure, message):
    app = AppTest.from_file(str(PAGE), default_timeout=15).run()
    run(app)

    def fail(url, **kwargs):
        if failure == "offline":
            raise httpx.ConnectError("Connection refused")
        return httpx.Response(422 if failure == "invalid" else 200,
                              json={"detail": "invalid settings"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fail)
    run(app)
    assert app.error[0].value.startswith(message)
    assert app.session_state["probability_result"] is None
    assert not app.metric
    assert not app.get("download_button")
