"""Data models for offline analysis."""
from dataclasses import dataclass, field

@dataclass
class XPost:
    url: str
    content: str
    label: str  # "yes", "no", "could_be"

@dataclass
class SkillAnalysis:
    keyword: str
    priority_rank: int  # 1-10, lower is higher priority
    resume_sources: list[str] = field(default_factory=list)
    x_posts: list[XPost] = field(default_factory=list)
    flag: str = "no_data"  # "highly_suspect", "suspect", "verified", "no_data"

    def to_dict(self) -> dict:
        return {
            "keyword": self.keyword,
            "priority_rank": self.priority_rank,
            "resume_sources": self.resume_sources,
            "x_posts": [{"url": p.url, "content": p.content, "label": p.label} for p in self.x_posts],
            "flag": self.flag,
        }
