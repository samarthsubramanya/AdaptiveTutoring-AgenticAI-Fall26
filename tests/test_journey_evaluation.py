"""Guard the frozen, full-HTTP scenario protocol and its discriminating controls."""

import json
from evaluation.journeys.run import run


def test_interactive_policy_comparison(tmp_path):
    run(tmp_path)
    summary = json.loads((tmp_path / "summary.json").read_text())
    trials = [json.loads(line) for line in (tmp_path / "trials.jsonl").read_text().splitlines()]
    assert len(trials) == 36 and not any(t["error"] for t in trials)
    for row in summary["summary"]:
        if row["arm"] == "system":
            assert all(m["rate"] == 1 for m in row["metrics"].values())
        elif row["arm"] == "C0_fixed":
            assert row["metrics"]["prerequisite_selection"]["rate"] == 0
        elif row["arm"] == "C1_memoryless":
            assert row["metrics"]["persistent_checkpoint"]["rate"] == 0
    trace = (tmp_path / "http_trace.jsonl").read_text()
    assert '"mode": "prerequisite_review"' in trace
    assert '"mode": "unassisted_check"' in trace
    assert "simulated_two_hour_gap_and_server_reconstruction" in trace
