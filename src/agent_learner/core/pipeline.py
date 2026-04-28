from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .lifecycle import LearningLifecycle
from .models import ComparisonDecisionType, LearningRule, utc_now_iso
from .storage import agent_learner_home, append_jsonl, migrate_local_learning_store_to_global, promotions_history_path, read_jsonl, resolve_learning_root
from .events import LearningEvent, event_storage_dir

RULE_HINT_RE = re.compile(
    r"\b(always|never|prefer|must|should|do not|don't|keep|avoid|ensure|whenever)\b",
    re.IGNORECASE,
)
TEXT_VALUE_KEYS = {
    "prompt",
    "user_prompt",
    "message",
    "text",
    "summary",
    "feedback",
    "instruction",
    "content",
}
COMPARISON_STATUSES = ["approved", "needs_review"]
GENERIC_REJECTION_TERMS = {"careful", "quality", "best", "good", "clean", "helpful", "process", "properly", "appropriate"}
NEGATION_TERMS = {"never", "not", "avoid", "except", "unless", "dont", "no"}
STOPWORDS = {"a", "an", "and", "be", "for", "the", "to", "with", "when", "whenever", "always"}
OPERATIONAL_CONTEXT_TERMS = {
    "debug",
    "debugging",
    "install",
    "installation",
    "runtime",
    "status",
    "message",
    "messages",
    "blocked",
    "completed",
    "operator",
    "triage",
}
TOOLING_NOTE_TERMS = {"omx", "agentlearner", "codex", "claude", "hermit", "channel", "channels", "hook", "hooks"}


@dataclass(slots=True)
class LearningCandidate:
    adapter: str
    source_event_path: str
    captured_at: str
    title: str
    summary: str
    suggested_rule: str
    scope: str
    evidence_excerpt: str
    transcript_path: str | None = None
    repo_id: str | None = None
    repo_root: str | None = None
    worktree_path: str | None = None
    repo_remote_url: str | None = None
    matched_rule: str | None = None
    decision: ComparisonDecisionType | None = None
    decision_reason: str | None = None
    review_required: bool = False
    confidence: str = "low"
    field_diffs: dict[str, str] | None = None


@dataclass(slots=True)
class ProcessedEventResult:
    event_path: str
    status: str
    source_adapter: str | None = None
    candidate_path: str | None = None
    rule_path: str | None = None
    reason: str | None = None
    decision: ComparisonDecisionType | None = None
    matched_rule: str | None = None
    ledger_path: str | None = None
    review_required: bool = False


@dataclass(slots=True)
class CandidateComparison:
    decision: ComparisonDecisionType
    matched_rule: str | None
    confidence: str
    reason: str
    review_required: bool
    field_diffs: dict[str, str]
    similarity: float = 0.0


@dataclass(slots=True)
class CandidateRecord:
    path: Path
    candidate: LearningCandidate
    status: str = "draft_candidate"


def candidate_storage_dir(project_root: Path, adapter: str) -> Path:
    return agent_learner_home() / "candidates" / adapter


def processed_marker_dir(project_root: Path, processor: str, adapter: str) -> Path:
    return agent_learner_home() / "state" / "processed-events" / processor / adapter


def list_candidate_paths(project_root: Path, adapter: str | None = None) -> list[Path]:
    migrate_local_learning_store_to_global(project_root)
    if adapter:
        return sorted(candidate_storage_dir(project_root, adapter).glob("candidate-*.md"))
    root = agent_learner_home() / "candidates"
    paths: list[Path] = []
    for adapter_dir in sorted(root.glob("*")):
        if adapter_dir.is_dir():
            paths.extend(sorted(adapter_dir.glob("candidate-*.md")))
    return sorted(paths)

def load_candidate_record(path: Path) -> CandidateRecord:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(text)
    metadata = parse_frontmatter(frontmatter)
    sections = parse_markdown_sections(body)
    candidate = LearningCandidate(
        adapter=str(metadata.get("adapter") or path.parent.name),
        source_event_path=str(metadata.get("source_event_path") or ""),
        captured_at=str(metadata.get("captured_at") or ""),
        title=path.stem.replace("candidate-", "").replace("-", " "),
        summary=str(sections.get("Summary") or ""),
        suggested_rule=str(sections.get("Suggested rule") or ""),
        scope=str(sections.get("Scope") or ""),
        evidence_excerpt=str(sections.get("Evidence") or ""),
        transcript_path=str(metadata.get("transcript_path") or "") or None,
        repo_id=str(metadata.get("repo_id") or "") or None,
        repo_root=str(metadata.get("repo_root") or "") or None,
        worktree_path=str(metadata.get("worktree_path") or "") or None,
        repo_remote_url=str(metadata.get("repo_remote_url") or "") or None,
        matched_rule=str(metadata.get("matched_rule") or "") or None,
        decision=str(metadata.get("decision") or "") or None,
        decision_reason=str(metadata.get("decision_reason") or "") or None,
        review_required=str(metadata.get("review_required") or "").lower() == "true",
        confidence=str(metadata.get("confidence") or "low"),
        field_diffs=dict(metadata.get("field_diffs") or {}),
    )
    title = str(sections.get("title") or "").strip()
    if title:
        candidate.title = title
    return CandidateRecord(path=path, candidate=candidate, status=str(metadata.get("status") or "draft_candidate"))


def save_candidate_record(record: CandidateRecord) -> Path:
    candidate = record.candidate
    body = [
        "---",
        f"adapter: {candidate.adapter}",
        f"captured_at: {candidate.captured_at}",
        f"source_event_path: {candidate.source_event_path}",
        f"transcript_path: {candidate.transcript_path or ''}",
        f"repo_id: {candidate.repo_id or ''}",
        f"repo_root: {candidate.repo_root or ''}",
        f"worktree_path: {candidate.worktree_path or ''}",
        f"repo_remote_url: {candidate.repo_remote_url or ''}",
        f"status: {record.status}",
        f"decision: {candidate.decision or ''}",
        f"decision_reason: {json.dumps(candidate.decision_reason or '', ensure_ascii=False)}",
        f"matched_rule: {candidate.matched_rule or ''}",
        f"review_required: {'true' if candidate.review_required else 'false'}",
        f"confidence: {candidate.confidence}",
        f"field_diffs: {json.dumps(candidate.field_diffs or {}, ensure_ascii=False)}",
        "---",
        "",
        f"# {candidate.title}",
        "",
        "## Suggested rule",
        candidate.suggested_rule,
        "",
        "## Summary",
        candidate.summary,
        "",
        "## Scope",
        candidate.scope,
        "",
        "## Evidence",
        candidate.evidence_excerpt,
        "",
    ]
    record.path.write_text("\n".join(body), encoding="utf-8")
    return record.path


def list_event_paths(project_root: Path, adapter: str | None = None) -> list[Path]:
    migrate_local_learning_store_to_global(project_root)
    adapters = [adapter] if adapter else [path.name for path in (agent_learner_home() / "events").glob("*") if path.is_dir()]
    paths: list[Path] = []
    for adapter_name in adapters:
        paths.extend(sorted(event_storage_dir(project_root, adapter_name).glob("*.json")))
    return sorted(paths)


def load_learning_event(event_path: Path) -> LearningEvent:
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    return LearningEvent(
        adapter=str(payload["adapter"]),
        event_name=str(payload["event_name"]),
        cwd=str(payload["cwd"]),
        captured_at=str(payload["captured_at"]),
        session_id=payload.get("session_id"),
        transcript_path=payload.get("transcript_path"),
        payload=dict(payload.get("payload") or {}),
        repo_id=str(payload.get("repo_id") or "") or None,
        repo_root=str(payload.get("repo_root") or "") or None,
        worktree_path=str(payload.get("worktree_path") or "") or None,
        repo_remote_url=str(payload.get("repo_remote_url") or "") or None,
    )


def is_processed(project_root: Path, event_path: Path, processor: str = "extract") -> bool:
    marker = processed_marker_dir(project_root, processor, event_path.parent.name) / f"{event_path.stem}.done"
    return marker.exists()


def mark_processed(project_root: Path, event_path: Path, processor: str = "extract") -> Path:
    marker = processed_marker_dir(project_root, processor, event_path.parent.name) / f"{event_path.stem}.done"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(event_path.name + "\n", encoding="utf-8")
    return marker


def process_unprocessed_events(project_root: Path, adapter: str | None = None, limit: int | None = None) -> list[ProcessedEventResult]:
    migrate_local_learning_store_to_global(project_root)
    results: list[ProcessedEventResult] = []
    lifecycle = LearningLifecycle(resolve_learning_root(project_root))
    lifecycle.cleanup_drafts()
    for event_path in list_event_paths(project_root, adapter=adapter):
        if limit is not None and len(results) >= limit:
            break
        if is_processed(project_root, event_path):
            continue
        event = load_learning_event(event_path)
        candidate = extract_candidate_from_event(project_root, event_path, event)
        candidate_path: Path | None = None
        rule_path: Path | None = None
        ledger_path: Path | None = None
        comparison: CandidateComparison | None = None
        if candidate is not None:
            comparison = compare_candidate_to_existing_rule(project_root, lifecycle, candidate)
            candidate.decision = comparison.decision
            candidate.matched_rule = comparison.matched_rule
            candidate.decision_reason = comparison.reason
            candidate.review_required = comparison.review_required
            candidate.confidence = comparison.confidence
            candidate.field_diffs = comparison.field_diffs
            candidate_path = write_candidate(project_root, candidate)
            ledger_path = append_candidate_decision_entry(project_root, candidate, comparison)
            if comparison.decision == "refresh_existing" and comparison.matched_rule:
                existing_rule = lifecycle.load_rule(comparison.matched_rule)
                if comparison.review_required:
                    status = "candidate_written"
                else:
                    refreshed_path = lifecycle.refresh(
                        comparison.matched_rule,
                        status_override="approved" if existing_rule.status == "needs_review" else None,
                        source_event=candidate.source_event_path,
                        source_adapter=candidate.adapter,
                        derived_from_candidate=f"candidate-{slugify(candidate.title)}.md",
                        decision_reason=comparison.reason,
                        evidence_excerpt=candidate.evidence_excerpt,
                    )
                    rule_path = refreshed_path
                    status = "rule_reapproved" if existing_rule.status == "needs_review" else "rule_refreshed"
                    comparison.matched_rule = refreshed_path.stem
                    comparison.review_required = False
                    candidate.matched_rule = refreshed_path.stem
                    update_candidate_status(
                        candidate_path,
                        "auto_applied",
                        matched_rule=refreshed_path.stem,
                        review_required=False,
                        confidence=comparison.confidence,
                    )
            elif comparison.decision == "reject_candidate":
                status = "candidate_rejected"
                update_candidate_status(candidate_path, "rejected_candidate", review_required=False, confidence=comparison.confidence)
            elif comparison.decision == "revise_existing" and comparison.matched_rule:
                existing_rule = lifecycle.load_rule(comparison.matched_rule)
                if comparison.review_required:
                    status = "candidate_written"
                else:
                    revised_path = lifecycle.revise(
                        comparison.matched_rule,
                        rule_text=candidate.suggested_rule,
                        summary=candidate.summary,
                        scope=candidate.scope,
                        why=comparison.reason,
                        status_override="approved" if existing_rule.status == "needs_review" else None,
                        source_event=candidate.source_event_path,
                        source_adapter=candidate.adapter,
                        derived_from_candidate=f"candidate-{slugify(candidate.title)}.md",
                        decision_reason=comparison.reason,
                        evidence_excerpt=candidate.evidence_excerpt,
                    )
                    rule_path = revised_path
                    status = "rule_reapproved" if existing_rule.status == "needs_review" else "rule_revised"
                    comparison.matched_rule = revised_path.stem
                    candidate.review_required = False
                    comparison.review_required = False
                    candidate.matched_rule = revised_path.stem
                    update_candidate_status(
                        candidate_path,
                        "auto_applied",
                        matched_rule=revised_path.stem,
                        review_required=False,
                        confidence=comparison.confidence,
                    )
            elif comparison.decision in {"new_rule", "fork_rule"}:
                if comparison.review_required:
                    status = "candidate_written"
                else:
                    promoted_path = auto_promote_candidate_as_rule(project_root, lifecycle, candidate, comparison, candidate_path)
                    rule_path = promoted_path
                    status = "rule_promoted" if comparison.decision == "new_rule" else "rule_forked"
                    comparison.matched_rule = promoted_path.stem
                    candidate.review_required = False
                    comparison.review_required = False
                    candidate.matched_rule = promoted_path.stem
                    update_candidate_status(
                        candidate_path,
                        "auto_applied",
                        matched_rule=promoted_path.stem,
                        review_required=False,
                        confidence=comparison.confidence,
                    )
            else:
                status = "candidate_written"
        else:
            status = "no_candidate"
        mark_processed(project_root, event_path)
        results.append(
            ProcessedEventResult(
                event_path=str(event_path),
                status=status,
                source_adapter=event.adapter,
                candidate_path=str(candidate_path) if candidate_path else None,
                rule_path=str(rule_path) if rule_path else None,
                reason=None if candidate is not None else "no durable rule-like signal found",
                decision=comparison.decision if comparison else None,
                matched_rule=comparison.matched_rule if comparison else None,
                ledger_path=str(ledger_path) if ledger_path else None,
                review_required=comparison.review_required if comparison else False,
            )
        )
    return results


def extract_candidate_from_event(project_root: Path, event_path: Path, event: LearningEvent) -> LearningCandidate | None:
    corpus = build_event_corpus(project_root, event)
    if not corpus.strip():
        return None
    evidence = find_rule_like_excerpt(corpus)
    if not evidence:
        return None
    title = build_candidate_title(event, evidence)
    summary = compact_text(evidence, 160)
    suggested_rule = normalize_rule_text(evidence)
    return LearningCandidate(
        adapter=event.adapter,
        source_event_path=str(event_path),
        captured_at=event.captured_at,
        title=title,
        summary=summary,
        suggested_rule=suggested_rule,
        scope=f"{event.adapter} adapter event:{event.event_name}",
        evidence_excerpt=compact_text(evidence, 260),
        transcript_path=event.transcript_path,
        repo_id=event.repo_id,
        repo_root=event.repo_root,
        worktree_path=event.worktree_path,
        repo_remote_url=event.repo_remote_url,
    )


def write_candidate(project_root: Path, candidate: LearningCandidate) -> Path:
    target_dir = candidate_storage_dir(project_root, candidate.adapter)
    target_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(candidate.title)
    target = target_dir / f"candidate-{slug}.md"
    return save_candidate_record(CandidateRecord(path=target, candidate=candidate))


def update_candidate_status(
    path: Path | None,
    status: str,
    *,
    matched_rule: str | None = None,
    review_required: bool | None = None,
    confidence: str | None = None,
) -> Path | None:
    if path is None or not path.exists():
        return path
    record = load_candidate_record(path)
    record.status = status
    if matched_rule:
        record.candidate.matched_rule = matched_rule
    if review_required is not None:
        record.candidate.review_required = review_required
    if confidence is not None:
        record.candidate.confidence = confidence
    return save_candidate_record(record)


def compare_candidate_to_existing_rule(project_root: Path, lifecycle: LearningLifecycle, candidate: LearningCandidate) -> CandidateComparison:
    if should_reject_candidate(candidate):
        return CandidateComparison(
            decision="reject_candidate",
            matched_rule=None,
            confidence="high",
            reason="candidate signal is too generic to become a durable rule",
            review_required=False,
            field_diffs={},
            similarity=0.0,
        )
    operational_note = candidate_is_operational_tooling_note(candidate)
    repeated_signal = candidate_repeat_signal_count(project_root, candidate) >= 1

    best_rule: LearningRule | None = None
    best_similarity = 0.0
    best_exact = False
    candidate_slug = slugify(candidate.title)
    for path in lifecycle.list_rule_paths(statuses=COMPARISON_STATUSES):
        rule = lifecycle.load_rule(path)
        exact = slugify(rule.name) == candidate_slug
        similarity = rule_similarity(candidate, rule)
        if exact and not best_exact:
            best_rule = rule
            best_similarity = similarity
            best_exact = True
            continue
        if exact == best_exact and similarity > best_similarity:
            best_rule = rule
            best_similarity = similarity

    if best_rule is None:
        strong_new_rule = candidate_is_strong_new_rule(candidate)
        return CandidateComparison(
            decision="new_rule",
            matched_rule=None,
            confidence="high" if strong_new_rule and (not operational_note or repeated_signal) else "medium",
            reason="no existing rule had a meaningful semantic match and the candidate is specific enough to auto-approve"
            if strong_new_rule and not operational_note
            else "no existing rule had a meaningful semantic match",
            review_required=not strong_new_rule or (operational_note and not repeated_signal),
            field_diffs={},
            similarity=0.0,
        )

    diffs = describe_field_diffs(candidate, best_rule)
    conflict = has_negation_conflict(candidate.suggested_rule, best_rule.rule)
    resolves_needs_review = best_rule.status == "needs_review" and (best_exact or best_similarity >= 0.55) and not conflict
    if (best_exact or best_similarity >= 0.82) and not conflict and diffs["rule"] == "unchanged" and diffs["scope"] == "unchanged":
        return CandidateComparison(
            decision="refresh_existing",
            matched_rule=best_rule.name,
            confidence="high",
            reason="same imperative meaning with unchanged scope and fresher evidence"
            if best_rule.status != "needs_review"
            else "needs_review rule confirmed by matching evidence and can return to approved",
            review_required=False,
            field_diffs=diffs,
            similarity=best_similarity,
        )
    if (best_exact or best_similarity >= 0.55) and not conflict:
        return CandidateComparison(
            decision="revise_existing",
            matched_rule=best_rule.name,
            confidence="high" if resolves_needs_review else "medium",
            reason="needs_review rule clarified by stronger evidence and can return to approved"
            if resolves_needs_review
            else "same conceptual rule but durable wording should change materially",
            review_required=not resolves_needs_review,
            field_diffs=diffs,
            similarity=best_similarity,
        )
    if best_similarity >= 0.45:
        strong_fork_rule = candidate_is_strong_fork_rule(candidate, best_rule, diffs, best_similarity, conflict)
        return CandidateComparison(
            decision="fork_rule",
            matched_rule=best_rule.name,
            confidence="high" if strong_fork_rule and (not operational_note or repeated_signal) else "medium",
            reason="related topic overlaps with an existing rule but the conflict is clear enough to auto-fork safely"
            if strong_fork_rule and not operational_note
            else "related topic overlaps with an existing rule but safe merge is not possible",
            review_required=not strong_fork_rule or (operational_note and not repeated_signal),
            field_diffs=diffs,
            similarity=best_similarity,
        )
    return CandidateComparison(
        decision="new_rule",
        matched_rule=None,
        confidence="medium",
        reason="existing rules are too distant to reuse safely",
        review_required=True,
        field_diffs={},
        similarity=best_similarity,
    )


def append_candidate_decision_entry(project_root: Path, candidate: LearningCandidate, comparison: CandidateComparison) -> Path:
    payload = {
        "ts": utc_now_iso(),
        "action": decision_to_history_action(comparison.decision),
        "rule": comparison.matched_rule or slugify(candidate.title),
        "source_adapter": candidate.adapter,
        "source_event": candidate.source_event_path,
        "derived_from_candidate": f"candidate-{slugify(candidate.title)}.md",
        "reason": comparison.reason,
        "decision": comparison.decision,
        "confidence": comparison.confidence,
        "review_required": comparison.review_required,
        "matched_rule": comparison.matched_rule,
        "similarity": round(comparison.similarity, 3),
        "field_diffs": comparison.field_diffs,
        "field_diffs_summary": summarize_field_diffs(comparison.field_diffs),
    }
    return append_jsonl(promotions_history_path(project_root), payload)


def append_candidate_review_entry(
    project_root: Path,
    record: CandidateRecord,
    action: str,
    *,
    rule_name: str | None = None,
    reason: str | None = None,
) -> Path:
    payload = {
        "ts": utc_now_iso(),
        "action": action,
        "rule": rule_name or record.candidate.matched_rule or slugify(record.candidate.title),
        "source_adapter": record.candidate.adapter,
        "source_event": record.candidate.source_event_path,
        "derived_from_candidate": record.path.name,
        "reason": reason or record.candidate.decision_reason or "",
        "decision": record.candidate.decision,
        "review_required": record.candidate.review_required,
        "matched_rule": record.candidate.matched_rule,
        "field_diffs": record.candidate.field_diffs or {},
        "field_diffs_summary": summarize_field_diffs(record.candidate.field_diffs or {}),
    }
    return append_jsonl(promotions_history_path(project_root), payload)


def auto_promote_candidate_as_rule(
    project_root: Path,
    lifecycle: LearningLifecycle,
    candidate: LearningCandidate,
    comparison: CandidateComparison,
    candidate_path: Path | None,
) -> Path:
    rule_name = auto_rule_name(lifecycle, candidate, comparison)
    rule = LearningRule(
        name=rule_name,
        rule=candidate.suggested_rule,
        why=comparison.reason,
        scope=candidate.scope,
        good_pattern=candidate.summary or candidate.suggested_rule,
        avoid_pattern="",
        summary=candidate.summary or candidate.suggested_rule,
    )
    rule.source_event = candidate.source_event_path
    rule.source_adapter = candidate.adapter
    rule.derived_from_candidate = f"candidate-{slugify(candidate.title)}.md"
    rule.decision = comparison.decision
    rule.decision_reason = comparison.reason
    rule.evidence_excerpt = candidate.evidence_excerpt
    rule.evidence = candidate.evidence_excerpt
    rule.source_project = candidate.repo_root or project_root.name
    rule.repo_id = candidate.repo_id
    rule.repo_root = candidate.repo_root
    rule.worktree_path = candidate.worktree_path
    rule.repo_remote_url = candidate.repo_remote_url
    if candidate.repo_id:
        rule.projects = [candidate.repo_id]
    if comparison.decision == "fork_rule" and comparison.matched_rule:
        rule.related_rule = comparison.matched_rule
    saved = lifecycle.promote(rule)
    record = CandidateRecord(path=candidate_path or Path(f"candidate-{slugify(candidate.title)}.md"), candidate=candidate, status="auto_applied")
    append_candidate_review_entry(project_root, record, "promote", rule_name=saved.stem, reason=comparison.reason)
    return saved


def auto_rule_name(lifecycle: LearningLifecycle, candidate: LearningCandidate, comparison: CandidateComparison) -> str:
    base = canonical_rule_slug(candidate)
    if comparison.decision == "fork_rule" and comparison.matched_rule:
        base = f"{comparison.matched_rule}-fork-{candidate.adapter}"
    candidate_name = base
    counter = 2
    while True:
        try:
            lifecycle.resolve_rule_path(candidate_name)
        except FileNotFoundError:
            return candidate_name
        candidate_name = f"{base}-{counter}"
        counter += 1


def summarize_field_diffs(field_diffs: dict[str, str]) -> str:
    if not field_diffs:
        return "none"
    parts = [f"{key}:{value}" for key, value in sorted(field_diffs.items()) if value != "unchanged"]
    return ", ".join(parts) if parts else "unchanged"


def approve_candidate(project_root: Path, candidate_ref: str | Path) -> tuple[CandidateRecord, Path]:
    record = resolve_candidate_record(project_root, candidate_ref)
    lifecycle = LearningLifecycle(resolve_learning_root(project_root))
    if record.status in {"auto_applied", "approved_candidate"} and record.candidate.matched_rule:
        resolved = lifecycle.resolve_rule_path(record.candidate.matched_rule)
        return record, resolved
    rule_name = record.candidate.matched_rule or slugify(record.candidate.title)
    existing_path = None
    try:
        existing_path = lifecycle.resolve_rule_path(rule_name)
    except FileNotFoundError:
        existing_path = None

    if record.candidate.decision == "refresh_existing" and existing_path is not None:
        saved = lifecycle.refresh(
            existing_path,
            source_event=record.candidate.source_event_path,
            source_adapter=record.candidate.adapter,
            derived_from_candidate=record.path.name,
            decision_reason=record.candidate.decision_reason,
            evidence_excerpt=record.candidate.evidence_excerpt,
        )
        record.status = "approved_candidate"
        save_candidate_record(record)
        append_candidate_review_entry(project_root, record, "refresh", rule_name=saved.stem)
        return record, saved

    if existing_path is not None:
        rule = lifecycle.load_rule(existing_path)
    else:
        rule = LearningRule(
            name=rule_name,
            rule=record.candidate.suggested_rule,
            why=record.candidate.decision_reason or "Approved from candidate review.",
            scope=record.candidate.scope,
            good_pattern=record.candidate.summary or record.candidate.suggested_rule,
            avoid_pattern="",
            summary=record.candidate.summary or record.candidate.suggested_rule,
        )

    rule.name = rule_name
    rule.rule = record.candidate.suggested_rule
    rule.summary = record.candidate.summary or record.candidate.suggested_rule
    rule.scope = record.candidate.scope
    rule.why = record.candidate.decision_reason or rule.why or "Approved from candidate review."
    rule.source_event = record.candidate.source_event_path
    rule.source_adapter = record.candidate.adapter
    rule.derived_from_candidate = record.path.name
    rule.decision = record.candidate.decision
    rule.decision_reason = record.candidate.decision_reason
    rule.evidence_excerpt = record.candidate.evidence_excerpt
    rule.evidence = record.candidate.evidence_excerpt
    rule.source_project = record.candidate.repo_root or project_root.name
    rule.repo_id = record.candidate.repo_id
    rule.repo_root = record.candidate.repo_root
    rule.worktree_path = record.candidate.worktree_path
    rule.repo_remote_url = record.candidate.repo_remote_url
    if record.candidate.repo_id:
        rule.projects = [record.candidate.repo_id]
    if existing_path is not None and record.candidate.decision == "revise_existing":
        rule.supersedes = rule_name

    saved = lifecycle.promote(rule)
    record.status = "approved_candidate"
    save_candidate_record(record)
    append_candidate_review_entry(project_root, record, "promote", rule_name=saved.stem)
    return record, saved


def reject_candidate(project_root: Path, candidate_ref: str | Path, *, reason: str | None = None) -> CandidateRecord:
    record = resolve_candidate_record(project_root, candidate_ref)
    record.status = "rejected_candidate"
    if reason:
        record.candidate.decision_reason = reason
    save_candidate_record(record)
    append_candidate_review_entry(project_root, record, "reject_candidate", reason=reason)
    return record


def mark_candidate_needs_review(project_root: Path, candidate_ref: str | Path, *, reason: str | None = None) -> CandidateRecord:
    record = resolve_candidate_record(project_root, candidate_ref)
    record.status = "needs_review_candidate"
    if reason:
        record.candidate.decision_reason = reason
    save_candidate_record(record)
    append_candidate_review_entry(project_root, record, "mark_needs_review", reason=reason)
    return record


def resolve_candidate_record(project_root: Path, candidate_ref: str | Path) -> CandidateRecord:
    candidate_path = Path(candidate_ref)
    if candidate_path.exists():
        return load_candidate_record(candidate_path)
    reference = str(candidate_ref).strip()
    for path in list_candidate_paths(project_root):
        if path.name == reference or path.stem == reference or path.stem == f"candidate-{slugify(reference)}":
            return load_candidate_record(path)
    raise FileNotFoundError(f"candidate not found: {candidate_ref}")


def decision_to_history_action(decision: ComparisonDecisionType) -> str:
    if decision == "new_rule":
        return "candidate_created"
    if decision == "refresh_existing":
        return "refresh"
    if decision == "revise_existing":
        return "revise"
    if decision == "fork_rule":
        return "candidate_created"
    return "reject_candidate"


def should_reject_candidate(candidate: LearningCandidate) -> bool:
    tokens = tokenize_for_compare(candidate.suggested_rule)
    useful = [token for token in tokens if token not in GENERIC_REJECTION_TERMS and token not in STOPWORDS]
    return len(useful) < 2


def candidate_specificity_score(candidate: LearningCandidate) -> int:
    useful = [token for token in tokenize_for_compare(candidate.suggested_rule) if token not in GENERIC_REJECTION_TERMS and token not in STOPWORDS]
    scope_tokens = tokenize_for_compare(candidate.scope)
    evidence_tokens = tokenize_for_compare(candidate.evidence_excerpt)
    score = len(set(useful))
    if len(scope_tokens) >= 3:
        score += 2
    if len(evidence_tokens) >= 6:
        score += 2
    if candidate.summary and len(candidate.summary.split()) >= 5:
        score += 1
    return score


def candidate_is_strong_new_rule(candidate: LearningCandidate) -> bool:
    return candidate_specificity_score(candidate) >= 7


def candidate_is_strong_fork_rule(
    candidate: LearningCandidate,
    rule: LearningRule,
    diffs: dict[str, str],
    similarity: float,
    conflict: bool,
) -> bool:
    if not conflict:
        return False
    if similarity < 0.45:
        return False
    if diffs.get("scope") not in {"unchanged", "broadened", "narrowed"}:
        return False
    return candidate_specificity_score(candidate) >= 7 and len(tokenize_for_compare(rule.rule)) >= 3


def canonical_rule_slug(candidate: LearningCandidate) -> str:
    title_slug = slugify(candidate.title)
    if title_slug and not title_slug.startswith(("learned-rule-draft", "session-learning", "candidate")):
        return title_slug
    summary_slug = slugify(candidate.summary)
    if summary_slug and not summary_slug.startswith(("learned-rule-draft", "session-learning", "candidate")):
        return summary_slug
    rule_slug = slugify(candidate.suggested_rule)
    if rule_slug and not rule_slug.startswith(("learned-rule-draft", "session-learning", "candidate")):
        return rule_slug
    return title_slug or summary_slug or rule_slug or "learning-rule"


def candidate_is_operational_tooling_note(candidate: LearningCandidate) -> bool:
    tokens = set(tokenize_for_compare(" ".join([candidate.suggested_rule, candidate.summary, candidate.evidence_excerpt])))
    return bool(tokens & OPERATIONAL_CONTEXT_TERMS) and bool(tokens & TOOLING_NOTE_TERMS)


def candidate_repeat_signal_count(project_root: Path, candidate: LearningCandidate) -> int:
    target_slug = canonical_rule_slug(candidate)
    candidate_name = f"candidate-{slugify(candidate.title)}.md"
    count = 0
    for entry in read_jsonl(promotions_history_path(project_root)):
        if str(entry.get("rule") or "") == target_slug:
            count += 1
            continue
        if str(entry.get("derived_from_candidate") or "") == candidate_name:
            count += 1
    return count


def describe_field_diffs(candidate: LearningCandidate, rule: LearningRule) -> dict[str, str]:
    return {
        "rule": classify_text_diff(candidate.suggested_rule, rule.rule),
        "summary": classify_text_diff(candidate.summary, rule.summary or rule.rule),
        "scope": classify_text_diff(candidate.scope, rule.scope),
        "evidence": "updated_evidence" if normalize_compare_text(candidate.evidence_excerpt) != normalize_compare_text(rule.evidence_excerpt or rule.evidence or "") else "unchanged",
    }


def classify_text_diff(left: str, right: str) -> str:
    normalized_left = normalize_compare_text(left)
    normalized_right = normalize_compare_text(right)
    if normalized_left == normalized_right:
        return "unchanged"
    if semantic_rule_text_equivalent(left, right):
        return "unchanged"
    left_tokens = tokenize_for_compare(left)
    right_tokens = tokenize_for_compare(right)
    if set(left_tokens).issubset(set(right_tokens)):
        return "narrowed"
    if set(right_tokens).issubset(set(left_tokens)):
        return "broadened"
    if has_negation_conflict(left, right):
        return "contradicted"
    return "rewritten"


def rule_similarity(candidate: LearningCandidate, rule: LearningRule) -> float:
    if semantic_rule_text_equivalent(candidate.suggested_rule, rule.rule):
        return 0.9
    candidate_tokens = set(tokenize_for_compare(" ".join([candidate.suggested_rule, candidate.summary, candidate.scope])))
    rule_tokens = set(tokenize_for_compare(" ".join([rule.rule, rule.summary, rule.scope, " ".join(rule.triggers), " ".join(rule.task_types)])))
    if not candidate_tokens or not rule_tokens:
        return 0.0
    overlap = len(candidate_tokens & rule_tokens)
    union = len(candidate_tokens | rule_tokens)
    similarity = overlap / union if union else 0.0
    candidate_core = imperative_signature_tokens(candidate.suggested_rule)
    rule_core = imperative_signature_tokens(rule.rule)
    if candidate_core and rule_core and candidate_core[0] == rule_core[0] and candidate_core[-2:] == rule_core[-2:]:
        candidate_middle = set(candidate_core[1:-2])
        rule_middle = set(rule_core[1:-2])
        if candidate_middle and rule_middle and candidate_middle.isdisjoint(rule_middle):
            return min(similarity, 0.44)
    return similarity


def semantic_rule_text_equivalent(left: str, right: str) -> bool:
    left_signature = imperative_signature_tokens(left)
    right_signature = imperative_signature_tokens(right)
    if len(left_signature) < 3 or len(right_signature) < 3:
        return False
    if left_signature[0] != right_signature[0]:
        return False
    if left_signature[-2:] != right_signature[-2:]:
        return False
    return has_contextual_pronoun_or_lead_in(left) or has_contextual_pronoun_or_lead_in(right)


def has_contextual_pronoun_or_lead_in(text: str) -> bool:
    normalized = compact_text(text, 220)
    clause = extract_imperative_clause(text)
    if clause != normalized:
        return True
    return any(token in {"them", "it", "this", "that", "these", "those"} for token in tokenize_for_compare(clause))


def imperative_signature_tokens(text: str) -> list[str]:
    clause = extract_imperative_clause(text)
    raw_tokens = tokenize_for_compare(clause)
    return [token for token in raw_tokens if token not in STOPWORDS and token not in GENERIC_REJECTION_TERMS and token not in {"them", "it", "this", "that", "these", "those"}]


LEAD_IN_CONDITION_TERMS = {"when", "while", "if", "after", "before", "during", "once"}


def extract_imperative_clause(text: str) -> str:
    cleaned = compact_text(text, 220)
    if not cleaned:
        return cleaned
    prefix, separator, suffix = cleaned.partition(",")
    prefix_tokens = tokenize_for_compare(prefix)
    if separator and prefix_tokens and prefix_tokens[0] in LEAD_IN_CONDITION_TERMS:
        return suffix.strip() or cleaned
    return cleaned


def has_negation_conflict(left: str, right: str) -> bool:
    left_negated = any(term in tokenize_for_compare(left) for term in NEGATION_TERMS)
    right_negated = any(term in tokenize_for_compare(right) for term in NEGATION_TERMS)
    return left_negated != right_negated


def normalize_compare_text(text: str) -> str:
    normalized = " ".join(text.lower().split())
    return re.sub(r"[^a-z0-9\s]", "", normalized)


def tokenize_for_compare(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalize_compare_text(text))


def split_frontmatter(text: str) -> tuple[str, str]:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end >= 0:
            return text[4:end], text[end + 5 :]
    return "", text


def parse_frontmatter(text: str) -> dict[str, str]:
    metadata: dict[str, object] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parsed = value.strip()
        if (parsed.startswith('"') and parsed.endswith('"')) or (parsed.startswith("{") and parsed.endswith("}")) or (parsed.startswith("[") and parsed.endswith("]")):
            try:
                parsed = json.loads(parsed)
            except json.JSONDecodeError:
                parsed = parsed.strip('"')
        metadata[key.strip()] = parsed
    return metadata


def parse_markdown_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    title = ""
    current: str | None = None
    lines: list[str] = []
    for raw_line in text.splitlines():
        if raw_line.startswith("# ") and not title:
            title = raw_line[2:].strip()
            continue
        if raw_line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(lines).strip()
            current = raw_line[3:].strip()
            lines = []
            continue
        lines.append(raw_line)
    if current is not None:
        sections[current] = "\n".join(lines).strip()
    if title:
        sections["title"] = title
    return sections


def build_event_corpus(project_root: Path, event: LearningEvent) -> str:
    parts: list[str] = []
    parts.extend(extract_text_values(event.payload))
    transcript_path = resolve_transcript_path(project_root, event)
    if transcript_path and transcript_path.exists():
        parts.append(read_transcript_text(transcript_path))
    return "\n".join(part for part in parts if part.strip())


def resolve_transcript_path(project_root: Path, event: LearningEvent) -> Path | None:
    if not event.transcript_path:
        return None
    transcript = Path(event.transcript_path)
    if transcript.is_absolute():
        return transcript
    return project_root / transcript


def extract_text_values(payload: dict[str, object]) -> list[str]:
    values: list[str] = []
    for key, value in payload.items():
        if isinstance(value, str) and (key in TEXT_VALUE_KEYS or len(value.split()) > 3):
            values.append(value)
        elif isinstance(value, dict):
            values.extend(extract_text_values(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and len(item.split()) > 3:
                    values.append(item)
                elif isinstance(item, dict):
                    values.extend(extract_text_values(item))
    return values


def read_transcript_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        lines: list[str] = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                lines.append(stripped)
                continue
            if isinstance(payload, dict):
                lines.extend(extract_text_values(payload))
        return "\n".join(lines)
    if path.suffix == ".json":
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        lines = extract_transcript_messages(payload)
        return "\n".join(line for line in lines if line.strip())
    return raw


def extract_transcript_messages(payload: object) -> list[str]:
    if isinstance(payload, list):
        lines: list[str] = []
        for item in payload:
            lines.extend(extract_transcript_messages(item))
        return lines
    if not isinstance(payload, dict):
        return []

    role = str(payload.get("role") or "").strip().lower()
    lines: list[str] = []
    if role in {"user", "assistant"}:
        lines.extend(extract_transcript_content(payload.get("content")))
        lines.extend(extract_transcript_messages(payload.get("codex_message_items")))
        return lines

    for key in ("messages", "conversation", "history", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            lines.extend(extract_transcript_messages(value))
    return lines


def extract_transcript_content(value: object) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        lines: list[str] = []
        for item in value:
            lines.extend(extract_transcript_content(item))
        return lines
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str) and text.strip():
            return [text]
        for key in ("content", "parts"):
            nested = value.get(key)
            if nested is not None:
                return extract_transcript_content(nested)
    return []


def find_rule_like_excerpt(corpus: str) -> str | None:
    for chunk in split_corpus(corpus):
        if RULE_HINT_RE.search(chunk):
            return chunk
    return None


def split_corpus(corpus: str) -> list[str]:
    normalized = corpus.replace("\r", "\n")
    pieces = re.split(r"[\n.!?]+", normalized)
    return [compact_text(piece, 260) for piece in pieces if piece.strip()]


def compact_text(text: str, limit: int) -> str:
    normalized = " ".join(text.split())
    return normalized if len(normalized) <= limit else normalized[: limit - 3].rstrip() + "..."


def normalize_rule_text(text: str) -> str:
    cleaned = compact_text(text, 180)
    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned[:1].upper() + cleaned[1:] if cleaned else cleaned


def build_candidate_title(event: LearningEvent, evidence: str) -> str:
    core = evidence.lower()
    for prefix in ["always ", "never ", "prefer ", "must ", "should ", "do not ", "don't ", "keep ", "avoid ", "ensure ", "whenever "]:
        if core.startswith(prefix):
            core = core[len(prefix):]
            break
    words = [word for word in re.findall(r"[a-z0-9]+", core) if word not in {"the", "a", "an", "and", "or", "to", "of", "for", "with", "when"}]
    if not words:
        words = [event.adapter, event.event_name, "learning"]
    return " ".join(words[:6])


def slugify(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return "-".join(words[:8]) or "learning-candidate"


def processed_results_as_json(results: list[ProcessedEventResult]) -> str:
    return json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2)


def processed_results_as_text(results: list[ProcessedEventResult]) -> str:
    if not results:
        return "No new unprocessed events found."
    lines = []
    for result in results:
        line = f"- {result.status}: {result.event_path}"
        if result.candidate_path:
            line += f" -> {result.candidate_path}"
        elif result.reason:
            line += f" ({result.reason})"
        if result.decision:
            line += f" [decision={result.decision}]"
        if result.matched_rule:
            line += f" [matched_rule={result.matched_rule}]"
        lines.append(line)
    return "\n".join(lines)
