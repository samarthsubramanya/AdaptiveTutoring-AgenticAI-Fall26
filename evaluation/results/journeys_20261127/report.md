# Interactive tutoring workflow evaluation

in-process ASGI HTTP via FastAPI TestClient; production router and session engine

Two fixed synthetic datasets; six session scenarios each, three policies, 36 trials. Expected answers were authored before execution. Traces include all HTTP turns and explicit simulated two-hour gaps.

C0_fixed = fixed sequence/full support without cross-session memory. C1_memoryless = adaptive within a session without cross-session memory. These are policy ablations, not earlier B1/B2 model baselines.

| Dataset | Policy | Completed | Prerequisite/return | Fresh unaided check | Return-session recall | Memory retained |
|---|---|---|---|---|---|---|
| A_algebra_sessions | system | 6/6 | 1/1 | 4/4 | 4/4 | 4/4 |
| A_algebra_sessions | C0_fixed | 6/6 | 0/1 | 0/4 | 0/4 | 0/4 |
| A_algebra_sessions | C1_memoryless | 6/6 | 1/1 | 3/4 | 0/4 | 0/4 |
| B_statistics_sessions | system | 6/6 | 1/1 | 4/4 | 4/4 | 4/4 |
| B_statistics_sessions | C0_fixed | 6/6 | 0/1 | 0/4 | 0/4 | 0/4 |
| B_statistics_sessions | C1_memoryless | 6/6 | 1/1 | 3/4 | 0/4 | 0/4 |

## What these results establish

The tutor is exercised through complete request/response sessions: unaided attempt, feedback, hints and reflection, correction, prerequisite review, return, transfer to a fresh item, and reconstruction from persisted learner evidence. Baselines use the same bank, checker, HTTP contract and student script; their policy/memory switches differ.

This measures deterministic workflow adherence and state persistence. Synthetic students follow authored scripts; their corrected answers do not demonstrate learning. It does not evaluate LLM-generated teaching quality, natural-language interpretation, human learning gains, or superiority to the previous B1/B2 models. Durations exclude browser rendering and external model calls. Small convenience scenarios are not a representative educational benchmark.

Inspect per-metric applicable denominators in summary.json. Metrics are evaluated only in scenarios that exercise them; N/A is not zero. Failed trials retain their error and count as incomplete. Full raw HTTP transcripts are in http_trace.jsonl.
