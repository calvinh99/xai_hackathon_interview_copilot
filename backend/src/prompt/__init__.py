"""
Simple registry of prompt lineages. Baseline text is kept in plain files under
`baseline_prompts/` (sibling to this module). Each SystemPrompt requires baseline
text on first initialization; subsequent loads reuse existing history.
"""

from .prompt import SystemPrompt
from .constant import BASELINE_DIR, TUNER_SYSTEM_PROMPT
from backend.src.common.file_utils import load_text

interview_baseline_prompt = SystemPrompt(
    "interview_baseline",
    baseline_text=load_text("interview_baseline", BASELINE_DIR),
)

__all__ = [
    "SystemPrompt",
    "interview_baseline_prompt",
    "TUNER_SYSTEM_PROMPT",
]