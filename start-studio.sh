#!/usr/bin/env bash
# Run the independent React workspace alongside the existing Streamlit launcher.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
PYTHON_BIN="${KERNEL_PYTHON:-$ROOT_DIR/.venv/bin/python}"
API_PORT="${KERNEL_API_PORT:-8000}"
MCP_PORT="${KERNEL_MCP_PORT:-8001}"
UI_PORT="${KERNEL_UI_PORT:-5173}"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "Create .venv and install requirements.txt, or set KERNEL_PYTHON to your environment's Python."
    exit 1
fi
if [ ! -d frontend/node_modules ]; then
    echo "Install the frontend first: cd frontend && npm ci"
    exit 1
fi
PIDS=()
cleanup() {
    for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
    wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM
export MCP_SERVER_URL="http://127.0.0.1:$MCP_PORT/mcp"
export KERNEL_API_URL="http://127.0.0.1:$API_PORT"
"$PYTHON_BIN" -c 'import sys; from mcp_server.server import mcp; mcp.run(transport="streamable-http", host="127.0.0.1", port=int(sys.argv[1]))' "$MCP_PORT" &
PIDS+=("$!")
"$PYTHON_BIN" -m uvicorn api.app:app --host 127.0.0.1 --port "$API_PORT" &
PIDS+=("$!")
(cd "$ROOT_DIR/frontend"; exec node node_modules/vite/bin/vite.js --host 127.0.0.1 --port "$UI_PORT") &
PIDS+=("$!")
echo "Learning studio: http://127.0.0.1:$UI_PORT"
echo "The existing ./start.sh launcher and ui/ remain available for Streamlit."
while true; do
    for pid in "${PIDS[@]}"; do
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "A service stopped. Check the output above; try unused ports if another app is running."
            exit 1
        fi
    done
    sleep 1
done
