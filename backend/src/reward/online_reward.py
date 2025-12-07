import time
import threading
from typing import List, Dict, Optional, Literal, Tuple
from pydantic import BaseModel, Field

from ..common.grok import call_grok
from ..prompt.prompt_tuner import TuningReward


class OnlineReward:
    """Manages generated questions for a single kind (bait or hint) and emits rewards."""

    def __init__(self, kind: Literal["bait", "hint"]) -> None:
        self.kind = kind
        self.questions: List[Dict] = []
        self.pending_rewards: List[TuningReward] = []
        self.last_tune_ts: float = 0.0
        self._lock = threading.Lock()

    @staticmethod
    def _build_match_prompt(interviewer_q: str, candidates: List[Tuple[str, str]]) -> Tuple[str, str]:
        """
        Build prompts for Grok similarity matching.
        
        candidates: list of (ref_id, question)
        """
        system_prompt = (
            "You are a semantic matcher. Given an interviewer question and a list of "
            "previously generated bait/hint questions, decide if any are semantically similar. "
            "Return strict JSON: "
            "{'matched': bool, 'ref': ref_id_or_null, 'confidence': 0-1, 'reason': '...'}"
        )
        formatted = "\n".join([f"{idx+1}. [{ref}] {q}" for idx, (ref, q) in enumerate(candidates)])
        user_prompt = (
            f"Interviewer question: \"{interviewer_q}\"\n"
            f"Candidate generated questions:\n{formatted}\n"
            "If no good match, set matched=false and ref=null."
        )
        return system_prompt, user_prompt

    def store_generated(self, questions: List[str]) -> None:
        """Persist generated questions in session state."""
        now = time.time()
        with self._lock:
            for q in questions:
                normalized = q.strip()
                if not normalized:
                    continue
                self.questions.append({"text": normalized, "ts": now, "used": False})

    class RewardMatchResponse(BaseModel):
        matched: bool = Field(..., description="True if a candidate question matches")
        ref: Optional[str] = Field(None, description="Reference id of matched question")
        confidence: float = Field(0.0, description="Confidence score 0-1")
        reason: Optional[str] = Field(None, description="Short rationale for the match")

    def match_interviewer_question(self, interviewer_q: str) -> Optional[Tuple[TuningReward, Dict]]:
        """Ask Grok to match interviewer question to stored questions."""
        with self._lock:
            candidates: List[Tuple[str, str, Dict]] = []
            for idx, item in enumerate(self.questions):
                if not item.get("used"):
                    candidates.append((f"{self.kind}-{idx}", item["text"], item))

        if not candidates:
            return None

        ref_pairs = [(ref, q) for ref, q, _ in candidates]
        system_prompt, user_prompt = self._build_match_prompt(interviewer_q, ref_pairs)

        try:
            resp: OnlineReward.RewardMatchResponse = call_grok(
                user_prompt,
                system_prompt,
                is_reasoning=False,
                max_tokens=256,
                response_model=OnlineReward.RewardMatchResponse,
            )
        except Exception as e:
            print(f"⚠️ [Reward Matcher Error]: {e}")
            return None

        if not resp.matched:
            return None

        ref = resp.ref
        if not isinstance(ref, str):
            return None

        try:
            ref_kind, idx_str = ref.split("-", 1)
            idx = int(idx_str)
        except Exception:
            return None

        with self._lock:
            if ref_kind != self.kind:
                return None

            if idx < 0 or idx >= len(self.questions):
                return None

            entry = self.questions[idx]
            if entry.get("used"):
                return None
            entry["used"] = True

        confidence = resp.confidence
        reason = resp.reason or ""
        reward = TuningReward(
            question=entry["text"],
            accepted=True,
            meta={
                "kind": self.kind,
                "confidence": confidence,
                "reason": reason,
                "interviewer_question": interviewer_q,
            },
        )

        with self._lock:
            self.pending_rewards.append(reward)

        return reward, {"kind": self.kind, "confidence": confidence, "reason": reason}

    def take_pending_rewards(self) -> List[TuningReward]:
        """Atomically fetch and clear pending rewards."""
        with self._lock:
            rewards = list(self.pending_rewards)
            self.pending_rewards.clear()
            return rewards

    def put_back_pending(self, rewards: List[TuningReward]) -> None:
        """Re-queue rewards (used when tuning cooldown not met)."""
        if not rewards:
            return
        with self._lock:
            self.pending_rewards.extend(rewards)

    def last_tuned_at(self) -> float:
        with self._lock:
            return self.last_tune_ts

    def mark_tuned(self, ts: float) -> None:
        with self._lock:
            self.last_tune_ts = ts

