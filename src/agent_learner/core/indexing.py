from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .models import LearningScope, LearningRule, RuleConfidence, RulePriority, RuleStatus, RuleModelDependency, utc_now_iso

if TYPE_CHECKING:
    from .lifecycle import LearningLifecycle


@dataclass(slots=True)
class RuleIndexEntry:
    name: str
    relative_path: str
    status: RuleStatus
    summary: str
    rule: str
    why: str
    scope: str
    good_pattern: str
    avoid_pattern: str
    tags: list[str]
    triggers: list[str]
    task_types: list[str]
    file_patterns: list[str]
    projects: list[str]
    languages: list[str]
    frameworks: list[str]
    validated_on_models: list[str]
    excluded_models: list[str]
    model_dependency: RuleModelDependency
    priority: RulePriority
    confidence: RuleConfidence
    token_estimate: int
    use_count: int
    refresh_count: int
    promote_count: int
    updated_at: str | None
    last_used: str | None
    harness: str = "universal"
    learning_scope: LearningScope = "project"
    source_project: str | None = None
    repo_id: str | None = None
    repo_root: str | None = None
    worktree_path: str | None = None


@dataclass(slots=True)
class RuleIndexDocument:
    learning_root: str
    generated_at: str
    total_rules: int
    entries: list[RuleIndexEntry]


def index_root_for_learning_root(learning_root: Path) -> Path:
    return learning_root.parent / "index"


def rule_index_json_path(learning_root: Path) -> Path:
    return index_root_for_learning_root(learning_root) / "rules.json"


def rule_index_markdown_path(learning_root: Path) -> Path:
    return index_root_for_learning_root(learning_root) / "index.md"


def rule_to_index_entry(learning_root: Path, path: Path, rule: LearningRule) -> RuleIndexEntry:
    return RuleIndexEntry(
        name=rule.name,
        relative_path=str(path.relative_to(learning_root)),
        status=rule.status,
        summary=rule.summary or rule.rule,
        rule=rule.rule,
        why=rule.why,
        scope=rule.scope,
        good_pattern=rule.good_pattern,
        avoid_pattern=rule.avoid_pattern,
        tags=list(rule.tags),
        triggers=list(rule.triggers),
        task_types=list(rule.task_types),
        file_patterns=list(rule.file_patterns),
        projects=list(rule.projects),
        languages=list(rule.languages),
        frameworks=list(rule.frameworks),
        validated_on_models=list(rule.validated_on_models),
        excluded_models=list(rule.excluded_models),
        model_dependency=rule.model_dependency,
        priority=rule.priority,
        confidence=rule.confidence,
        token_estimate=rule.token_estimate,
        use_count=rule.use_count,
        refresh_count=rule.refresh_count,
        promote_count=rule.promote_count,
        updated_at=rule.updated_at,
        last_used=rule.last_used,
        learning_scope=rule.learning_scope,
        source_project=rule.source_project,
        repo_id=rule.repo_id,
        repo_root=rule.repo_root,
        worktree_path=rule.worktree_path,
        harness=rule.harness,
    )


def build_rule_index_document(lifecycle: "LearningLifecycle") -> RuleIndexDocument:
    learning_root = lifecycle.root
    entries: list[RuleIndexEntry] = []
    for path in lifecycle.list_rule_paths():
        rule = lifecycle.load_rule(path)
        entries.append(rule_to_index_entry(learning_root, path, rule))
    entries.sort(key=lambda item: (item.status, item.name))
    return RuleIndexDocument(
        learning_root=str(learning_root),
        generated_at=utc_now_iso(),
        total_rules=len(entries),
        entries=entries,
    )


def write_rule_index_document(document: RuleIndexDocument, learning_root: Path) -> dict[str, Path]:
    index_root = index_root_for_learning_root(learning_root)
    index_root.mkdir(parents=True, exist_ok=True)
    json_path = rule_index_json_path(learning_root)
    markdown_path = rule_index_markdown_path(learning_root)
    json_path.write_text(
        json.dumps(
            {
                "learning_root": document.learning_root,
                "generated_at": document.generated_at,
                "total_rules": document.total_rules,
                "entries": [asdict(entry) for entry in document.entries],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_rule_index_markdown(document), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def rebuild_rule_index(lifecycle: "LearningLifecycle") -> dict[str, object]:
    document = build_rule_index_document(lifecycle)
    paths = write_rule_index_document(document, lifecycle.root)
    return {
        "learning_root": str(lifecycle.root),
        "generated_at": document.generated_at,
        "total_rules": document.total_rules,
        "json_path": str(paths["json"]),
        "markdown_path": str(paths["markdown"]),
    }


def _prune_stale_entries(learning_root: Path, entries: list[RuleIndexEntry]) -> list[RuleIndexEntry]:
    pruned: list[RuleIndexEntry] = []
    for entry in entries:
        if (learning_root / entry.relative_path).exists():
            pruned.append(entry)
    return pruned


def sync_rule_index_entry(learning_root: Path, path: Path, rule: LearningRule) -> dict[str, object]:
    document = load_rule_index(learning_root)
    entries = [] if document is None else _prune_stale_entries(learning_root, document.entries)
    entries = [entry for entry in entries if entry.name != rule.name]
    entries.append(rule_to_index_entry(learning_root, path, rule))
    entries.sort(key=lambda item: (item.status, item.name))
    updated = RuleIndexDocument(
        learning_root=str(learning_root),
        generated_at=utc_now_iso(),
        total_rules=len(entries),
        entries=entries,
    )
    paths = write_rule_index_document(updated, learning_root)
    return {
        "learning_root": str(learning_root),
        "generated_at": updated.generated_at,
        "total_rules": updated.total_rules,
        "json_path": str(paths["json"]),
        "markdown_path": str(paths["markdown"]),
    }


def load_rule_index(learning_root: Path) -> RuleIndexDocument | None:
    path = rule_index_json_path(learning_root)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = [RuleIndexEntry(**item) for item in payload.get("entries", [])]
    return RuleIndexDocument(
        learning_root=str(payload.get("learning_root") or learning_root),
        generated_at=str(payload.get("generated_at") or ""),
        total_rules=int(payload.get("total_rules") or len(entries)),
        entries=entries,
    )


def ensure_rule_index(lifecycle: "LearningLifecycle") -> RuleIndexDocument:
    document = load_rule_index(lifecycle.root)
    if document is None:
        rebuild_rule_index(lifecycle)
        document = load_rule_index(lifecycle.root)
    assert document is not None
    return document


def render_rule_index_markdown(document: RuleIndexDocument) -> str:
    lines = [
        "# Rule Index",
        "",
        f"- Learning root: `{document.learning_root}`",
        f"- Generated at: `{document.generated_at}`",
        f"- Total rules: `{document.total_rules}`",
        "",
    ]
    statuses = ["approved", "needs_review", "draft", "deprecated"]
    for status in statuses:
        bucket = [entry for entry in document.entries if entry.status == status]
        if not bucket:
            continue
        lines.append(f"## {status}")
        lines.append("")
        for entry in sorted(bucket, key=lambda item: item.name):
            applies: list[str] = []
            if entry.task_types:
                applies.append(f"tasks={', '.join(entry.task_types)}")
            if entry.file_patterns:
                applies.append(f"files={', '.join(entry.file_patterns)}")
            if entry.languages:
                applies.append(f"langs={', '.join(entry.languages)}")
            if entry.frameworks:
                applies.append(f"frameworks={', '.join(entry.frameworks)}")
            applies_text = f" ({'; '.join(applies)})" if applies else ""
            lines.append(f"- `{entry.name}` — {entry.summary}{applies_text}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
