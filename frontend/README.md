# Kernel learning studio

A separate React + TypeScript workspace for mathematics practice and agent research.
The existing `ui/` Streamlit app and `start.sh` launcher are preserved.

## Start locally

Use Node 22.12+ (or Node 24/26) and the Python environment described in the root
README. From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm --prefix frontend ci
./start-studio.sh
```

Open <http://127.0.0.1:5173>. The launcher starts the API on 8000 and MCP on 8001;
Ctrl+C stops only the processes it started. If those ports are occupied, set
`KERNEL_API_PORT`, `KERNEL_MCP_PORT`, and `KERNEL_UI_PORT`, or run the components
separately. To reuse an installed Python environment, set `KERNEL_PYTHON`.

Deterministic practice needs no model key. For research, create the root `.env`
from `.env.example` and set the model credentials. No secret belongs in a `VITE_`
variable, browser storage, or committed file. Restart the Python API after editing
credentials. Research uses the existing Supervisor/TaskExecutor/MCP pipeline.

For separate terminals:

```sh
# Repository root, terminal 1
.venv/bin/python -m mcp_server.server
# Repository root, terminal 2
.venv/bin/python -m uvicorn api.app:app --host 127.0.0.1 --port 8000
# Repository root, terminal 3
npm --prefix frontend run dev
```

The Vite proxy forwards `/api/*` to the Python API and strips `/api`. This keeps
development requests same-origin without broadening API CORS. To customize the
target, set `KERNEL_API_URL` in the shell or `frontend/.env`. To run Streamlit
alongside the studio, reuse the running API/MCP and start only Streamlit:

```sh
API_BASE_URL=http://127.0.0.1:8000 .venv/bin/python -m streamlit run ui/app.py
```

## Features and boundaries

- Overview and server-backed practice catalogue; accurate browser-local counts.
- Guided algebra: original sessions, hints, revision checks, and next problems.
- Inequalities: edit linear/quadratic problems, check complete intervals, and view
  the verified number line. No solution is drawn before a correct attempt.
- Statistics: explicit data, measure and population/sample convention, chart
  preview, and independently checked answers. The first 24 values are plotted.
- Research: async submission, serialized polling, bounded backoff, pause/resume,
  reconnect on reload, task activity, Markdown/GFM tables, and raw output access.
- Journal: up to 100 locally stored checks, export, and clear with undo. This is
  browser history, not a persistent learner profile or mastery measure.
- Responsive desktop/sidebar and mobile/drawer layouts, labelled inputs, live
  feedback, keyboard focus, and reduced-motion support.

Switching subjects aborts stale grading responses. Leaving the research page
keeps its request tracked at app level; closing the app stops browser polling but
does not cancel server work. Polling pauses after 15 minutes and can be resumed.
Neither API health nor the “ready” badge establishes model/provider availability.
The API's existing in-memory state disappears on restart.

## Build and validation

```sh
npm --prefix frontend run build
npm --prefix frontend test
python -m pytest -q tests/test_studio.py tests/test_algebra.py tests/test_algebra_api.py tests/test_custom_math.py
```

The build creates `frontend/dist/`. In deployment, serve these static files with
SPA fallback and reverse-proxy `/api` to the Python server. Vite's development
proxy is not part of the static build; `vite preview` alone does not provide the
API proxy. The application is intended for a local course demo: adding public
authentication, persistent sessions, and deployment hardening is separate work.

`components/` holds shared visuals; `pages/` holds screens; `hooks/` owns research
polling; `lib/` holds contracts, networking, storage and pure helpers. The backend
retains authoritative grading. Raw model content is never rendered as HTML;
reasoning/control fragments are filtered in the reading view and retained in the
explicit raw-output view. Fonts fall back to installed system fonts offline.
