import json
from pathlib import Path

from agent_learner.core.events import build_learning_event, write_learning_event
from agent_learner.core.lifecycle import LearningLifecycle
from agent_learner.core.models import LearningRule
from agent_learner.core.pipeline import (
    extract_candidate_from_event,
    is_processed,
    load_learning_event,
    load_candidate_record,
    process_unprocessed_events,
)


def promote_rule(tmp_path: Path, **overrides: object) -> None:
    lifecycle = LearningLifecycle(tmp_path / ".agent-learner" / "learning")
    rule = LearningRule(
        name=str(overrides.pop("name", "existing-rule")),
        rule=str(overrides.pop("rule", "Update tests whenever behavior changes.")),
        why=str(overrides.pop("why", "Verification should track behavior changes.")),
        scope=str(overrides.pop("scope", "codex adapter event:stop")),
        good_pattern=str(overrides.pop("good_pattern", "Edit code and tests together.")),
        avoid_pattern=str(overrides.pop("avoid_pattern", "Ship behavior changes without tests.")),
        summary=str(overrides.pop("summary", "Keep tests aligned with behavior changes.")),
        evidence=str(overrides.pop("evidence", "Older evidence")),
    )
    for key, value in overrides.items():
        setattr(rule, key, value)
    lifecycle.promote(rule)


def test_process_events_extracts_candidate_from_transcript_and_marks_processed(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(json.dumps({"message": "Always keep learned rules short and reusable."}) + "\n", encoding="utf-8")
    event_path = write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="claude",
            event_name="session_end",
            cwd=str(tmp_path),
            session_id="abc123",
            transcript_path=str(transcript),
            payload={"message": "session ended"},
        ),
    )

    results = process_unprocessed_events(tmp_path, adapter="claude")
    assert len(results) == 1
    assert results[0].status == "rule_promoted"
    assert results[0].candidate_path is not None
    assert results[0].rule_path is not None
    candidate_path = Path(results[0].candidate_path)
    assert candidate_path.exists()
    content = candidate_path.read_text(encoding="utf-8")
    assert "Always keep learned rules short and reusable." in content
    candidate_record = load_candidate_record(candidate_path)
    assert candidate_record.status == "auto_applied"
    assert candidate_record.candidate.review_required is False
    assert candidate_record.candidate.confidence == "high"
    assert is_processed(tmp_path, event_path)

    second = process_unprocessed_events(tmp_path, adapter="claude")
    assert second == []


def test_extract_candidate_returns_none_without_rule_signal(tmp_path: Path) -> None:
    event_path = write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="codex",
            event_name="stop",
            cwd=str(tmp_path),
            session_id="codex-1",
            payload={"message": "session complete", "stats": {"files": 3}},
        ),
    )
    event = load_learning_event(event_path)
    candidate = extract_candidate_from_event(tmp_path, event_path, event)
    assert candidate is None


def test_process_events_refreshes_existing_rule_and_writes_ledger(tmp_path: Path) -> None:
    promote_rule(
        tmp_path,
        name="keep-tests-aligned",
        rule="Always keep learned rules short and reusable.",
        summary="Always keep learned rules short and reusable.",
        scope="claude adapter event:session_end",
        evidence="Older evidence",
    )
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(json.dumps({"message": "Always keep learned rules short and reusable."}) + "\n", encoding="utf-8")
    write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="claude",
            event_name="session_end",
            cwd=str(tmp_path),
            session_id="refresh-1",
            transcript_path=str(transcript),
            payload={"message": "Always keep learned rules short and reusable."},
        ),
    )

    results = process_unprocessed_events(tmp_path, adapter="claude")
    assert results[0].status == "rule_refreshed"
    assert results[0].decision == "refresh_existing"
    assert results[0].candidate_path is not None
    ledger = (tmp_path / ".agent-learner" / "history" / "promotions.jsonl").read_text(encoding="utf-8")
    assert '"action": "refresh"' in ledger

    lifecycle = LearningLifecycle(tmp_path / ".agent-learner" / "learning")
    refreshed = lifecycle.load_rule("keep-tests-aligned")
    assert refreshed.refresh_count == 1
    assert refreshed.decision == "refresh_existing"
    assert refreshed.source_adapter == "claude"
    assert refreshed.derived_from_candidate is not None


def test_process_events_marks_revision_candidate_with_review_required(tmp_path: Path) -> None:
    promote_rule(
        tmp_path,
        name="update-tests",
        rule="Update tests whenever behavior changes.",
        summary="Update tests whenever behavior changes.",
        scope="codex adapter event:stop",
    )
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(json.dumps({"message": "Always update tests whenever behavior changes in shared workflows and service-level changes."}) + "\n", encoding="utf-8")
    write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="codex",
            event_name="stop",
            cwd=str(tmp_path),
            session_id="revise-1",
            transcript_path=str(transcript),
            payload={"message": "Always update tests whenever behavior changes in shared workflows and service-level changes."},
        ),
    )

    results = process_unprocessed_events(tmp_path, adapter="codex")
    assert results[0].status == "rule_revised"
    assert results[0].decision == "revise_existing"
    assert results[0].matched_rule == "update-tests"
    assert results[0].review_required is False
    candidate_path = Path(results[0].candidate_path or "")
    assert candidate_path.exists()
    content = candidate_path.read_text(encoding="utf-8")
    assert "decision: revise_existing" in content
    lifecycle = LearningLifecycle(tmp_path / ".agent-learner" / "learning")
    revised = lifecycle.load_rule("update-tests")
    assert revised.decision == "revise_existing"
    assert revised.supersedes is not None
    ledger = (tmp_path / ".agent-learner" / "history" / "promotions.jsonl").read_text(encoding="utf-8")
    assert '"field_diffs_summary"' in ledger
    assert 'rule:' in ledger


def test_process_events_rejects_generic_candidate_and_writes_rejection_ledger(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(json.dumps({"message": "Always be careful and good."}) + "\n", encoding="utf-8")
    write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="claude",
            event_name="session_end",
            cwd=str(tmp_path),
            session_id="reject-1",
            transcript_path=str(transcript),
            payload={"message": "Always be careful and good."},
        ),
    )

    results = process_unprocessed_events(tmp_path, adapter="claude")
    assert results[0].status == "candidate_rejected"
    assert results[0].decision == "reject_candidate"
    assert results[0].candidate_path is not None
    ledger = (tmp_path / ".agent-learner" / "history" / "promotions.jsonl").read_text(encoding="utf-8")
    assert '"action": "reject_candidate"' in ledger


def test_process_events_marks_related_conflict_as_fork_rule(tmp_path: Path) -> None:
    promote_rule(
        tmp_path,
        name="retry-network-failures",
        rule="Never retry network failures when the request budget is exhausted.",
        summary="Never retry network failures when the request budget is exhausted.",
        scope="codex adapter event:stop",
    )
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(json.dumps({"message": "Always retry network failures when the request budget allows it."}) + "\n", encoding="utf-8")
    write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="codex",
            event_name="stop",
            cwd=str(tmp_path),
            session_id="fork-1",
            transcript_path=str(transcript),
            payload={"message": "Always retry network failures when the request budget allows it."},
        ),
    )

    results = process_unprocessed_events(tmp_path, adapter="codex")
    assert results[0].status == "rule_forked"
    assert results[0].decision == "fork_rule"
    assert results[0].matched_rule != "retry-network-failures"
    assert results[0].review_required is False
    assert results[0].rule_path is not None
    candidate_record = load_candidate_record(Path(results[0].candidate_path or ""))
    assert candidate_record.status == "auto_applied"
    assert candidate_record.candidate.review_required is False
    assert candidate_record.candidate.confidence == "high"
    lifecycle = LearningLifecycle(tmp_path / ".agent-learner" / "learning")
    forked = lifecycle.load_rule(results[0].matched_rule or "")
    assert forked.related_rule == "retry-network-failures"


def test_process_events_allows_short_specific_rule_to_refresh(tmp_path: Path) -> None:
    promote_rule(
        tmp_path,
        name="keep-tests-updated",
        rule="Keep tests updated.",
        summary="Keep tests updated.",
        scope="codex adapter event:stop",
    )
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(json.dumps({"message": "Keep tests updated."}) + "\n", encoding="utf-8")
    write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="codex",
            event_name="stop",
            cwd=str(tmp_path),
            session_id="short-1",
            transcript_path=str(transcript),
            payload={"message": "Keep tests updated."},
        ),
    )

    results = process_unprocessed_events(tmp_path, adapter="codex")
    assert results[0].status == "rule_refreshed"
    assert results[0].decision == "refresh_existing"


def test_process_events_reapprove_needs_review_rule_when_evidence_is_clear(tmp_path: Path) -> None:
    lifecycle = LearningLifecycle(tmp_path / ".agent-learner" / "learning")
    rule = LearningRule(
        name="clear-review-rule",
        rule="Keep tests updated.",
        why="Verification should stay aligned with behavior changes.",
        scope="codex adapter event:stop",
        good_pattern="Update tests with code.",
        avoid_pattern="Ship stale tests.",
        summary="Keep tests updated.",
        status="needs_review",
    )
    lifecycle.mark_needs_review(rule)

    transcript = tmp_path / "session.jsonl"
    transcript.write_text(json.dumps({"message": "Keep tests updated."}) + "\n", encoding="utf-8")
    write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="codex",
            event_name="stop",
            cwd=str(tmp_path),
            session_id="reapprove-1",
            transcript_path=str(transcript),
            payload={"message": "Keep tests updated."},
        ),
    )

    results = process_unprocessed_events(tmp_path, adapter="codex")
    assert results[0].status == "rule_reapproved"
    assert results[0].decision == "refresh_existing"
    resolved = lifecycle.load_rule("clear-review-rule")
    assert resolved.status == "approved"


def test_process_events_reapprove_needs_review_rule_when_revision_is_clear(tmp_path: Path) -> None:
    lifecycle = LearningLifecycle(tmp_path / ".agent-learner" / "learning")
    rule = LearningRule(
        name="service-tests-rule",
        rule="Update tests whenever behavior changes.",
        why="Verification should stay aligned with behavior changes.",
        scope="codex adapter event:stop",
        good_pattern="Update tests with code.",
        avoid_pattern="Ship stale tests.",
        summary="Update tests whenever behavior changes.",
        status="needs_review",
    )
    lifecycle.mark_needs_review(rule)

    transcript = tmp_path / "session.jsonl"
    transcript.write_text(
        json.dumps({"message": "Always update tests whenever behavior changes in shared workflows and service-level changes."}) + "\n",
        encoding="utf-8",
    )
    write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="codex",
            event_name="stop",
            cwd=str(tmp_path),
            session_id="reapprove-revise-1",
            transcript_path=str(transcript),
            payload={"message": "Always update tests whenever behavior changes in shared workflows and service-level changes."},
        ),
    )

    results = process_unprocessed_events(tmp_path, adapter="codex")
    assert results[0].status == "rule_reapproved"
    assert results[0].decision == "revise_existing"
    resolved = lifecycle.load_rule("service-tests-rule")
    assert resolved.status == "approved"
    assert resolved.decision == "revise_existing"
