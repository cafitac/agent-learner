from __future__ import annotations

import json
from pathlib import Path

from agent_learner.core.context import detect_context
from agent_learner.core.lifecycle import LearningLifecycle
from agent_learner.core.retrieval import RetrievedRule, RetrievalRequest, retrieve_rules

DEFAULT_CONTEXT_LIMIT = 3
DEFAULT_TOKEN_BUDGET = 240


def build_retrieval_request(prompt: str, project_root: Path, **kwargs: object) -> RetrievalRequest:
    context = kwargs.get("context") or detect_context(project_root)
    return RetrievalRequest(
        query=prompt,
        scope=kwargs.get("scope"),
        task_type=kwargs.get("task_type") or infer_task_type(prompt),
        file_paths=list(kwargs.get("file_paths") or []),
        limit=int(kwargs.get("limit") or DEFAULT_CONTEXT_LIMIT),
        token_budget=kwargs.get("token_budget"),
        include_needs_review=bool(kwargs.get("include_needs_review", False)),
        context=context,
    )


def retrieve_for_codex(learning_root: Path, prompt: str, **kwargs: object) -> list[RetrievedRule]:
    lifecycle = LearningLifecycle(learning_root)
    project_root = learning_root.parents[2] if learning_root.name == "learning" else learning_root
    results = retrieve_rules(lifecycle, build_retrieval_request(prompt, project_root, **kwargs))
    if kwargs.get("track_usage", True):
        for result in results:
            lifecycle.touch_rule(result.path)
    return results


def infer_task_type(prompt: str) -> str | None:
    normalized = prompt.lower()
    if any(word in normalized for word in ["refactor", "cleanup", "clean up"]):
        return "refactor"
    if any(word in normalized for word in ["test", "pytest", "unit test", "regression"]):
        return "test"
    if any(word in normalized for word in ["docs", "readme", "documentation"]):
        return "docs"
    if any(word in normalized for word in ["bug", "fix", "failure", "error"]):
        return "bugfix"
    if any(word in normalized for word in ["cli", "command", "hook"]):
        return "cli"
    if any(word in normalized for word in ["prompt", "context", "inject"]):
        return "prompt"
    return None


def render_codex_learning_context(
    learning_root: Path,
    prompt: str,
    *,
    scope: str | None = None,
    task_type: str | None = None,
    file_paths: list[str] | None = None,
    limit: int = DEFAULT_CONTEXT_LIMIT,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    include_needs_review: bool = False,
) -> str | None:
    results = retrieve_for_codex(
        learning_root,
        prompt,
        scope=scope,
        task_type=task_type,
        file_paths=file_paths or [],
        limit=limit,
        token_budget=token_budget,
        include_needs_review=include_needs_review,
    )
    if not results:
        return None

    lines = [
        "<active_learning>",
        "Use only if relevant to the current task. These repo-local learned rules were selected for this turn.",
    ]
    for result in results:
        rule = result.rule
        applies: list[str] = []
        if rule.task_types:
            applies.append(f"task types: {', '.join(rule.task_types)}")
        if rule.file_patterns:
            applies.append(f"file patterns: {', '.join(rule.file_patterns)}")
        if rule.triggers:
            applies.append(f"triggers: {', '.join(rule.triggers)}")
        if rule.languages:
            applies.append(f"languages: {', '.join(rule.languages)}")
        if rule.frameworks:
            applies.append(f"frameworks: {', '.join(rule.frameworks)}")
        applies_text = f" Applies when: {'; '.join(applies)}." if applies else ""
        status_text = "" if rule.status == "approved" else f" [{rule.status}]"
        lines.append(
            f"- {rule.name}{status_text}: {rule.summary or rule.rule}. Scope: {rule.scope}.{applies_text}"
        )
    lines.append("</active_learning>")
    return "\n".join(lines)


def build_codex_user_prompt_hook_output(
    project_root: Path,
    prompt: str,
    *,
    scope: str | None = None,
    task_type: str | None = None,
    file_paths: list[str] | None = None,
    limit: int = DEFAULT_CONTEXT_LIMIT,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
) -> dict[str, object] | None:
    additional_context = render_codex_learning_context(
        project_root / ".codex" / "references" / "learning",
        prompt,
        scope=scope,
        task_type=task_type,
        file_paths=file_paths,
        limit=limit,
        token_budget=token_budget,
    )
    if not additional_context:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context,
        }
    }


def format_retrieval_results_as_text(project_root: Path, prompt: str, **kwargs: object) -> str:
    learning_root = project_root / ".codex" / "references" / "learning"
    results = retrieve_for_codex(learning_root, prompt, **kwargs)
    if not results:
        return "No matching learning rules found."
    lines = []
    for result in results:
        lines.append(
            f"- {result.rule.name} [{result.rule.status}] score={result.score:.1f} tokens={result.token_cost}: {result.rule.summary or result.rule.rule}"
        )
    return "\n".join(lines)


def format_retrieval_results_as_json(project_root: Path, prompt: str, **kwargs: object) -> str:
    learning_root = project_root / ".codex" / "references" / "learning"
    results = retrieve_for_codex(learning_root, prompt, **kwargs)
    payload = [
        {
            "name": result.rule.name,
            "status": result.rule.status,
            "score": round(result.score, 3),
            "token_cost": result.token_cost,
            "summary": result.rule.summary or result.rule.rule,
            "scope": result.rule.scope,
            "reasons": result.reasons,
            "path": str(result.path),
        }
        for result in results
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)
