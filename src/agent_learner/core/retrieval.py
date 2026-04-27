from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path

from .context import ContextSnapshot
from .indexing import RuleIndexEntry, ensure_rule_index
from .lifecycle import LearningLifecycle
from .models import LearningRule, RuleStatus
from .storage import effective_learning_roots

WORD_RE = re.compile(r"[a-z0-9_./-]+")
APPROVED_STATUSES: list[RuleStatus] = ["approved"]
RETRIEVAL_STATUSES: list[RuleStatus] = ["approved", "needs_review"]


@dataclass(slots=True)
class RetrievedRule:
    rule: LearningRule
    path: Path
    score: float
    token_cost: int
    source_scope: str = "project"
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RetrievalRequest:
    query: str = ""
    scope: str | None = None
    task_type: str | None = None
    file_paths: list[str] = field(default_factory=list)
    limit: int = 3
    token_budget: int | None = None
    include_needs_review: bool = False
    context: ContextSnapshot | None = None
    adapter: str | None = None


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for match in WORD_RE.finditer(text.lower()):
        token = match.group(0).strip("._-/")
        if token:
            tokens.append(token)
    return tokens


def retrieve_rules(lifecycle: LearningLifecycle, request: RetrievalRequest) -> list[RetrievedRule]:
    statuses = RETRIEVAL_STATUSES if request.include_needs_review else APPROVED_STATUSES
    document = ensure_rule_index(lifecycle)
    scored: list[tuple[RuleIndexEntry, float, list[str]]] = []
    for entry in document.entries:
        if entry.status not in statuses:
            continue
        if request.adapter is not None and entry.harness not in (request.adapter, "universal", ""):
            continue
        if not should_inject_rule(entry, request.context):
            continue
        score, reasons = score_rule(entry, request)
        if score <= 0:
            continue
        scored.append((entry, score, reasons))
    scored.sort(key=lambda item: (-item[1], item[0].name))
    limited = scored[: max(request.limit * 3, request.limit)]
    selected = apply_budget_to_entries(limited, request.limit, request.token_budget)

    hydrated: list[RetrievedRule] = []
    for entry, score, reasons in selected:
        path = lifecycle.root / entry.relative_path
        rule = lifecycle.load_rule(path, statuses=statuses)
        hydrated.append(
            RetrievedRule(
                rule=rule,
                path=path,
                score=score,
                token_cost=entry.token_estimate or lifecycle.estimate_rule_tokens(rule),
                source_scope=entry.learning_scope,
                reasons=reasons,
            )
        )
    return hydrated


def retrieve_rules_for_project(project_root: Path, request: RetrievalRequest) -> list[RetrievedRule]:
    roots = effective_learning_roots(project_root)
    combined: dict[str, RetrievedRule] = {}
    for root in roots:
        lifecycle = LearningLifecycle(root)
        results = retrieve_rules(lifecycle, request)
        for result in results:
            existing = combined.get(result.rule.name)
            if existing is None:
                combined[result.rule.name] = result
                continue
            if result.score > existing.score:
                combined[result.rule.name] = result
                continue
            if result.score == existing.score and result.source_scope == "project" and existing.source_scope != "project":
                combined[result.rule.name] = result
    ranked = sorted(combined.values(), key=lambda item: (-item.score, 0 if item.source_scope == "project" else 1, item.rule.name))
    limited = ranked[: max(request.limit * 3, request.limit)]
    return apply_budget(limited, request.limit, request.token_budget)


def should_inject_rule(rule: LearningRule | RuleIndexEntry, context: ContextSnapshot | None) -> bool:
    if context is None:
        return True
    if rule.projects and rule.projects != ["*"] and context.project_name not in rule.projects:
        return False
    if rule.languages and not any(language in context.languages for language in rule.languages):
        return False
    if rule.frameworks and rule.frameworks != ["none"] and not any(framework in context.frameworks for framework in rule.frameworks):
        return False
    current_model = (context.current_model or "").strip()
    if current_model:
        if current_model in rule.excluded_models:
            return False
        if current_model in rule.validated_on_models:
            return True
        if rule.model_dependency == "none":
            return True
        if rule.model_dependency == "low":
            return True
        if rule.model_dependency == "high":
            return any(is_upgrade(validated, current_model) for validated in rule.validated_on_models)
    return True


def score_rule(rule: LearningRule | RuleIndexEntry, request: RetrievalRequest) -> tuple[float, list[str]]:
    score = 3.0 if rule.status == "approved" else 1.5
    reasons = [f"status:{rule.status}"]
    relevance = 0.0

    if request.scope and request.scope.lower() in rule.scope.lower():
        score += 2.5
        relevance += 2.5
        reasons.append("scope")
    if request.task_type and request.task_type in rule.task_types:
        score += 3.0
        relevance += 3.0
        reasons.append(f"task_type:{request.task_type}")

    for file_path in request.file_paths:
        if file_matches_rule(file_path, rule.file_patterns):
            score += 2.5
            relevance += 2.5
            reasons.append(f"file:{file_path}")
            break

    terms = tokenize(request.query)
    if not terms and not request.scope and not request.task_type and not request.file_paths:
        score += priority_bonus(rule.priority) + confidence_bonus(rule.confidence)
        score += usage_bonus(rule.use_count)
        return score, reasons

    indexed_fields = {
        "name": tokenize(rule.name),
        "summary": tokenize(rule.summary or rule.rule),
        "rule": tokenize(rule.rule),
        "scope": tokenize(rule.scope),
        "why": tokenize(rule.why),
        "tags": [item.lower() for item in rule.tags],
        "triggers": [item.lower() for item in rule.triggers],
        "task_types": [item.lower() for item in rule.task_types],
        "patterns": [item.lower() for item in rule.file_patterns],
        "projects": [item.lower() for item in rule.projects],
        "languages": [item.lower() for item in rule.languages],
        "frameworks": [item.lower() for item in rule.frameworks],
        "good_pattern": tokenize(rule.good_pattern),
        "avoid_pattern": tokenize(rule.avoid_pattern),
    }

    for term in terms:
        if term in indexed_fields["name"]:
            score += 3.5
            relevance += 3.5
            reasons.append(f"name:{term}")
        elif term in indexed_fields["summary"]:
            score += 3.0
            relevance += 3.0
            reasons.append(f"summary:{term}")
        elif term in indexed_fields["rule"]:
            score += 2.5
            relevance += 2.5
            reasons.append(f"rule:{term}")
        elif term in indexed_fields["triggers"] or term in indexed_fields["tags"]:
            score += 2.2
            relevance += 2.2
            reasons.append(f"metadata:{term}")
        elif term in indexed_fields["task_types"]:
            score += 2.0
            relevance += 2.0
            reasons.append(f"task:{term}")
        elif term in indexed_fields["patterns"]:
            score += 1.8
            relevance += 1.8
            reasons.append(f"pattern:{term}")
        elif term in indexed_fields["scope"] or term in indexed_fields["languages"] or term in indexed_fields["frameworks"]:
            score += 1.7
            relevance += 1.7
            reasons.append(f"scope-term:{term}")
        elif term in indexed_fields["projects"]:
            score += 1.5
            relevance += 1.5
            reasons.append(f"project:{term}")
        elif term in indexed_fields["why"] or term in indexed_fields["good_pattern"]:
            score += 1.0
            relevance += 1.0
            reasons.append(f"detail:{term}")

    if (terms or request.scope or request.task_type or request.file_paths) and relevance <= 0:
        return 0.0, reasons

    score += priority_bonus(rule.priority)
    score += confidence_bonus(rule.confidence)
    score += usage_bonus(rule.use_count)
    return score, reasons


def apply_budget_to_entries(results: list[tuple[RuleIndexEntry, float, list[str]]], limit: int, token_budget: int | None) -> list[tuple[RuleIndexEntry, float, list[str]]]:
    if token_budget is None:
        return results[:limit]
    selected: list[tuple[RuleIndexEntry, float, list[str]]] = []
    used = 0
    for entry, score, reasons in results:
        cost = max(1, entry.token_estimate)
        if selected and len(selected) >= limit:
            break
        if selected and used + cost > token_budget:
            continue
        if not selected and cost > token_budget:
            selected.append((entry, score, reasons))
            break
        selected.append((entry, score, reasons))
        used += cost
        if len(selected) >= limit:
            break
    return selected


def file_matches_rule(file_path: str, patterns: list[str]) -> bool:
    if not file_path or not patterns:
        return False
    normalized = file_path.replace("\\", "/")
    basename = Path(normalized).name
    return any(fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(basename, pattern) for pattern in patterns)


def priority_bonus(priority: str) -> float:
    return {"high": 1.4, "medium": 0.6, "low": 0.1}.get(priority, 0.0)


def confidence_bonus(confidence: str) -> float:
    return {"high": 0.9, "medium": 0.4, "low": 0.0}.get(confidence, 0.0)


def usage_bonus(use_count: int) -> float:
    return min(1.5, max(0, use_count) * 0.15)


def is_upgrade(old: str, new: str) -> bool:
    old_prefix = model_prefix(old)
    new_prefix = model_prefix(new)
    return old_prefix != "" and old_prefix == new_prefix


def model_prefix(model: str) -> str:
    base = (model or "").split(":", 1)[0]
    parts = [part for part in base.split("-") if part and not part[0].isdigit()]
    return "-".join(parts)


def apply_budget(results: list[RetrievedRule], limit: int, token_budget: int | None) -> list[RetrievedRule]:
    if token_budget is None:
        return results[:limit]
    selected: list[RetrievedRule] = []
    used = 0
    for result in results:
        cost = max(1, result.token_cost)
        if selected and len(selected) >= limit:
            break
        if selected and used + cost > token_budget:
            continue
        if not selected and cost > token_budget:
            selected.append(result)
            break
        selected.append(result)
        used += cost
        if len(selected) >= limit:
            break
    return selected
