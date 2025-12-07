from pathlib import Path
from backend.src.common.file_utils import load_text

PROMPT_STORE_ROOT = "/tmp/prompt_store"
BASELINE_DIR = Path(__file__).parent / "baseline_prompts"
TUNER_SYSTEM_PROMPT=load_text("tuner_system_prompt", BASELINE_DIR)

MAX_TUNING_TOKENS = 8096