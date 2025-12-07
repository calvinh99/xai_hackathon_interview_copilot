#!/bin/bash
# Start backend and frontend

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Kill any existing process on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Start backend in background
(cd "$ROOT_DIR/backend" && uv run uvicorn src.app:app --reload --port 8000) &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 2

# Start frontend
cd "$ROOT_DIR/frontend" && bun start

# Cleanup on exit
kill $BACKEND_PID 2>/dev/null
