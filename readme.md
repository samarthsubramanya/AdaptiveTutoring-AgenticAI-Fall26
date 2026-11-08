# KernelAI

KernelAI is an agentic runtime that turns a user request into independently scheduled tasks. An orchestrator admits requests, a dedicated supervisor delegates work to skill-equipped workers, and runtime events make execution visible through a web interface. An offline learning pipeline evaluates recorded executions and proposes policy candidates for manual release.

## Implemented features

- **Concurrent orchestration:** one supervisor per admitted request, configurable request/task concurrency, duplicate active request-ID rejection, and lifecycle cleanup.
- **Agent runtime:** asynchronous worker loops, hosted OpenAI-compatible LLM calls, a local Ollama caller, tool discovery, and skill-based tool access. The application launcher uses the hosted model path.
- **Tools and skills:** registered `web_search` and `text2sql` skills; an MCP server exposes web search, PostgreSQL queries restricted to `SELECT`/`WITH`, and a shell tool with workspace, timeout, output, and environment restrictions. Coding/teaching skill documents are included in `vault/`; they are not registered production skills in the current registry.
- **Observability:** structured request/task/worker/tool events, argument-secret redaction, bounded trace previews, terminal and JSONL sinks, indexed in-memory event histories, and frontend lifecycle projections.
- **API and UI:** FastAPI request submission, status/activity/event endpoints, a Streamlit chat interface, a live observability dashboard, and a read-only offline learning dashboard.
- **Offline learning:** trace loading, deterministic metrics, semantic/batched evaluation, policy inspection, candidate creation, and a learning-cycle CLI. Candidate promotion is a separate manual release operation.
- **Existing verification coverage:** tracer/sink and tool-observability tests, runtime/API integration tests, concurrent-request tests, and historical single-request/50-task stress artifacts.

## Setup from scratch

### 1. Prerequisites

Use macOS or Linux, or a Bash-capable environment such as WSL on Windows. Install:

- Git.
- **Python 3.11 to 3.14**, including `venv` and `pip`. The setup below was verified with Python 3.14.10 on macOS; on Python 3.15 the `pyarrow` dependency failed to build. Make sure `python3 --version` reports a supported version.
- Bash and `curl`, used by `start.sh`.
- Access to an OpenAI-compatible LLM endpoint and its API key. The supplied template targets the ASU gateway.
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

If your default `python3` is outside that range, substitute a supported interpreter, for example `python3.14 -m venv .venv`. The launcher expects the environment to be named `.venv` in the repository root and activates it automatically.

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

The backend loads `.env` automatically. Keep credentials in the ignored `.env` file. The template also contains `KERNELAI_VAULT_PATH`, but the current runtime does not read it. `skills/registry.py` registers the `web_search` and `text2sql` prompts from fixed paths under `vault/skills/`; changing the variable does not register the vault's coding or teaching skills. The startup script sets `API_BASE_URL` for the UI automatically.

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

Use the Streamlit page selector to open **Observability** or **Offline Learning**. The MCP endpoint is a protocol endpoint, not a browser dashboard. The MCP process binds to `0.0.0.0:8001` in the current implementation; the API and UI launcher addresses are loopback-only.

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

Verified on November 6, 2026 with macOS and Python 3.14.10: HTTPS cloning of the default `main` branch, a fresh `.venv` dependency install, `pip check`, all **11 selected local tests**, and both CLI help commands below. The launcher reached readiness, API/UI health and dashboard HTTP checks passed, MCP discovered `web_search`, `sql_executor`, and `shell`, and Ctrl+C shut the services down.

Startup checks used an isolated copy with API/UI ports 18000/18501 because an existing process occupied port 8000; MCP used 8001. The checked launcher and application files match the remote default branch. Credentialed LLM requests, live web searches, PostgreSQL queries, and a full learning cycle were not exercised.

Re-verified on November 8, 2026 with macOS and Python 3.14.10 from a fresh clone: dependency install, `pip check`, the 11 selected local tests, launcher startup, API/UI health checks, loading of both registered skill prompts from `vault/skills/`, and one credentialed web-search request that completed through the Supervisor and `web_search` skill. PostgreSQL queries and a full learning cycle were not exercised.

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
| `mcp_server/`, `skills/`, `vault/` | Tools, the skill registry (`skills/registry.py`), and skill documents, including the registered `web_search` and `text2sql` prompts. |
| `observability/` | Events, sanitization, sinks, and frontend projections. |
| `api/`, `ui/`, `.streamlit/`, `start.sh` | HTTP API, chat/dashboard pages, theme, and service launcher. |
| `learning/`, `generate_learning_traces.py` | Offline evaluation, candidates/releases, and workload generation. |
| `tests/`, `docs/` | Tests, historical artifacts, sample prompts, and runtime contract notes. |
