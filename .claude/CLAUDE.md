# Interview Copilot

AI-powered interview assistant to catch cheaters/liars.

## Modes

- **Offline**: Pre-interview analysis. Compare candidate's X profile vs resume, flag inconsistencies, assess technical competence from tweets (real knowledge vs posers).
- **Online**: Live interview. Real-time transcript analysis, flag contradictions, lie detection, extensible modules (AI code check, video analysis, etc).

## Tech Stack

| Layer | Tech | Package Manager |
|-------|------|-----------------|
| Backend | Python 3.11+, FastAPI | `uv` |
| Frontend | Electron (floating window) | `bun` |
| LLM | Grok/xAI API | - |

## Project Structure

```
backend/
  src/
    app.py           # FastAPI entry, API endpoints
    offline/         # X profile, resume parsing, inconsistency analysis
    online/          # Live transcript processing, lie detection
    common/
      llm.py         # Grok API client

frontend/
  src/
    index.js         # Electron main process (floating window config)
    index.html       # UI with Offline/Online tabs
    renderer.js      # Frontend logic, calls backend API

data/                # Sample test data (X profile, resume, job desc)
```

## Commands

```bash
# Backend
cd backend && uv sync
uv run uvicorn src.app:app --reload --port 8000

# Frontend
cd frontend && bun install
bun start

# Both
./start.sh
```

## API

- `GET /health` - health check
- `POST /offline/analyze` - analyze candidate (x_profile_url, resume_text, job_description)
- `POST /online/process` - process live transcript (transcript, session_id)

## Key Design Decisions

- Electron for floating always-on-top window (adapted from cheating-daddy repo)
- FastAPI backend for simplicity and async support
- Minimal dependencies, hackathon-style code
- Frontend communicates with backend via HTTP (localhost:8000)
