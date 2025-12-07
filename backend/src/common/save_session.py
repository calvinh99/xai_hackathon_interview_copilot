"""Session logging for API calls."""
import json
from datetime import datetime
from pathlib import Path
from threading import Lock

_session = None
_lock = Lock()


class Session:
    """Logs API calls to a JSON file."""

    def __init__(self):
        self.started = datetime.now().isoformat()
        self.calls = []
        self.output_dir = Path(__file__).parent.parent.parent / "outputs"
        self.output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filepath = self.output_dir / f"session_{timestamp}.json"
        self._save()

    def log(self, step: str, prompt: str, response: str, **metadata):
        """Log an API call."""
        self.calls.append({
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "prompt": prompt[:500] + "..." if len(prompt) > 500 else prompt,
            "response": response,
            "metadata": metadata,
        })
        self._save()

    def _save(self):
        """Save session to file."""
        with open(self.filepath, "w") as f:
            json.dump({"started": self.started, "calls": self.calls}, f, indent=2)


def get_session() -> Session:
    """Get or create the current session."""
    global _session
    with _lock:
        if _session is None:
            _session = Session()
        return _session


def reset_session():
    """Reset session for a new analysis run."""
    global _session
    with _lock:
        _session = Session()
    return _session
