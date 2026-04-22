from pathlib import Path

from agent_learner.core.lifecycle import LearningLifecycle
from agent_learner.core.indexing import load_rule_index, rule_index_json_path, rule_index_markdown_path
from agent_learner.core.models import LearningRule


def make_rule(name: str = "change-with-tests") -> LearningRule:
    return LearningRule(
        name=name,
        rule="Update or add tests whenever behavior changes.",
        why="Avoid shipping changes without verification coverage.",
        scope="changes",
        good_pattern="Update production code and tests in the same change.",
        avoid_pattern="Postpone test updates until later.",
        summary="Keep tests aligned with behavior changes.",
        tags=["tests", "behavior"],
        triggers=["behavior", "validation"],
        task_types=["bugfix", "refactor"],
        file_patterns=["src/**", "tests/**"],
        priority="high",
        confidence="high",
    )


def test_promote_creates_approved_rule(tmp_path: Path) -> None:
    lifecycle = LearningLifecycle(tmp_path)
    rule = make_rule()
    path = lifecycle.promote(rule)
    assert path.exists()
    assert path.name == "change-with-tests.md"
    content = path.read_text(encoding="utf-8")
    assert "status: approved" in content
    assert "task_types: [\"bugfix\", \"refactor\"]" in content


def test_save_and_load_rule_round_trip(tmp_path: Path) -> None:
    lifecycle = LearningLifecycle(tmp_path)
    rule = make_rule("prompt-routing")
    path = lifecycle.save_draft(rule)
    loaded = lifecycle.load_rule(path)
    assert loaded.name == rule.name
    assert loaded.summary == rule.summary
    assert loaded.tags == rule.tags
    assert loaded.task_types == rule.task_types
    assert loaded.file_patterns == rule.file_patterns
    assert loaded.status == "draft"


def test_rule_transitions_move_single_copy_between_statuses(tmp_path: Path) -> None:
    lifecycle = LearningLifecycle(tmp_path)
    rule = make_rule("single-source-rule")
    lifecycle.save_draft(rule)
    approved_path = lifecycle.promote(rule)
    assert approved_path.exists()
    assert not (tmp_path / "drafts" / "single-source-rule.md").exists()

    needs_review_path = lifecycle.mark_needs_review(rule)
    assert needs_review_path.exists()
    assert not approved_path.exists()

    deprecated_path = lifecycle.deprecate(rule)
    assert deprecated_path.exists()
    assert not needs_review_path.exists()


def test_validate_exclude_and_sweep_rule_lifecycle(tmp_path: Path) -> None:
    lifecycle = LearningLifecycle(tmp_path)
    rule = make_rule("model-sensitive-rule")
    rule.model_dependency = "high"
    path = lifecycle.promote(rule)
    lifecycle.validate_rule(path, "claude-sonnet-4-6")
    validated = lifecycle.load_rule("model-sensitive-rule")
    assert "claude-sonnet-4-6" in validated.validated_on_models

    lifecycle.exclude_rule("model-sensitive-rule", "claude-opus-4-7")
    excluded = lifecycle.load_rule("model-sensitive-rule", statuses=["needs_review"])
    assert excluded.status == "needs_review"
    assert "claude-opus-4-7" in excluded.excluded_models

    needs_review_path = lifecycle.path_for_status("needs_review") / "model-sensitive-rule.md"
    content = needs_review_path.read_text(encoding="utf-8").replace(excluded.updated_at or "", "2000-01-01T00:00:00Z")
    needs_review_path.write_text(content, encoding="utf-8")
    changes = lifecycle.sweep_rules(current_model="claude-opus-4-7", needs_review_days=1)
    assert any(change["to"] == "deprecated" for change in changes)


def test_touch_rule_updates_use_tracking(tmp_path: Path) -> None:
    lifecycle = LearningLifecycle(tmp_path)
    path = lifecycle.promote(make_rule("touch-me"))
    lifecycle.touch_rule(path)
    touched = lifecycle.load_rule("touch-me")
    assert touched.use_count == 1
    assert touched.last_used is not None


def test_refresh_updates_provenance_fields(tmp_path: Path) -> None:
    lifecycle = LearningLifecycle(tmp_path)
    lifecycle.promote(make_rule("refresh-me"))
    lifecycle.refresh(
        "refresh-me",
        source_event="codex/stop-1.json",
        source_adapter="codex",
        derived_from_candidate="candidate-refresh-me.md",
        decision_reason="same meaning and fresher evidence",
        evidence_excerpt="Update or add tests whenever behavior changes.",
    )
    refreshed = lifecycle.load_rule("refresh-me")
    assert refreshed.refresh_count == 1
    assert refreshed.decision == "refresh_existing"
    assert refreshed.source_event == "codex/stop-1.json"
    assert refreshed.source_adapter == "codex"
    assert refreshed.derived_from_candidate == "candidate-refresh-me.md"


def test_promote_updates_machine_and_human_indexes(tmp_path: Path) -> None:
    lifecycle = LearningLifecycle(tmp_path)
    lifecycle.promote(make_rule("indexed-rule"))

    document = load_rule_index(tmp_path)
    assert document is not None
    assert any(entry.name == "indexed-rule" for entry in document.entries)
    assert rule_index_json_path(tmp_path).exists()
    assert rule_index_markdown_path(tmp_path).exists()
    assert "indexed-rule" in rule_index_markdown_path(tmp_path).read_text(encoding="utf-8")
