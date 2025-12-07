"""Interview Copilot Backend API."""
import json
import logging
import queue
import tempfile
import threading
import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from src.offline import run_full_analysis

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="Interview Copilot")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# SSE progress queues per session
_progress_queues: dict[str, queue.Queue] = {}


class _ProgressHandler(logging.Handler):
    """Log handler that sends logs to SSE queue."""
    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id

    def emit(self, record):
        if self.session_id in _progress_queues:
            _progress_queues[self.session_id].put({"type": "log", "message": self.format(record)})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/offline/analyze")
async def analyze_candidate(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    x_handle: str = Form(...),
    top_n: int = Form(10),
):
    """Analyze candidate with streaming progress via SSE."""
    session_id = str(uuid.uuid4())

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await resume.read())
        tmp_path = tmp.name

    _progress_queues[session_id] = queue.Queue()
    handler = _ProgressHandler(session_id)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger("src.offline.pipeline").addHandler(handler)

    def generate():
        try:
            yield f"data: {json.dumps({'type': 'start', 'session_id': session_id})}\n\n"
            result_holder = {}

            def run():
                try:
                    result_holder["results"] = run_full_analysis(tmp_path, job_description, x_handle, top_n)
                except Exception as e:
                    result_holder["error"] = str(e)
                finally:
                    _progress_queues[session_id].put({"type": "done"})

            thread = threading.Thread(target=run)
            thread.start()

            while True:
                try:
                    msg = _progress_queues[session_id].get(timeout=1)
                    if msg["type"] == "done":
                        break
                    yield f"data: {json.dumps(msg)}\n\n"
                except queue.Empty:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

            thread.join(timeout=5)

            if "error" in result_holder:
                yield f"data: {json.dumps({'type': 'error', 'message': result_holder['error']})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'results', 'skills': [r.to_dict() for r in result_holder.get('results', [])]})}\n\n"
        finally:
            Path(tmp_path).unlink(missing_ok=True)
            logging.getLogger("src.offline.pipeline").removeHandler(handler)
            _progress_queues.pop(session_id, None)

    return StreamingResponse(generate(), media_type="text/event-stream")


# Online endpoints
@app.post("/online/process")
def process_transcript(transcript: str, session_id: str):
    """Process live transcript, detect inconsistencies."""
    # TODO: implement
    return {"flags": [], "suggestions": []}
