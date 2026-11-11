# KernelAI

KernelAI is an agentic runtime that turns a user request into independently scheduled tasks. An orchestrator admits requests, a dedicated supervisor delegates work to skill-equipped workers, and runtime events make execution visible through a web interface. An offline learning pipeline evaluates recorded executions and proposes policy candidates for manual release.

## Implemented features

- **Concurrent orchestration:** one supervisor per admitted request, configurable request/task concurrency, duplicate active request-ID rejection, and lifecycle cleanup.
- **Agent runtime:** asynchronous worker loops, hosted OpenAI-compatible LLM calls, a local Ollama caller, tool discovery, and skill-based tool access. The application launcher uses the hosted model path.
- **Tools and skills:** registered `web_search`, `text2sql`, and bank-scoped `algebra` skills; an MCP server exposes web search, PostgreSQL queries restricted to `SELECT`/`WITH`, guarded shell execution, algebra problem discovery, and SymPy answer verification. Coding/teaching skill documents are included in `vault/`; those vault documents are not registered production skills in the current registry.
- **Algebra tutor:** guided practice with eight predefined equations, graduated hints, retries, and prerequisite review; plus LLM-assisted custom questions with interpretation review, generated solutions/explanations/hints, and independent SymPy verification. Custom cases cover linear/quadratic equations, polynomial simplification, expansion, factoring, and derivatives.
- **Observability:** structured request/task/worker/tool events, argument-secret redaction, bounded trace previews, terminal and JSONL sinks, indexed in-memory event histories, and frontend lifecycle projections.
- **API and UI:** FastAPI request submission, status/activity/event endpoints, a Streamlit chat interface, a live observability dashboard, and a read-only offline learning dashboard.
- **Offline learning:** trace loading, deterministic metrics, semantic/batched evaluation, policy inspection, candidate creation, and a learning-cycle CLI. Candidate promotion is a separate manual release operation.
- **Existing verification coverage:** tracer/sink and tool-observability tests, runtime/API integration tests, concurrent-request tests, and historical single-request/50-task stress artifacts.

## Setup from scratch

### 1. Prerequisites

Use macOS or Linux, or a Bash-capable environment such as WSL on Windows. Install:

- Git.
- **Python 3.11 or newer**, including `venv` and `pip`. The setup below was verified with Python 3.14.10 on macOS; make sure `python3 --version` reports a supported version.
- Bash and `curl`, used by `start.sh`.
- Access to an OpenAI-compatible LLM endpoint and its API key for general agent/chat, learning, and LLM-assisted algebra requests. Configure all three `ASU_LLM_*` values in `.env`. The supplied template targets the ASU gateway.
- A running PostgreSQL database and connection credentials **if using `text2sql`**. Web-only requests do not require a database. There is no bundled database server, schema migration, or seed dataset.

The launcher uses ports **8000** (API), **8001** (MCP), and **8501** (UI); keep them available.

### 2. Clone the repository

```bash
git clone https://github.com/samarthsubramanya/AdaptiveTutoring-AgenticAI-Fall26.git
cd AdaptiveTutoring-AgenticAI-Fall26
```

For a private repository, authenticate to GitHub first. Run the remaining commands from this repository root.

### 3. Create a virtual environment and install dependencies

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
```

If your default `python3` is older than 3.11, substitute a supported interpreter, for example `python3.14 -m venv .venv`. The launcher expects the environment to be named `.venv` in the repository root and activates it automatically.

### 4. Configure the environment

```bash
cp .env.example .env
mkdir -p ../kernelai-workspace
```

Edit `.env` with your actual values. The following shows the relevant settings; replace the key and absolute workspace path. Add `DATABASE_URL` when using SQL, because it is required by the SQL tool but is currently absent from `.env.example`.

```dotenv
ASU_LLM_API_KEY=your-api-key
ASU_LLM_BASE_URL=https://openai.rc.asu.edu/v1
ASU_LLM_MODEL=glm-5-3-flash
MCP_SERVER_URL=http://localhost:8001/mcp
KERNELAI_AGENT=generic
SHELL_WORKSPACE=/absolute/path/to/kernelai-workspace

# Required only for database-backed requests:
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
```

| Setting | Purpose |
|---|---|
| `ASU_LLM_API_KEY` | Credential for the hosted model endpoint. |
| `ASU_LLM_BASE_URL` | OpenAI-compatible API base URL; adjust for your provider. |
| `ASU_LLM_MODEL` | Tool-capable model available to your account. |
| `MCP_SERVER_URL` | MCP endpoint used by task workers. |
| `KERNELAI_AGENT` | Keep `generic`; it is the implemented agent backend. |
| `SHELL_WORKSPACE` | Existing directory used as the shell tool's workspace. |
| `DATABASE_URL` | PostgreSQL connection string used by `asyncpg`; provision your own database/schema. |

The backend loads `.env` automatically. Keep credentials in the ignored `.env` file. The template also contains `KERNELAI_VAULT_PATH`, but the current runtime does not read it; changing it does not register the vault's coding or teaching skills. The startup script sets `API_BASE_URL` for the UI automatically.

For database requests, use tables that actually exist in your database. Prompts and integration tests mentioning `customers`, `products`, or `orders` assume those tables have been provisioned externally.

### 5. Start KernelAI

```bash
STREAMLIT_SERVER_HEADLESS=true bash start.sh
```

`STREAMLIT_SERVER_HEADLESS=true` skips Streamlit's first-run email prompt and automatic browser opening; you still open the UI in your browser. This avoids an interactive prompt blocking the launcher's UI readiness check on a new installation. After Streamlit has already been initialized, `bash start.sh` also works without that setting.

The script activates `.venv`, starts MCP, starts the API, waits for the API and UI HTTP checks, and prints the service URLs. Keep this terminal open. Press **Ctrl+C** to stop all three services.

| Service | Address |
|---|---|
| Chat UI and dashboard pages | <http://127.0.0.1:8501> |
| API | <http://127.0.0.1:8000> |
| Interactive API documentation | <http://127.0.0.1:8000/docs> |
| MCP endpoint | <http://localhost:8001/mcp> |

Use the Streamlit page selector to open **Observability**, **Offline Learning**, or **Algebra Tutor**. The MCP endpoint is a protocol endpoint, not a browser dashboard. The MCP process binds to `0.0.0.0:8001` in the current implementation; the API and UI launcher addresses are loopback-only.

### 6. Check the installation

In a second terminal, return to the repository root and activate the environment:

```bash
source .venv/bin/activate
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8501/_stcore/health
python -m pytest -q tests/test_observability.py tests/test_tool_observability.py
```

The API health response is `{"status":"ok"}`. The UI health response is `ok`. The selected local tests exercise tracing and scripted tool/LLM behavior; they do not require live LLM or database calls. Health checks establish service availability, not that your external credentials or database are working.

To try a real request, open the chat UI and ask, for example, “Search the web for recent NVIDIA GPU news and summarize it.” Alternatively:

```bash
curl --fail -X POST http://127.0.0.1:8000/requests \
  -H 'Content-Type: application/json' \
  -d '{"query":"Search the web for recent NVIDIA GPU news and summarize it."}'
```

Submission returns a `request_id`. Replace `YOUR_REQUEST_ID` below to follow execution:

```bash
curl --fail http://127.0.0.1:8000/requests/YOUR_REQUEST_ID
curl --fail http://127.0.0.1:8000/requests/YOUR_REQUEST_ID/activity
curl --fail http://127.0.0.1:8000/requests/YOUR_REQUEST_ID/events
```

Actual execution requires valid model credentials, access to the configured endpoint, and internet access for web search. SQL requests additionally require the configured PostgreSQL database.

### Setup verification

Verified on November 6, 2026 with macOS and Python 3.14.10: HTTPS cloning of the default `main` branch, a fresh `.venv` dependency install, `pip check`, and both CLI help commands below. The current selected suite has **105 passing tests**, including guided and LLM-assisted Streamlit flows, wrong model answers, incomplete roots, malformed model responses, bounded schema repair, and non-JSON API responses. Live model calls produced a quadratic solution and a factored expression that independently passed SymPy checks, and a model-generated hint. Earlier live API/UI health checks, the guided tutoring flow, and MCP bank-answer checks also passed. Restart MCP to load the new `verify_symbolic_answer` tool alongside the existing tools.

The original launcher check used an isolated copy with API/UI ports 18000/18501 because an existing process occupied port 8000. The guided algebra smoke check used temporary services on API/UI ports 18000/18501 and MCP port 18001, then shut those services down. Live web searches, PostgreSQL queries, and a full learning cycle were not exercised.

## Try the algebra tutor

After installing the updated `requirements.txt`, start the services as above and open **Algebra Tutor** in the Streamlit page selector. This is a separate practice flow from the general chat page.

1. Keep the starting problem `distribution-01` selected and click **Start new session**. The equation is `3(x - 2) = 12`.
2. Enter `x=2` and click **Check answer**. Expect **SymPy verification: incorrect**; the problem stays open.
3. Click **Give me a hint**. The first hint suggests dividing both sides by the factor outside the parentheses.
4. Enter `x=6`. Expect **SymPy verification: correct** and a next-problem button.
5. Click **Next problem**. A fresh distribution equation appears. Solve it without a hint to record independent success.
6. To demonstrate remediation, start a new default session, submit `2` and then `4`, and click **Practice prerequisite**. Solve `3x - 6 = 12` with `6`, then click **Next problem** to return to the original equation.

Use **Verification evidence** for the original equation, normalized answer, real-number domain, SymPy version, and substitution residual. **Session history** shows attempts, hints, transitions, and independent versus assisted successes. Invalid input and verifier failures remain ungraded and do not unlock advancement.

Guided-practice answers are numeric literals, decimals, or fractions, optionally prefixed with `x=`: `6`, `x=6`, `12/2`, `1.5`, and `3/2`. General expressions and multiple solutions use the separate custom-problem mode below. No user input is passed to Python `eval` or SymPy's expression parser.

**Guided practice** uses the predefined problem bank and rule-based feedback. **LLM-assisted problems** handles your own questions as described below. Verification covers final mathematical answers, not every reasoning step or mastery. Sessions/cases are process-local, expire after one idle hour, and disappear on API restart. Run one API worker for this demo. There is no authentication or persistent student profile; treat IDs as private and use it locally.

### LLM-assisted custom problems

1. Configure `ASU_LLM_API_KEY`, `ASU_LLM_BASE_URL`, and `ASU_LLM_MODEL` in `.env`, then restart the API so it loads the configuration.
2. Open **Algebra Tutor** and select **LLM-assisted problems**.
3. Choose an example or enter your own question, then click **Ask math tutor**.
4. Review the operation, equation/expression, variable, real-number domain, and interpretation against your original question. Tick **This interpretation matches my question** only if it does.
5. Click **Verify model answer**, or enter a student answer and click **Check my answer**. The backend uses its stored interpretation and computes its own SymPy result; it does not accept the model's answer as an answer key.
6. Use **Ask for a hint** for a generated next-step hint, or expand the LLM explanation. Explanation steps are not individually verified.

Examples to try:

| Question | Answer to check |
|---|---|
| Solve `x^2 - 5*x + 6 = 0`. | `2,3` (both roots; `2` alone is incomplete) |
| Solve `x^2 - 2 = 0`. | `-sqrt(2),sqrt(2)` |
| Solve `x^2 - x + 6 = 0` over the reals. | `no real solutions` |
| Factor `x^2 - 9`. | `(x-3)*(x+3)` |
| Expand `(x+2)*(x-3)`. | `x^2-x-6` |
| Simplify `3*x + 2*x - 4`. | `5*x-4` |
| Differentiate `x^3 - 2*x`. | `3*x^2-2` |
| A number doubled and increased by 3 equals 17. | Review the translation `2*x+3=17`; then check `7`. |

The checker supports one variable (`x`, `y`, or `t`), rational-coefficient polynomials of degree at most 8, and linear/quadratic solving over the reals. Use explicit `*`, integer powers `0..6`, and numeric constant denominators. For equations, provide every real root; `no real solutions` is accepted for an empty real solution set. Arbitrary code/functions, variable denominators, systems, inequalities, trigonometry, geometry, and proofs are outside scope. Inputs are parsed with an allowlisted AST and never executed as Python code.

A correct symbolic result proves the checked statement for the **reviewed interpretation**; it does not establish that an LLM correctly translated a word problem. Unsupported, invalid, or inconclusive checks remain ungraded. Equivalent expressions in the wrong requested factor/expanded form receive a `needs_form` result. Incomplete or malformed model responses receive at most one format-repair attempt within an overall timeout; missing answers are never filled in as if the model supplied them. Model failures return an actionable error rather than a fabricated solution.

The agent runtime can discover `algebra_problems`, `verify_algebra_answer`, and `verify_symbolic_answer` through MCP using the `algebra` skill. General-chat prose does not update a tutoring session or serve as an authoritative grade.

### Test the demo automatically

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q tests/test_algebra.py tests/test_algebra_api.py tests/test_custom_math.py tests/test_observability.py tests/test_tool_observability.py
```

These automated tests use mocked model replies and make no live provider/database/web-search calls. They cover bank and custom answers, incomplete root sets, wrong model proposals, malformed model output, missing credentials, interpretation confirmation, unsupported expressions, session isolation, stale submissions, the non-JSON response regression, and both Streamlit flows.

### Try the tutoring API

With the API running, create a session:

```bash
curl --fail -X POST http://127.0.0.1:8000/tutoring/sessions \
  -H 'Content-Type: application/json' -d '{}'
```

Copy its `session_id` into `YOUR_SESSION_ID` below. A new session has revision `0`:

```bash
curl --fail -X POST http://127.0.0.1:8000/tutoring/sessions/YOUR_SESSION_ID/answers \
  -H 'Content-Type: application/json' \
  -d '{"problem_id":"distribution-01","answer":"2","revision":0}'
```

Use the returned `revision` for the next action. The API rejects stale revisions or a different problem ID with HTTP 409, so retries cannot silently grade the wrong problem. The `/docs` page lists all `/tutoring` routes, including hints, next problem, session retrieval, and deletion. Client-supplied grade fields are rejected.

## Offline learning

Application execution appends production events to `learning/data/traces/production/runtime.jsonl`. The learning dashboard reads trace volume, configuration, evaluation history, policies, candidates, and releases.

With `.venv` active, inspect and run the learning CLI:

```bash
python -m learning.run --help
python -m learning.run --verbose
```

This uses the configured LLM to evaluate historical traces and may create candidate artifacts. It does not release candidates into production. Learning settings are in `learning/config/learning.yaml`; manual promotion is implemented by `learning/release.py`.

An optional workload generator can submit requests to the running API:

```bash
python generate_learning_traces.py --help
python generate_learning_traces.py --count 10 --concurrency 2
```

The built-in workload includes database questions as well as web research. Configure both services before using it; it makes real model/tool calls and appends new production traces.

## Troubleshooting

| Symptom | Check |
|---|---|
| `.venv` not found | Create it in the repository root before starting the launcher. |
| Missing packages or incompatible Python | Activate `.venv`, check `python --version`, reinstall `requirements.txt`, and run `python -m pip check`. |
| Missing `ASU_LLM_*` variables or model authentication errors | Fill all three settings in `.env` and confirm the endpoint/model are available to your account. |
| Tool connection fails | Confirm MCP is running and `MCP_SERVER_URL` ends in `/mcp` on port 8001. |
| `DATABASE_URL` missing or SQL relation does not exist | Add the connection string and provision the requested tables in PostgreSQL. |
| Shell workspace error | Replace `workspace_path` from the template with the absolute path of an existing directory. |
| Address already in use | Stop the process occupying 8000, 8001, or 8501, then restart the launcher. |
| UI startup stalls at an email prompt | Use `STREAMLIT_SERVER_HEADLESS=true bash start.sh`. |

Most other tests under `tests/` are live integration tests. They may require hosted model credentials, Ollama for local-model cases, MCP, internet access, specific database tables, or machine-specific workspaces. Some rewrite tracked trace/result artifacts. Use the selected local tests above for a first check rather than treating a bare `pytest` run as an offline smoke test.

## Project layout

| Path | Responsibility |
|---|---|
| `orchestrator/` | Request admission and lifecycle coordination. |
| `supervisor/`, `tasks/`, `worker/` | Delegation, task execution, model/tool clients, and agent runtime. |
| `mcp_server/`, `skills/`, `vault/` | Tools, production skill registry, and additional skill documents. |
| `observability/` | Events, sanitization, sinks, and frontend projections. |
| `tutoring/` | Trusted algebra bank, exact verification, in-memory sessions, and tutoring API routes. |
| `api/`, `ui/`, `.streamlit/`, `start.sh` | HTTP API, chat/dashboard pages, theme, and service launcher. |
| `learning/`, `generate_learning_traces.py` | Offline evaluation, candidates/releases, and workload generation. |
| `tests/`, `docs/` | Tests, historical artifacts, sample prompts, and runtime contract notes. |

## Inequalities and descriptive statistics

The registered `inequalities` and `statistics` skills expose deterministic tools
through MCP, with credential-free HTTP checks for the learning workspace:

- `POST /studio/inequalities/check`: `expression`, `relation` (`<`, `<=`, `>`,
  `>=`), `rhs`, `variable`, and `answer`. Supports real constant, linear, and
  quadratic polynomials. Use complete interval notation such as `(-inf, 4]`,
  unions separated by ` U `, isolated points `{0}`, `empty`, or `R`.
- `POST /studio/statistics/check`: rational `values` (1–100 strings), `metric`
  (`mean`, `median`, `range`, `variance`, `standard_deviation`), `convention`
  (`population` or `sample`), and `answer`. Sample variance uses `n - 1` and
  needs at least two observations. Checks accept error up to
  `max(1e-8, abs(expected) * 1e-6)`; use fractions or numeric square roots for
  exact answers. Modes include all ties; no repeats means no mode.
- `GET /studio/skills`: the student-facing practice catalogue.

Both skills reuse the allowlisted mathematical parser; student expressions are
never executed. Unsupported expressions are ungraded. Verification establishes
numeric answers or complete solution sets, not student mastery or proof quality.
Streamlit and its existing session endpoints remain available.
