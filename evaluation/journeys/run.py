"""Run multi-turn scenarios through production HTTP routes with isolated disk memory.

No LLM judge or direct checker calls. Controls are policy ablations, NOT the
earlier B1/B2 foundation-model baselines. Simulated time is explicit in traces.
"""

import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tutoring.journey import JourneyStore
from tutoring.journey_api import create_router
from tutoring.learners import LearnerStore


MANIFEST_PATH = Path(__file__).with_name("cases.json")


class Driver:
    def __init__(self, root, config, trace, arm, case):
        self.root, self.config, self.trace = root, config, trace
        self.arm, self.case = arm, case
        self.reopen()

    def reopen(self):
        if hasattr(self, "client"):
            self.client.close()
        app = FastAPI()
        app.include_router(create_router(JourneyStore(LearnerStore(self.root), **self.config)))
        self.client = TestClient(app)

    def request(self, method, path, body=None):
        start = time.perf_counter()
        response = self.client.request(method, path, json=body) if body is not None else self.client.request(method, path)
        data = response.json() if response.content else None
        self.trace.append({"arm": self.arm, "case": self.case, "method": method, "path": path,
                           "body": body, "http_status": response.status_code, "response": data,
                           "elapsed_seconds": time.perf_counter() - start})
        return response.status_code, data

    def start(self, skill, topic):
        code, data = self.request("POST", "/journeys/sessions", {"learner_id": "synthetic-learner", "skill": skill, "topic": topic})
        if code != 201:
            raise RuntimeError(f"Session start failed ({code}): {data}")
        return data

    def turn(self, state, action, **fields):
        code, data = self.request("POST", f"/journeys/sessions/{state['session_id']}/{action}",
                                  {"revision": state["revision"], **fields})
        if code != 200:
            raise RuntimeError(f"Turn failed ({code}): {data}")
        return data


def scenario(driver, skill, case, answers, clock):
    metrics = {}
    state = driver.start(skill, case["topic"])
    initial_id = state["item"]["id"]
    state = driver.turn(state, "hints")
    metrics["attempt_gate"] = state["hint"]["status"] == "attempt_first"
    invalid = driver.turn(state, "answers", answer="not a mathematical answer")
    metrics["ungraded_safety"] = invalid["attempts"] == 0 and invalid["profile"]["topics"] == []
    code, _ = driver.request("POST", f"/journeys/sessions/{state['session_id']}/answers",
                             {"revision": state["revision"], "answer": answers[initial_id]})
    metrics["revision_safety"] = code == 409
    state = invalid
    variant = case["scenario"]
    def correct(s):
        return driver.turn(s, "answers", answer=answers[s["item"]["id"]], confidence_before=4)

    if variant == "invalid_revision":
        state = correct(state)
        metrics["completion"] = state["solved"]
        return metrics
    if variant == "independent_fading":
        state = correct(state)
        state = driver.turn(state, "next")
        state = correct(state)
        metrics["support_fading"] = state["max_hints"] == 1
    else:
        state = driver.turn(state, "answers", answer="999")
        state = driver.turn(state, "hints")
        metrics["graduated_hint"] = state["hint"].get("level") == 1
        if variant == "hint_reflection":
            state = driver.turn(state, "hints")
            metrics["reflection_gate"] = state["hint"]["status"] == "reflection_required"
            state = driver.turn(state, "hints", reflection="I tried the first step but do not understand the next operation.")
            metrics["hint_escalation"] = state["hint"].get("level") == 2
        if variant == "prerequisite_return":
            state = driver.turn(state, "answers", answer="999")
            can_review = state["can_next"] and not state["solved"]
            metrics["prerequisite_selection"] = can_review
            if can_review:
                state = driver.turn(state, "next")
                metrics["prerequisite_selection"] = state["mode"] == "prerequisite_review" and state["item"]["topic"] != case["topic"]
                state = correct(state)
                state = driver.turn(state, "next")
                metrics["return_to_original"] = state["mode"] == "return" and state["item"]["id"] == initial_id
            else:
                metrics["return_to_original"] = False
        state = correct(state)
        metrics["assisted_not_independent"] = state["history"][-1]["learning"]["assisted"]
        if variant == "resume_after_assist":
            driver.reopen()
            state = driver.start(skill, case["topic"])
            metrics["persistent_checkpoint"] = state["mode"] == "unassisted_check" and state["item"]["id"] != initial_id and state["max_hints"] == 0
        else:
            state = driver.turn(state, "next")
        metrics["fresh_unaided_check"] = state["mode"] == "unassisted_check" and state["item"]["id"] != initial_id and state["max_hints"] == 0
        state = correct(state)
    metrics["completion"] = state["solved"]
    if variant != "resume_after_assist":
        previous_attempts = sum(t["attempts"] for t in state["profile"]["topics"])
        old_item = state["item"]["id"]
        clock[0] += timedelta(hours=2)
        driver.trace.append({"arm": driver.arm, "case": driver.case, "event": "simulated_two_hour_gap_and_server_reconstruction"})
        driver.reopen()
        state = driver.start(skill, case["topic"])
        metrics["return_session_retrieval"] = state["mode"] == "retrieve"
        metrics["disk_memory_retained"] = sum(t["attempts"] for t in state["profile"]["topics"]) == previous_attempts
        metrics["return_item_fresh"] = state["item"]["id"] != old_item
    return metrics


def run(output):
    manifest = json.loads(MANIFEST_PATH.read_text())
    rows, trace = [], []
    for dataset in manifest["datasets"]:
        for case in dataset["cases"]:
            for arm, config in manifest["arms"].items():
                with TemporaryDirectory(prefix="kernel-journey-eval-") as temp:
                    driver = Driver(Path(temp), config, trace, arm, case["id"])
                    clock = [datetime.now(timezone.utc)]
                    start = time.perf_counter()
                    try:
                        with patch("tutoring.learners._now", lambda: clock[0]):
                            metrics = scenario(driver, dataset["skill"], case, manifest["expected_answers"], clock)
                        error = None
                    except Exception as exc:
                        metrics, error = {"completion": False}, str(exc)
                    finally:
                        driver.client.close()
                    rows.append({"dataset": dataset["id"], "case": case["id"], "scenario": case["scenario"],
                                 "arm": arm, "metrics": metrics, "error": error,
                                 "elapsed_seconds": time.perf_counter() - start})
    summary = []
    for dataset in manifest["datasets"]:
        for arm in manifest["arms"]:
            group = [r for r in rows if r["dataset"] == dataset["id"] and r["arm"] == arm]
            buckets = defaultdict(list)
            for row in group:
                for metric, result in row["metrics"].items():
                    buckets[metric].append(result)
            summary.append({"dataset": dataset["id"], "arm": arm, "scenarios": len(group),
                            "errors": sum(r["error"] is not None for r in group),
                            "metrics": {k: {"passed": sum(v), "applicable": len(v), "rate": sum(v)/len(v)} for k,v in buckets.items()}})
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    except subprocess.SubprocessError:
        commit, dirty = "unknown", True
    output.mkdir(parents=True, exist_ok=True)
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    (output/"trials.jsonl").write_text(''.join(json.dumps(r)+"\n" for r in rows))
    (output/"http_trace.jsonl").write_text(''.join(json.dumps(t)+"\n" for t in trace))
    result = {"executed_at": datetime.now(timezone.utc).isoformat(), "source_commit": commit,
              "working_tree_dirty": dirty, "manifest_sha256": hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest(),
              "source_files_sha256": {str(p.relative_to(Path(__file__).resolve().parents[2])): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in [*sorted((Path(__file__).resolve().parents[2]/"tutoring").glob("*.py")), Path(__file__).resolve()]},
              "transport": "in-process ASGI HTTP via FastAPI TestClient; production router and session engine",
              "summary": summary}
    (output/"summary.json").write_text(json.dumps(result, indent=2)+"\n")
    lines = ["# Interactive tutoring workflow evaluation", "", result["transport"], "",
             "Two fixed synthetic datasets; six session scenarios each, three policies, 36 trials. Expected answers were authored before execution. Traces include all HTTP turns and explicit simulated two-hour gaps.", "",
             "C0_fixed = fixed sequence/full support without cross-session memory. C1_memoryless = adaptive within a session without cross-session memory. These are policy ablations, not earlier B1/B2 model baselines.", "",
             "| Dataset | Policy | Completed | Prerequisite/return | Fresh unaided check | Return-session recall | Memory retained |", "|---|---|---|---|---|---|---|"]
    for row in summary:
        def show(key):
            v=row["metrics"].get(key)
            return f"{v['passed']}/{v['applicable']}" if v else "N/A"
        lines.append(f"| {row['dataset']} | {row['arm']} | {show('completion')} | {show('return_to_original')} | {show('fresh_unaided_check')} | {show('return_session_retrieval')} | {show('disk_memory_retained')} |")
    lines += ["", "## What these results establish", "", "The tutor is exercised through complete request/response sessions: unaided attempt, feedback, hints and reflection, correction, prerequisite review, return, transfer to a fresh item, and reconstruction from persisted learner evidence. Baselines use the same bank, checker, HTTP contract and student script; their policy/memory switches differ.", "", "This measures deterministic workflow adherence and state persistence. Synthetic students follow authored scripts; their corrected answers do not demonstrate learning. It does not evaluate LLM-generated teaching quality, natural-language interpretation, human learning gains, or superiority to the previous B1/B2 models. Durations exclude browser rendering and external model calls. Small convenience scenarios are not a representative educational benchmark.", "", "Inspect per-metric applicable denominators in summary.json. Metrics are evaluated only in scenarios that exercise them; N/A is not zero. Failed trials retain their error and count as incomplete. Full raw HTTP transcripts are in http_trace.jsonl."]
    (output/"report.md").write_text('\n'.join(lines)+'\n')
    print(json.dumps({"trials": len(rows), "errors": [r for r in rows if r["error"]], "report": str(output/"report.md")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/journeys_20261127"))
    run(parser.parse_args().output)
