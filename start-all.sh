#!/usr/bin/env bash
# Local demo: React, API, MCP, and the preserved Streamlit interface.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
PYTHON_BIN="${KERNEL_PYTHON:-$ROOT_DIR/.venv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "Create .venv and install requirements.txt, or set KERNEL_PYTHON."
    exit 1
fi
STREAMLIT_PORT="${KERNEL_STREAMLIT_PORT:-8501}"
export API_BASE_URL="http://127.0.0.1:${KERNEL_API_PORT:-8000}"
export VITE_STREAMLIT_URL="http://127.0.0.1:$STREAMLIT_PORT"
PIDS=()
cleanup() {
    for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
    wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM
./start-studio.sh &
PIDS+=("$!")
"$PYTHON_BIN" -m streamlit run ui/app.py --server.address 127.0.0.1 --server.port "$STREAMLIT_PORT" --server.headless true &
PIDS+=("$!")
echo "Streamlit: $VITE_STREAMLIT_URL"
while true; do
    for pid in "${PIDS[@]}"; do
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "A demo service stopped. Check the output above."
            exit 1
        fi
    done
    sleep 1
done
