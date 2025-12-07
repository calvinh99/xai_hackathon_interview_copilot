#!/usr/bin/env bash

# Simple helper to serve the outputs directory and open viewer.html in a browser.

set -euo pipefail

# Always run from the script's directory so relative paths work.
cd "$(dirname "$0")"

PORT="${PORT:-8000}"

# Start a lightweight HTTP server.
python3 -m http.server "$PORT" &
SERVER_PID=$!

cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT

# Give the server a moment to start, then open the page.
sleep 1
if command -v open >/dev/null 2>&1; then
  open "http://localhost:${PORT}/viewer.html"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://localhost:${PORT}/viewer.html"
else
  printf 'Server running at http://localhost:%s/viewer.html\n' "$PORT"
fi

# Keep the server alive until the script is interrupted.
wait "$SERVER_PID"
