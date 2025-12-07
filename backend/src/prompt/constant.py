from pathlib import Path
from ..common.file_utils import load_text

PROMPT_STORE_ROOT = Path(__file__).parent.parent.parent / "prompt_store"
BASELINE_DIR = Path(__file__).parent / "baseline_prompts"
TUNER_SYSTEM_PROMPT=load_text("tuner_system_prompt", BASELINE_DIR)

MAX_TUNING_TOKENS = 8096