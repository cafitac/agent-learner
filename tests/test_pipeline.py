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
    lifecycle = LearningLifecycle(tmp_path / "home-learning" / "learning")
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


def test_process_events_extracts_hermes_candidate_from_transcript(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(json.dumps({"message": "Always keep Hermes learning rules short and reusable."}) + "\n", encoding="utf-8")
    event_path = write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="hermes",
            event_name="session_end",
            cwd=str(tmp_path),
            session_id="hermes-123",
            transcript_path=str(transcript),
            payload={"message": "session ended"},
        ),
    )

    results = process_unprocessed_events(tmp_path, adapter="hermes")
    assert len(results) == 1
    assert results[0].status == "rule_promoted"
    assert results[0].source_adapter == "hermes"
    assert results[0].candidate_path is not None
    assert results[0].rule_path is not None
    candidate_record = load_candidate_record(Path(results[0].candidate_path or ""))
    assert candidate_record.status == "auto_applied"
    assert candidate_record.candidate.review_required is False
    assert is_processed(tmp_path, event_path)


def test_extract_candidate_ignores_hermes_session_metadata_and_tool_schema(tmp_path: Path) -> None:
    transcript = tmp_path / "session.json"
    transcript.write_text(
        json.dumps(
            {
                "system_prompt": "Memory is injected into every turn. Always save durable facts.",
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "memory",
                            "description": "Always save durable facts when needed.",
                        },
                    }
                ],
                "message_count": 2,
                "messages": [
                    {"role": "user", "content": "Say OK only"},
                    {"role": "assistant", "content": "OK"},
                ],
            }
        ),
        encoding="utf-8",
    )
    event_path = write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="hermes",
            event_name="session_end",
            cwd=str(tmp_path),
            session_id="hermes-json-1",
            transcript_path=str(transcript),
            payload={"message": "session ended"},
        ),
    )

    event = load_learning_event(event_path)
    candidate = extract_candidate_from_event(tmp_path, event_path, event)
    assert candidate is None


def test_extract_candidate_reads_rule_signal_from_hermes_session_messages(tmp_path: Path) -> None:
    transcript = tmp_path / "session.json"
    transcript.write_text(
        json.dumps(
            {
                "system_prompt": "Memory is injected into every turn. Always save durable facts.",
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "memory",
                            "description": "Always save durable facts when needed.",
                        },
                    }
                ],
                "message_count": 2,
                "messages": [
                    {"role": "user", "content": "Summarize the outcome."},
                    {"role": "assistant", "content": "Always keep Hermes learning rules short and reusable."},
                ],
            }
        ),
        encoding="utf-8",
    )
    event_path = write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="hermes",
            event_name="session_end",
            cwd=str(tmp_path),
            session_id="hermes-json-2",
            transcript_path=str(transcript),
            payload={"message": "session ended"},
        ),
    )

    event = load_learning_event(event_path)
    candidate = extract_candidate_from_event(tmp_path, event_path, event)
    assert candidate is not None
    assert candidate.suggested_rule == "Always keep Hermes learning rules short and reusable."


def test_extract_candidate_ignores_hermes_skill_wrapper_in_user_message(tmp_path: Path) -> None:
    transcript = tmp_path / "session.json"
    transcript.write_text(
        json.dumps(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "[IMPORTANT: The user has invoked the \"code-polish\" skill, indicating they want you to follow its instructions. The full skill content is loaded below.]\n\n---\nname: code-polish\ndescription: Use when you want Hermes to iterate review, apply, and push loops on an Earlypay PR until major findings are cleared.\n---\n\n# Code Polish\n\n## Overview\nUse this for the full review-fix-repeat loop. Hermes should repeat `code-review` and `code-apply` until serious findings are gone, then finish with testing and push preparation.\n\n[Skill directory: /Users/reddit/.hermes/skills/custom/code-polish]\nResolve any relative paths in this skill against that directory.\n\nThe user has provided the following instruction alongside the skill invocation: 4026",
                    },
                    {"role": "assistant", "content": ""},
                ]
            }
        ),
        encoding="utf-8",
    )
    event_path = write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="hermes",
            event_name="session_end",
            cwd=str(tmp_path),
            session_id="hermes-skill-wrapper-1",
            transcript_path=str(transcript),
            payload={"message": "session ended"},
        ),
    )

    event = load_learning_event(event_path)
    candidate = extract_candidate_from_event(tmp_path, event_path, event)
    assert candidate is None


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
    ledger = (tmp_path / "home-learning" / "history" / "promotions.jsonl").read_text(encoding="utf-8")
    assert '"action": "refresh"' in ledger

    lifecycle = LearningLifecycle(tmp_path / "home-learning" / "learning")
    refreshed = lifecycle.load_rule("keep-tests-aligned")
    assert refreshed.refresh_count == 1
    assert refreshed.decision == "refresh_existing"
    assert refreshed.source_adapter == "claude"
    assert refreshed.derived_from_candidate is not None


def test_process_events_refreshes_existing_hermes_rule_from_real_runtime_phrase(tmp_path: Path) -> None:
    promote_rule(
        tmp_path,
        name="keep-hermes-learning-rules-concise",
        rule="Keep Hermes learning rules concise and reusable.",
        summary="Keep Hermes learning rules concise and reusable.",
        scope="hermes adapter event:session_end",
    )
    transcript = tmp_path / "session.json"
    transcript.write_text(
        json.dumps(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "When generating durable learning candidates, keep them concise and reusable. Say OK only.",
                    },
                    {"role": "assistant", "content": "OK"},
                ]
            }
        ),
        encoding="utf-8",
    )
    write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="hermes",
            event_name="session_end",
            cwd=str(tmp_path),
            session_id="hermes-real-phrase-1",
            transcript_path=str(transcript),
            payload={"message": "done"},
        ),
    )

    results = process_unprocessed_events(tmp_path, adapter="hermes")
    assert results[0].status == "rule_refreshed"
    assert results[0].decision == "refresh_existing"
    assert results[0].matched_rule == "keep-hermes-learning-rules-concise"



def test_process_events_does_not_refresh_unrelated_concise_and_reusable_rule(tmp_path: Path) -> None:
    promote_rule(
        tmp_path,
        name="keep-hermes-learning-rules-concise",
        rule="Keep Hermes learning rules concise and reusable.",
        summary="Keep Hermes learning rules concise and reusable.",
        scope="hermes adapter event:session_end",
    )
    transcript = tmp_path / "session.json"
    transcript.write_text(
        json.dumps(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "Keep deployment logs concise and reusable. Say OK only.",
                    },
                    {"role": "assistant", "content": "OK"},
                ]
            }
        ),
        encoding="utf-8",
    )
    write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="hermes",
            event_name="session_end",
            cwd=str(tmp_path),
            session_id="hermes-real-phrase-2",
            transcript_path=str(transcript),
            payload={"message": "done"},
        ),
    )

    results = process_unprocessed_events(tmp_path, adapter="hermes")
    assert results[0].decision != "refresh_existing"
    assert results[0].matched_rule != "keep-hermes-learning-rules-concise"



def test_process_events_keeps_revision_candidate_in_queue_when_review_required(tmp_path: Path) -> None:
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
    assert results[0].status == "candidate_written"
    assert results[0].decision == "revise_existing"
    assert results[0].matched_rule == "update-tests"
    assert results[0].review_required is True
    candidate_path = Path(results[0].candidate_path or "")
    assert candidate_path.exists()
    content = candidate_path.read_text(encoding="utf-8")
    assert "decision: revise_existing" in content
    candidate_record = load_candidate_record(candidate_path)
    assert candidate_record.status == "draft_candidate"
    assert candidate_record.candidate.review_required is True
    lifecycle = LearningLifecycle(tmp_path / "home-learning" / "learning")
    revised = lifecycle.load_rule("update-tests")
    assert revised.decision is None
    assert revised.supersedes is None
    ledger = (tmp_path / "home-learning" / "history" / "promotions.jsonl").read_text(encoding="utf-8")
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
    ledger = (tmp_path / "home-learning" / "history" / "promotions.jsonl").read_text(encoding="utf-8")
    assert '"action": "reject_candidate"' in ledger


def test_process_events_rejects_real_runtime_generic_helpful_process_candidate(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    message = "Always keep the process clean and helpful."
    transcript.write_text(json.dumps({"message": message}) + "\n", encoding="utf-8")
    write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="hermes",
            event_name="session_end",
            cwd=str(tmp_path),
            session_id="reject-real-1",
            transcript_path=str(transcript),
            payload={"message": message},
        ),
    )

    results = process_unprocessed_events(tmp_path, adapter="hermes")
    assert results[0].status == "candidate_rejected"
    assert results[0].decision == "reject_candidate"
    candidate_record = load_candidate_record(Path(results[0].candidate_path or ""))
    assert candidate_record.status == "rejected_candidate"
    assert candidate_record.candidate.decision_reason == "candidate signal is too generic to become a durable rule"


def test_process_events_rejects_real_runtime_contextless_pronoun_candidate(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    message = "Keep it concise."
    transcript.write_text(json.dumps({"message": message}) + "\n", encoding="utf-8")
    write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="hermes",
            event_name="session_end",
            cwd=str(tmp_path),
            session_id="reject-real-pronoun-1",
            transcript_path=str(transcript),
            payload={"message": message},
        ),
    )

    results = process_unprocessed_events(tmp_path, adapter="hermes")
    assert results[0].status == "candidate_rejected"
    assert results[0].decision == "reject_candidate"
    candidate_record = load_candidate_record(Path(results[0].candidate_path or ""))
    assert candidate_record.status == "rejected_candidate"
    assert candidate_record.candidate.decision_reason == "candidate signal is too contextless to become a durable rule"


def test_process_events_rejects_real_runtime_contextless_pronoun_compact_candidate(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    message = "Keep it compact."
    transcript.write_text(json.dumps({"message": message}) + "\n", encoding="utf-8")
    write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="hermes",
            event_name="session_end",
            cwd=str(tmp_path),
            session_id="reject-real-pronoun-compact-1",
            transcript_path=str(transcript),
            payload={"message": message},
        ),
    )

    results = process_unprocessed_events(tmp_path, adapter="hermes")
    assert results[0].status == "candidate_rejected"
    assert results[0].decision == "reject_candidate"
    candidate_record = load_candidate_record(Path(results[0].candidate_path or ""))
    assert candidate_record.status == "rejected_candidate"
    assert candidate_record.candidate.decision_reason == "candidate signal is too contextless to become a durable rule"


def test_process_events_rejects_real_runtime_malformed_code_fragment_candidate(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    message = ", ack_mode=AUTO), so they do not protect the durability behavior that should rely on MANUAL ack / processing-list recovery."
    transcript.write_text(json.dumps({"message": message}) + "\n", encoding="utf-8")
    write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="hermes",
            event_name="session_end",
            cwd=str(tmp_path),
            session_id="reject-real-fragment-1",
            transcript_path=str(transcript),
            payload={"message": message},
        ),
    )

    results = process_unprocessed_events(tmp_path, adapter="hermes")
    assert results[0].status == "candidate_rejected"
    assert results[0].decision == "reject_candidate"
    candidate_record = load_candidate_record(Path(results[0].candidate_path or ""))
    assert candidate_record.status == "rejected_candidate"
    assert candidate_record.candidate.decision_reason == "candidate signal looks like a malformed code or log fragment, not a durable rule"


def test_process_events_rejects_task_specific_review_constraint_do_not_modify_files(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    message = (
        "Review the current uncommitted diff in /Users/reddit/Project/earlypay/earlypay-settlement for PR #4026 "
        "queue ack/recovery changes. Focus only on correctness issues that could cause message loss, duplicate "
        "dispatch, retry budget mistakes, or CI failures. Verify findings against the actual diff and repo; return "
        "concise severity-ranked findings or say no major findings. Do not modify files."
    )
    transcript.write_text(json.dumps({"message": message}) + "\n", encoding="utf-8")
    write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="hermes",
            event_name="session_end",
            cwd=str(tmp_path),
            session_id="reject-review-constraint-modify-files-1",
            transcript_path=str(transcript),
            payload={"message": message},
        ),
    )

    results = process_unprocessed_events(tmp_path, adapter="hermes")
    assert results[0].status == "candidate_rejected"
    assert results[0].decision == "reject_candidate"
    candidate_record = load_candidate_record(Path(results[0].candidate_path or ""))
    assert candidate_record.status == "rejected_candidate"
    assert candidate_record.candidate.decision_reason == "candidate signal is a task-specific review constraint, not a durable rule"


def test_process_events_rejects_task_specific_review_constraint_prior_reviews(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    message = (
        "Fresh correctness review of PR 4026 tests/factory/CI-hardening changes. Do not assume prior reviews are correct. "
        "Identify P1/P2/P3 issues only, grounded in current diff origin/develop...HEAD. Focus on UserFactory Sequence "
        "side effects, test coverage gaps, tests that might give false confidence, and whether local/CI gates cover "
        "changed behavior. Return concise Korean summary with file/line references if findings exist."
    )
    transcript.write_text(json.dumps({"message": message}) + "\n", encoding="utf-8")
    write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="hermes",
            event_name="session_end",
            cwd=str(tmp_path),
            session_id="reject-review-constraint-prior-reviews-1",
            transcript_path=str(transcript),
            payload={"message": message},
        ),
    )

    results = process_unprocessed_events(tmp_path, adapter="hermes")
    assert results[0].status == "candidate_rejected"
    assert results[0].decision == "reject_candidate"
    candidate_record = load_candidate_record(Path(results[0].candidate_path or ""))
    assert candidate_record.status == "rejected_candidate"
    assert candidate_record.candidate.decision_reason == "candidate signal is a task-specific review constraint, not a durable rule"


def test_process_events_keeps_operational_debug_note_in_candidate_queue_until_repeated(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    message = "Always distinguish OMX hook messages from AgentLearner hook messages when debugging Codex installs."
    transcript.write_text(json.dumps({"message": message}) + "\n", encoding="utf-8")
    write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="codex",
            event_name="stop",
            cwd=str(tmp_path),
            session_id="ops-1",
            transcript_path=str(transcript),
            payload={"message": message},
        ),
    )

    first = process_unprocessed_events(tmp_path, adapter="codex")
    assert first[0].status == "candidate_written"
    assert first[0].decision == "new_rule"
    assert first[0].review_required is True
    assert first[0].rule_path is None
    first_candidate = load_candidate_record(Path(first[0].candidate_path or ""))
    assert first_candidate.status == "draft_candidate"
    assert first_candidate.candidate.review_required is True

    write_learning_event(
        tmp_path,
        build_learning_event(
            adapter="codex",
            event_name="stop",
            cwd=str(tmp_path),
            session_id="ops-2",
            transcript_path=str(transcript),
            payload={"message": message},
        ),
    )

    second = process_unprocessed_events(tmp_path, adapter="codex")
    assert second[0].status == "rule_promoted"
    assert second[0].decision == "new_rule"
    assert second[0].review_required is False
    assert second[0].rule_path is not None
    second_candidate = load_candidate_record(Path(second[0].candidate_path or ""))
    assert second_candidate.status == "auto_applied"
    lifecycle = LearningLifecycle(tmp_path / "home-learning" / "learning")
    promoted = lifecycle.load_rule(second[0].matched_rule or "distinguish-omx-hook-messages-from-agentlearner")
    assert promoted.status == "approved"


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
    lifecycle = LearningLifecycle(tmp_path / "home-learning" / "learning")
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
    lifecycle = LearningLifecycle(tmp_path / "home-learning" / "learning")
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
    lifecycle = LearningLifecycle(tmp_path / "home-learning" / "learning")
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
