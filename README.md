# Interview Copilot

AI-powered interview assistant with two modes:
- **Offline**: Pre-interview analysis (X profile vs resume inconsistencies)
- **Online**: Live interview transcript analysis (lie detection, flagging)

## Prerequisites

Install [uv](https://docs.astral.sh/uv/) (Python package manager):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install [bun](https://bun.sh/) (JS runtime):
```bash
curl -fsSL https://bun.sh/install | bash
```

## Setup

```bash
# Backend
cd backend
uv sync

# Frontend
cd ../frontend
bun install
```

## Run

Terminal 1 (backend):
```bash
cd backend
uv run uvicorn src.app:app --reload --port 8000
```

Terminal 2 (frontend):
```bash
cd frontend
bun start
```

Or run both:
```bash
./start.sh
```

## Structure

```
backend/          Python FastAPI
  src/
    app.py        API endpoints
    offline/      Pre-interview analysis
    online/       Live transcript processing
    common/       Shared utils (Grok API)

frontend/         Electron floating window
  src/
    index.js      Main process
    index.html    UI
    renderer.js   API calls
```
