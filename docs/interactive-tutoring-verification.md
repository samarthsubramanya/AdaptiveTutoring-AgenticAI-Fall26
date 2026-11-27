# Verify the interactive tutoring implementation

Implemented and tested November 27, 2026 on `samarth/learning-studio`.

## What changed

The Learning journey is a connected tutoring workflow, rather than a page that
only calls a checker. The server owns the active problem and teaching mode.
It verifies attempts, gates hints, requires reflection before deeper help,
selects prerequisites after difficulty, returns through nested prerequisites,
and follows assisted success with a fresh unaided problem. Distinct item IDs are
consumed so a solved answer cannot be replayed as new independent evidence.
Revisions reject duplicated/stale actions. Unsupported/invalid answers remain
ungraded. Old evidence no longer suppresses support indefinitely.

Verified outcomes and observed hints are written to the existing STUDENT.md
learner record. Hints and assessment modes cannot be selected by a browser field.
Session reload restores the current journey; server restart retains the learner
record but intentionally does not restore the transient session. The next
session uses that evidence. A new subject can be chosen after closing a journey.
Sessions expire after one idle hour and have a 200-event/256-session limit.
A topic's finite bank can run out: choose another topic; there is no silent reuse
of a solved item as fresh assessment evidence.

MCP journey tools call the authoritative HTTP API process. They do not maintain
a second, conflicting in-memory session store in the MCP process. The Supervisor
can delegate `interactive_tutor`; its instructions prohibit bypassing hint gates
with other tools or inventing student attempts.

## Running services

- React: http://127.0.0.1:5173/#/journey
- API and interactive API docs: http://127.0.0.1:8000/docs
- MCP: http://127.0.0.1:8001/mcp (a tool endpoint, not an ordinary webpage)
- Preserved Streamlit interface: http://127.0.0.1:8501

From this checkout, `./start-studio.sh` starts React/API/MCP. The local ignored
`.venv` reuses the already-installed environment; no environment or credentials
are committed. For a clean checkout, create/install `.venv` as in the README.
To also start Streamlit against the running API:

```sh
API_BASE_URL=http://127.0.0.1:8000 .venv/bin/python -m streamlit run ui/app.py --server.address 127.0.0.1 --server.port 8501
```

The journey and its evaluation need no model key. Research and custom LLM
interpretation still require valid server-side credentials. No new claim is made
about provider availability. Keep these demo services local; they do not provide
public multi-user authentication. Use pseudonymous learner IDs.

## A concrete verification walk-through

1. Open **Learning journey**. In the sidebar, switch to a fresh lowercase learner
   ID such as `verify-nov27-a` (use a different suffix if already used).
2. Choose **Statistics**, then **Spread (variance, standard deviation)**. Begin.
   The first item asks for population variance of `1, 3, 5`.
3. Request a hint before an attempt. It must ask you to try first.
4. Submit `0`. Request a hint: conceptual help opens. Request another hint:
   you must enter a reflection of at least 15 characters before deeper help.
5. Submit `0` again. Click **Review prerequisite**. The tutor switches to the
   mean of `1, 3, 5`; answer `3`.
6. Continue. It returns to the original variance problem. Answer `8/3`.
   This is recorded as assisted, including help from the prerequisite.
7. Continue. A different item ID appears as **Fresh unaided check**, with zero
   hints. A correct first attempt counts as unaided; a corrected retry does not.
   The next translated triple also has variance `8/3`.
8. Reload the page: the active item, attempt count and restrictions remain.
   Open **Read your STUDENT.md** to inspect the verified evidence. Leave the
   journey and start again with the same ID to see an evidence-based next step.
9. For support fading, complete two distinct fresh problems correctly on their
   first attempt without hints. The same topic's support drops to one hint.
   The automated tests also verify a two-hour returning-learner recall decision
   with an explicitly simulated clock, and restoration of support for stale data.

The server, not these example answers or browser controls, determines grades.
Mathematics interpretation, general proof quality and student mastery are not
inferred from a correct final answer.

## Full interactive evaluation (addresses the Section 3 feedback)

Run:

```sh
.venv/bin/python -m evaluation.journeys.run --output evaluation/results/journeys_20261127
```

This sends HTTP turns through the production router/session engine using an
in-process ASGI transport and isolated on-disk learner records. No checker is
called by the driver. The browser has separately been exercised against the live
servers. Six scenarios each in **A_algebra_sessions** and
**B_statistics_sessions** cover assisted recovery, prerequisite return, graduated
hints/reflection, independent fading, resumption after assistance, and
invalid/stale actions. All three policies use the same scripts, answer labels,
checkers and bank. Thirty-six trials were run without scenario errors.

- `system`: the shipped adaptive tutor with cross-session memory.
- `C0_fixed`: fixed sequence and full support, no cross-session memory.
- `C1_memoryless`: adaptation within a session, no cross-session memory.

These controls are **policy ablations, not the earlier B1/B2 model baselines**.
See `evaluation/results/journeys_20261127/report.md`, `summary.json`, manifest,
per-trial results, and full HTTP transcripts. Source/manifest hashes and actual
execution time are recorded. Synthetic answer correction establishes workflow
behavior, not measured human learning gains. No LLM-generated teaching-quality
or original B1/B2 superiority claim is supported by this evaluation.

## Math skills in the vault

Open **this checkout's `vault/` directory** as the Obsidian vault. Start at
`skills/REGISTRY.md` → **mathematics** → `skills/math/DOMAIN.md`.
Algebra, inequalities, statistics, geometry, linear systems, probability,
equation solving, factoring, expansion, polynomial derivatives, solution
checking, and interactive tutoring now have linked operational notes. Runtime
math skill paths point to these same notes. Teaching links connect the hint,
retrieval, fading, and unaided-evidence methods. Probability remains a simulation
lab; it is not misrepresented as a scored journey dataset.

Historical `skills/*.md` files remain for compatibility; the registry's math
prompts are canonical in `vault/skills/math/`. Opening an older checkout's vault
will not show these new notes. Do not modify or commit `.obsidian` metadata.

## Tests and provenance

201 selected Python tests and three frontend tests passed, including full
journey HTTP scenarios, nested review/return, stale evidence, vault links, and
shared-state MCP tool routing. Production build and formatting checks passed.
Screenshots in the shared project's `pdocs/journey-verification-20261127/` show
the real browser workflow. Personal learner records are git-ignored.

The requested commit author dates are November 20 (vault), 23 (server journey),
25 (evaluation), and 27 (frontend/documentation). Committer timestamps and
benchmark execution dates remain the actual November 27 creation/run dates.
Nothing was pushed. Backdated author metadata does not mean these tests ran on
those earlier dates.

Use `./start-all.sh` from the repository root to launch React, API, MCP and Streamlit together. Ctrl+C stops the processes started by the launcher.
