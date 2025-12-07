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
from pydantic import BaseModel
import sounddevice as sd

from src.offline import run_full_analysis
from src.online import strategies
from src.online.streaming_stt import SystemAudioSTT, DualStreamingSTT

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


# =============================================================================
# Online Mode - Live Interview
# =============================================================================

class OnlineStartRequest(BaseModel):
    interviewer_device_id: int
    candidate_device_id: int

# Global state for online session
_online_stop_event: threading.Event | None = None
_online_events_queue: queue.Queue | None = None
_online_triggers = {
    "checkpoint": threading.Event(),
    "generate": threading.Event(),
    "evaluate": threading.Event(),
}


def _check_trigger(name: str) -> bool:
    if _online_triggers[name].is_set():
        _online_triggers[name].clear()
        return True
    return False


def _report_analysis(result: str, mode: str):
    """Callback to push analysis results to SSE queue."""
    if _online_events_queue:
        _online_events_queue.put({
            "type": "analysis",
            "mode": mode,
            "result": result
        })


def _report_transcript(speaker: str, text: str, is_final: bool):
    """Callback to push transcript updates to SSE queue."""
    if _online_events_queue:
        _online_events_queue.put({
            "type": "transcript",
            "speaker": speaker,
            "text": text,
            "is_final": is_final
        })


@app.get("/online/devices")
def list_audio_devices():
    """List available audio input devices."""
    devices = sd.query_devices()
    result = []

    # Add system audio option if available (macOS only)
    if SystemAudioSTT.is_available():
        result.append({
            "id": DualStreamingSTT.SYSTEM_AUDIO_DEVICE,  # -1
            "name": "System Audio (macOS)",
            "channels": 2,
            "is_default": False,
            "is_system_audio": True
        })

    for i, d in enumerate(devices):
        if d["max_input_channels"] > 0:  # Only input devices
            result.append({
                "id": i,
                "name": d["name"],
                "channels": d["max_input_channels"],
                "is_default": i == sd.default.device[0],
                "is_system_audio": False
            })
    return {"devices": result}


@app.post("/online/start")
def start_online_session(req: OnlineStartRequest):
    """Start live interview session with specified audio devices."""
    global _online_stop_event, _online_events_queue

    if _online_stop_event is not None and not _online_stop_event.is_set():
        return {"success": False, "error": "Session already running"}

    # Reset state
    _online_events_queue = queue.Queue()
    with strategies.log_lock:
        strategies.conversation_log = ""

    # Configure device IDs
    strategies.INTERVIEWER_DEVICE_ID = req.interviewer_device_id
    strategies.CANDIDATE_DEVICE_ID = req.candidate_device_id

    # Launch threads with streaming STT
    _online_stop_event = strategies.launch_threads(
        if_checkpoint=lambda: _check_trigger("checkpoint"),
        if_generate=lambda: _check_trigger("generate"),
        if_evaluate=lambda: _check_trigger("evaluate"),
        report_analysis=_report_analysis,
        report_transcript=_report_transcript,
    )

    log.info(f"Online session started: interviewer={req.interviewer_device_id}, candidate={req.candidate_device_id}")
    return {"success": True, "session_dir": strategies.current_session_dir}


@app.post("/online/stop")
def stop_online_session():
    """Stop live interview session."""
    global _online_stop_event

    if _online_stop_event is None:
        return {"success": False, "error": "No session running"}

    _online_stop_event.set()
    _online_stop_event = None
    log.info("Online session stopped")
    return {"success": True}


@app.get("/online/transcript")
def get_transcript():
    """Get current conversation transcript."""
    with strategies.log_lock:
        return {"transcript": strategies.conversation_log}


@app.post("/online/trigger/{action}")
def trigger_action(action: str):
    """Trigger analysis action: generate, evaluate, or checkpoint."""
    if action not in _online_triggers:
        return {"success": False, "error": f"Unknown action: {action}"}
    _online_triggers[action].set()
    return {"success": True, "action": action}


@app.get("/online/events")
def online_events():
    """SSE endpoint for real-time updates (transcript + analysis)."""

    def generate():
        while True:
            if _online_events_queue:
                try:
                    msg = _online_events_queue.get(timeout=0.5)
                    yield f"data: {json.dumps(msg)}\n\n"
                    continue
                except queue.Empty:
                    pass

            if _online_stop_event is None or _online_stop_event.is_set():
                yield f"data: {json.dumps({'type': 'stopped'})}\n\n"
                break

            yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
