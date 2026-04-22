from __future__ import annotations

import json
from pathlib import Path

from .lifecycle import LearningLifecycle
from .pipeline import approve_candidate, mark_candidate_needs_review, reject_candidate
from .storage import append_jsonl, ensure_global_learning_root, global_history_path, register_project, resolve_learning_root


def promote_rule_to_global(project_root: Path, name: str, *, all_projects: bool = False) -> dict[str, object]:
    project_root = project_root.resolve()
    register_project(project_root)
    local_lifecycle = LearningLifecycle(resolve_learning_root(project_root))
    global_lifecycle = LearningLifecycle(ensure_global_learning_root())
    rule = local_lifecycle.load_rule(name, statuses=["approved", "needs_review", "draft"])
    rule.brain_scope = "global"
    rule.source_project = project_root.name
    rule.projects = ["*"] if all_projects else sorted(set((rule.projects or []) + [project_root.name]))
    path = global_lifecycle.promote(rule)
    append_jsonl(
        global_history_path(),
        {
            "ts": rule.updated_at or "",
            "action": "promote_global",
            "rule": rule.name,
            "source_adapter": "project-sync",
            "source_project": project_root.name,
            "target_scope": "global",
        },
    )
    return {"rule": rule.name, "path": str(path), "projects": rule.projects, "brain_scope": rule.brain_scope}


def sync_rules_to_global(
    project_root: Path,
    *,
    min_promote_count: int = 1,
    min_use_count: int = 0,
    all_projects: bool = False,
) -> list[dict[str, object]]:
    project_root = project_root.resolve()
    register_project(project_root)
    local_lifecycle = LearningLifecycle(resolve_learning_root(project_root))
    global_lifecycle = LearningLifecycle(ensure_global_learning_root())
    promoted: list[dict[str, object]] = []
    for rule in local_lifecycle.list_rules(statuses=["approved"]):
        if rule.promote_count < min_promote_count or rule.use_count < min_use_count:
            continue
        rule.brain_scope = "global"
        rule.source_project = project_root.name
        rule.projects = ["*"] if all_projects else sorted(set((rule.projects or []) + [project_root.name]))
        path = global_lifecycle.promote(rule)
        promoted.append({"rule": rule.name, "path": str(path), "projects": rule.projects})
        append_jsonl(
            global_history_path(),
            {
                "ts": rule.updated_at or "",
                "action": "promote_global",
                "rule": rule.name,
                "source_adapter": "project-sync",
                "source_project": project_root.name,
                "target_scope": "global",
            },
        )
    return promoted


def apply_candidate_action(project_root: Path, candidate: str, action: str, reason: str | None = None) -> dict[str, object]:
    project_root = project_root.resolve()
    if action == "approve":
        record, saved_rule = approve_candidate(project_root, candidate)
        payload = {"candidate": str(record.path), "status": record.status, "rule_path": str(saved_rule), "action": "approve"}
    elif action == "reject":
        record = reject_candidate(project_root, candidate, reason=reason)
        payload = {"candidate": str(record.path), "status": record.status, "action": "reject"}
    else:
        record = mark_candidate_needs_review(project_root, candidate, reason=reason)
        payload = {"candidate": str(record.path), "status": record.status, "action": "needs-review"}
    payload["decision"] = record.candidate.decision
    payload["matched_rule"] = record.candidate.matched_rule
    payload["decision_reason"] = record.candidate.decision_reason
    payload["field_diffs"] = record.candidate.field_diffs or {}
    return payload
