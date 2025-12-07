#!/bin/bash
# Start backend and frontend

# Start backend in background
cd backend && uv run uvicorn src.app:app --reload --port 8000 &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 2

# Start frontend
cd ../frontend && bun start

# Cleanup on exit
kill $BACKEND_PID 2>/dev/null
