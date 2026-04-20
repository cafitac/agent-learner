from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .models import LearningRule


class LearningLifecycle:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.inbox = root / "inbox"
        self.drafts = root / "drafts"
        self.approved = root / "approved"
        self.needs_review = root / "needs_review"
        self.deprecated = root / "deprecated"
        for path in (self.inbox, self.drafts, self.approved, self.needs_review, self.deprecated):
            path.mkdir(parents=True, exist_ok=True)

    def promote(self, rule: LearningRule) -> Path:
        rule.status = "approved"
        rule.promote_count = max(rule.promote_count, 1)
        target = self.approved / f"{rule.name}.md"
        target.write_text(self.render_rule(rule), encoding="utf-8")
        return target

    def render_rule(self, rule: LearningRule) -> str:
        return (
            "---\n"
            f"name: {rule.name}\n"
            f"description: {rule.rule}\n"
            f"type: learned-feedback\n"
            f"status: {rule.status}\n"
            f"promote_count: {rule.promote_count}\n"
            "---\n\n"
            f"## Rule\n{rule.rule}\n\n"
            f"## Why\n{rule.why}\n\n"
            f"## Scope\n{rule.scope}\n\n"
            f"## Good pattern\n{rule.good_pattern}\n\n"
            f"## Avoid\n{rule.avoid_pattern}\n"
        )
