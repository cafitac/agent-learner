from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class LearningRule:
    name: str
    rule: str
    why: str
    scope: str
    good_pattern: str
    avoid_pattern: str
    status: str = "draft"
    first_seen_at: str | None = None
    last_seen_at: str | None = None
    promote_count: int = 0


@dataclass(slots=True)
class LearningSnapshot:
    session_id: str
    branch: str
    captured_at: str
    changed_files: list[str] = field(default_factory=list)
    diff_summary: str = ""
    recent_commits: str = ""

    @classmethod
    def now(cls, session_id: str, branch: str) -> "LearningSnapshot":
        return cls(session_id=session_id, branch=branch, captured_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
