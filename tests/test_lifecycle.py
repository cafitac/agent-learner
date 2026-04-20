from pathlib import Path

from agent_learner.core.lifecycle import LearningLifecycle
from agent_learner.core.models import LearningRule


def test_promote_creates_approved_rule(tmp_path: Path) -> None:
    lifecycle = LearningLifecycle(tmp_path)
    rule = LearningRule(
        name="change-with-tests",
        rule="Update or add tests whenever behavior changes.",
        why="Avoid shipping changes without verification coverage.",
        scope="changes",
        good_pattern="Update production code and tests in the same change.",
        avoid_pattern="Postpone test updates until later.",
    )
    path = lifecycle.promote(rule)
    assert path.exists()
    assert path.name == "change-with-tests.md"
    assert "status: approved" in path.read_text(encoding="utf-8")
