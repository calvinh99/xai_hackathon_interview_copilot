from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .constant import PROMPT_STORE_ROOT


@dataclass
class PromptVersion:
    """
    Represents a single prompt version on disk.
    """

    id: str
    parent_id: Optional[str]
    prompt_text: str
    diff_summary: str
    rewards: List[Dict[str, Any]]
    created_at: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptVersion":
        return cls(
            id=data["id"],
            parent_id=data.get("parent_id"),
            prompt_text=data["prompt_text"],
            diff_summary=data["diff_summary"],
            rewards=list(data.get("rewards", [])),
            created_at=data.get("created_at", time.time()),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "prompt_text": self.prompt_text,
            "diff_summary": self.diff_summary,
            "rewards": self.rewards,
            "created_at": self.created_at,
        }


class SystemPrompt:
    """
    Tracks the lineage of a single prompt. Each prompt instance owns its own
    folder under ``store_root`` named after the prompt (e.g. prompt_name="qa"
    -> prompt_store/qa/). Versions are stored as one JSON file per version with
    a HEAD file pointing at the latest version id. This keeps data durable
    across server restarts with no external dependencies.
    """

    def __init__(
        self,
        prompt_name: str,
        store_root: Path | str = PROMPT_STORE_ROOT,
        baseline_text: str | None = None,
        baseline_diff_summary: str = "baseline init",
    ) -> None:
        self.prompt_name = prompt_name
        self.store_root = Path(store_root)
        self.prompt_dir = self.store_root / prompt_name
        self.prompt_dir.mkdir(parents=True, exist_ok=True)
        self.head_path = self.prompt_dir / "HEAD"
        self._ensure_baseline(baseline_text, baseline_diff_summary)

    @classmethod
    def load(cls, prompt_name: str, store_root: Path | str = PROMPT_STORE_ROOT) -> "SystemPrompt":
        """
        Load an existing prompt lineage without creating a new directory.
        Raises FileNotFoundError if the prompt folder does not exist.
        """
        prompt_dir = Path(store_root) / prompt_name
        if not prompt_dir.exists():
            raise FileNotFoundError(
                f"SystemPrompt '{prompt_name}' not found under store '{store_root}'."
            )
        return cls(prompt_name, store_root=store_root)

    # ----- Public API --------------------------------------------------
    def latest_id(self) -> Optional[str]:
        """
        Return the id of the latest prompt version, or None if none exist.
        """
        if not self.head_path.exists():
            return None
        head = self.head_path.read_text().strip()
        return head or None

    def latest(self) -> Optional[PromptVersion]:
        """
        Load the latest prompt version (if any).
        """
        head = self.latest_id()
        return self.load_version(head) if head else None

    def history(self, from_id: Optional[str] = None) -> List[PromptVersion]:
        """
        Return lineage from the root to the specified version id.
        Defaults to the current HEAD if not provided.
        """
        current_id = from_id or self.latest_id()
        lineage: List[PromptVersion] = []
        while current_id:
            version = self.load_version(current_id)
            lineage.append(version)
            current_id = version.parent_id
        return list(reversed(lineage))

    def create_root(self, prompt_text: str, diff_summary: str = "init") -> str:
        """
        Create the initial prompt version. Fails if a version already exists.
        """
        if self.latest_id():
            raise ValueError(f"Prompt '{self.prompt_name}' already has a root; use propose_update instead.")

        version = PromptVersion(
            id=self._new_id(),
            parent_id=None,
            prompt_text=prompt_text,
            diff_summary=diff_summary,
            rewards=[],
            created_at=time.time(),
        )
        return self._write_version(version, update_head=True)

    def record_reward(
        self,
        version_id: str,
        question: str,
        accepted: bool,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Append a reward entry to a specific version. Does not change HEAD.
        """
        version = self.load_version(version_id)
        reward = {"question": question, "accepted": bool(accepted), "ts": time.time()}
        if meta:
            reward["meta"] = meta
        version.rewards.append(reward)
        # Re-write the same version file; keep HEAD untouched.
        self._write_version(version, update_head=False)

    def propose_update(
        self,
        new_prompt_text: str,
        parent_id: Optional[str] = None,
        diff_summary: Optional[str] = None,
    ) -> str:
        """
        Create a new prompt version as a child of parent_id (defaults to HEAD).
        """
        parent_id = parent_id or self.latest_id()
        if parent_id is None:
            raise ValueError("No existing prompt found; create_root first.")

        parent = self.load_version(parent_id)
        summary = diff_summary

        version = PromptVersion(
            id=self._new_id(),
            parent_id=parent.id,
            prompt_text=new_prompt_text,
            diff_summary=summary,
            rewards=[],
            created_at=time.time(),
        )
        return self._write_version(version, update_head=True)

    def load_version(self, version_id: str) -> PromptVersion:
        """
        Load a version by id from disk.
        """
        path = self._version_path(version_id)
        if not path.exists():
            raise FileNotFoundError(f"Version '{version_id}' not found for prompt '{self.prompt_name}'.")
        data = json.loads(path.read_text())
        return PromptVersion.from_dict(data)

    # ----- Internal helpers -------------------------------------------
    def _version_path(self, version_id: str) -> Path:
        return self.prompt_dir / f"{version_id}.json"

    def _write_version(self, version: PromptVersion, update_head: bool) -> str:
        path = self._version_path(version.id)
        path.write_text(json.dumps(version.to_dict(), indent=2))
        if update_head:
            self.head_path.write_text(version.id)
        return version.id

    def _new_id(self) -> str:
        return uuid.uuid4().hex

    def _ensure_baseline(self, baseline_text: str | None, diff_summary: str) -> None:
        """
        Ensure a root version exists; if none, create it from baseline_text.
        """
        if self.latest_id() is not None:
            return
        if baseline_text is None:
            raise ValueError(
                f"Baseline text is required to initialize prompt '{self.prompt_name}'."
            )
        self.create_root(baseline_text, diff_summary=diff_summary)