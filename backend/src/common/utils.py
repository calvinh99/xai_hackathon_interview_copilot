"""Shared utilities."""
import json
import os
from pathlib import Path


def load_env(env_path: Path | str | None = None):
    """Load .env file into environment. Tiny dotenv replacement."""
    if env_path is None:
        # Look in backend root
        env_path = Path(__file__).parent.parent.parent / ".env"
    env_path = Path(env_path)
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def parse_json_response(text: str) -> any:
    """Parse JSON from LLM response, handling markdown code blocks."""
    text = text.strip()
    if text.startswith("```"):
        # Extract content between first ``` and next ```
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
    return json.loads(text.strip())
