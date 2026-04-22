from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

RuleStatus = Literal["draft", "approved", "needs_review", "deprecated"]
RulePriority = Literal["low", "medium", "high"]
RuleConfidence = Literal["low", "medium", "high"]
RuleModelDependency = Literal["none", "low", "high"]
ComparisonDecisionType = Literal["new_rule", "refresh_existing", "revise_existing", "fork_rule", "reject_candidate"]
BrainScope = Literal["project", "global"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


@dataclass(slots=True)
class LearningRule:
    name: str
    rule: str
    why: str
    scope: str
    good_pattern: str
    avoid_pattern: str
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    task_types: list[str] = field(default_factory=list)
    file_patterns: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=lambda: ["*"])
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    validated_on_models: list[str] = field(default_factory=list)
    excluded_models: list[str] = field(default_factory=list)
    model_dependency: RuleModelDependency = "low"
    priority: RulePriority = "medium"
    confidence: RuleConfidence = "medium"
    status: RuleStatus = "draft"
    source: str | None = None
    evidence: str | None = None
    first_seen_at: str | None = None
    last_seen_at: str | None = None
    updated_at: str | None = None
    last_used: str | None = None
    promote_count: int = 0
    refresh_count: int = 0
    use_count: int = 0
    token_estimate: int = 0
    source_event: str | None = None
    source_adapter: str | None = None
    derived_from_candidate: str | None = None
    decision: ComparisonDecisionType | None = None
    decision_reason: str | None = None
    supersedes: str | None = None
    superseded_by: str | None = None
    related_rule: str | None = None
    evidence_excerpt: str | None = None
    last_validated_at: str | None = None
    last_validated_by: str | None = None
    brain_scope: BrainScope = "project"
    source_project: str | None = None

    def ensure_defaults(self) -> None:
        if not self.summary:
            self.summary = self.rule
        if not self.projects:
            self.projects = ["*"]
        if not self.first_seen_at:
            self.first_seen_at = utc_now_iso()


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
