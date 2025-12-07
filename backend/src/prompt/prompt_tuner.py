from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from pydantic import BaseModel, Field  # type: ignore[import-not-found]

from ..common.grok import call_grok
from .prompt import PromptVersion, SystemPrompt
from .constant import MAX_TUNING_TOKENS


logger = logging.getLogger(__name__)

@dataclass
class TuningReward:
    question: str
    accepted: bool
    meta: Optional[dict] = None


class PromptUpdateResponse(BaseModel):
    new_prompt: str = Field(..., description="Full updated prompt text.")
    diff_summary: Optional[str] = Field(
        None, description="Short summary of changes from prior prompt."
    )

class PromptTuner:
    """
    High-level orchestrator to tune a SystemPrompt based on rewards.
    """

    def __init__(
        self,
        tuner_system_prompt: str = (
            "You are a prompt-tuning assistant. Given the prompt change history "
            "and reward feedback, propose the next full prompt text and a brief "
            "diff-style summary of changes."
        ),
        model: str = "grok-4-1-fast-reasoning",
        max_tokens: int = MAX_TUNING_TOKENS,
    ) -> None:
        self.tuner_system_prompt = tuner_system_prompt
        self.model = model
        self.max_tokens = max_tokens

    def tune(
        self,
        prompt: SystemPrompt,
        rewards: Sequence[TuningReward],
    ) -> str:
        """
        Tune the provided SystemPrompt using the given rewards.

        Returns the new prompt version id.
        """
        current = prompt.latest()
        if current is None:
            raise ValueError("Prompt has no versions; ensure baseline is initialized.")

        # Persist incoming rewards to the latest prompt version.
        for r in rewards:
            prompt.record_reward(
                version_id=current.id,
                question=r.question,
                accepted=r.accepted,
                meta=r.meta,
            )
        logger.info(
            "Recorded %s rewards for prompt '%s' at version %s",
            len(rewards),
            prompt.prompt_name,
            current.id,
        )

        change_summary = self._build_change_summary(prompt.history())
        current_text = current.prompt_text
        user_prompt = self._format_user_prompt(
            prompt_name=prompt.prompt_name,
            current_prompt=current_text,
            change_summary=change_summary,
            rewards=rewards,
        )

        logger.info(
            "Tuning prompt '%s' (latest id=%s) with %s rewards; summary length=%s chars",
            prompt.prompt_name,
            current.id,
            len(rewards),
            len(change_summary),
        )

        response: PromptUpdateResponse = call_grok(
            user_prompt=user_prompt,
            system_prompt=self.tuner_system_prompt,
            model=self.model,
            max_tokens=self.max_tokens,
            response_model=PromptUpdateResponse,
        )

        diff_summary = response.diff_summary or "model-proposed update"
        new_id = prompt.propose_update(
            new_prompt_text=response.new_prompt,
            diff_summary=diff_summary,
        )
        logger.info(
            "Created new prompt version %s for '%s' with diff_summary=%r",
            new_id,
            prompt.prompt_name,
            diff_summary,
        )
        return new_id

    @staticmethod
    def _build_change_summary(history: Iterable[PromptVersion]) -> str:
        lines: List[str] = []
        for version in history:
            lines.append(f"- {version.id}: {version.diff_summary}")
        if not lines:
            return "No prior changes (initial baseline)."
        return "\n".join(lines)

    @staticmethod
    def _format_user_prompt(
        prompt_name: str,
        current_prompt: str,
        change_summary: str,
        rewards: Sequence[TuningReward],
    ) -> str:
        reward_lines = []
        for r in rewards:
            reward_lines.append(
                f"- question: {r.question!r} | accepted: {r.accepted} | meta: {r.meta}"
            )
        reward_block = "\n".join(reward_lines) if reward_lines else "No rewards yet."

        return (
            f"Prompt name: {prompt_name}\n\n"
            f"Current prompt:\n{current_prompt}\n\n"
            f"Recent change summary:\n{change_summary}\n\n"
            f"Reward feedback:\n{reward_block}\n\n"
            "Please return JSON matching the response model to update the prompt."
        )