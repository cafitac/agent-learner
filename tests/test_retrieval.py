from agent_learner.core.context import detect_context, write_current_model
from pathlib import Path

from agent_learner.adapters.codex_context import render_codex_learning_context
from agent_learner.core.lifecycle import LearningLifecycle
from agent_learner.core.models import LearningRule
from agent_learner.core.retrieval import RetrievalRequest, retrieve_rules


def promote_rule(lifecycle: LearningLifecycle, **overrides: object) -> LearningRule:
    rule = LearningRule(
        name=str(overrides.pop("name", "rule")),
        rule=str(overrides.pop("rule", "Default rule text")),
        why=str(overrides.pop("why", "Why this rule exists")),
        scope=str(overrides.pop("scope", "general")),
        good_pattern=str(overrides.pop("good_pattern", "Good pattern")),
        avoid_pattern=str(overrides.pop("avoid_pattern", "Avoid pattern")),
        summary=str(overrides.pop("summary", "Summary")),
        tags=list(overrides.pop("tags", [])),
        triggers=list(overrides.pop("triggers", [])),
        task_types=list(overrides.pop("task_types", [])),
        file_patterns=list(overrides.pop("file_patterns", [])),
        priority=str(overrides.pop("priority", "medium")),
        confidence=str(overrides.pop("confidence", "medium")),
        token_estimate=int(overrides.pop("token_estimate", 0)),
    )
    for key, value in overrides.items():
        setattr(rule, key, value)
    lifecycle.promote(rule)
    return rule


def test_retrieve_prefers_relevant_rule(tmp_path: Path) -> None:
    lifecycle = LearningLifecycle(tmp_path)
    promote_rule(
        lifecycle,
        name="prompt-hook-tests",
        rule="Update tests when the Codex prompt hook changes.",
        summary="Keep Codex prompt hook changes covered by tests.",
        scope="codex adapter",
        triggers=["hook", "tests"],
        task_types=["cli"],
        file_patterns=["src/**", "tests/**"],
        priority="high",
        confidence="high",
    )
    promote_rule(
        lifecycle,
        name="docs-only",
        rule="Update docs when examples change.",
        summary="Keep docs aligned.",
        scope="documentation",
        task_types=["docs"],
    )

    results = retrieve_rules(
        lifecycle,
        RetrievalRequest(
            query="fix codex prompt hook tests",
            task_type="cli",
            file_paths=["src/agent_learner/adapters/codex.py"],
        ),
    )
    assert results
    assert results[0].rule.name == "prompt-hook-tests"


def test_retrieve_respects_token_budget_and_status_weight(tmp_path: Path) -> None:
    lifecycle = LearningLifecycle(tmp_path)
    approved = promote_rule(
        lifecycle,
        name="approved-rule",
        rule="Prefer approved prompt rules.",
        summary="Approved rules should win.",
        scope="codex adapter",
        token_estimate=80,
        priority="high",
    )
    review_rule = LearningRule(
        name="needs-review-rule",
        rule="This rule still needs review.",
        why="It is less trusted.",
        scope="codex adapter",
        good_pattern="Tentative good pattern",
        avoid_pattern="Tentative bad pattern",
        summary="This rule is tentative.",
        status="needs_review",
        token_estimate=60,
    )
    lifecycle.mark_needs_review(review_rule)

    results = retrieve_rules(
        lifecycle,
        RetrievalRequest(
            query="approved prompt rules",
            limit=5,
            token_budget=90,
            include_needs_review=True,
        ),
    )
    assert [result.rule.name for result in results] == [approved.name]


def test_render_codex_learning_context_only_includes_selected_rules(tmp_path: Path) -> None:
    lifecycle = LearningLifecycle(tmp_path / ".codex" / "references" / "learning")
    promote_rule(
        lifecycle,
        name="behavior-tests",
        rule="Update tests whenever behavior changes.",
        summary="Keep tests aligned with behavior changes.",
        scope="changes",
        triggers=["behavior", "tests"],
        task_types=["bugfix"],
    )
    promote_rule(
        lifecycle,
        name="docs-refresh",
        rule="Update docs after UX copy changes.",
        summary="Refresh docs for UX copy changes.",
        scope="documentation",
        task_types=["docs"],
    )

    context = render_codex_learning_context(
        tmp_path / ".codex" / "references" / "learning",
        "fix behavior bug and keep tests green",
        task_type="bugfix",
        token_budget=120,
    )
    assert context is not None
    assert "behavior-tests" in context
    assert "docs-refresh" not in context


def test_retrieve_respects_context_and_model_gating(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    write_current_model(tmp_path, "claude-opus-4-7")
    lifecycle = LearningLifecycle(tmp_path / ".codex" / "references" / "learning")
    promote_rule(
        lifecycle,
        name="python-approved",
        summary="Use Python-specific workflow.",
        scope="core",
        languages=["python"],
        projects=[tmp_path.name],
        model_dependency="high",
        validated_on_models=["claude-opus-4-6"],
    )
    promote_rule(
        lifecycle,
        name="excluded-rule",
        summary="Should not load on excluded model.",
        scope="core",
        languages=["python"],
        excluded_models=["claude-opus-4-7"],
    )

    results = retrieve_rules(
        lifecycle,
        RetrievalRequest(query="workflow", context=detect_context(tmp_path)),
    )
    assert [result.rule.name for result in results] == ["python-approved"]
