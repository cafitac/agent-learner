import json
from pathlib import Path

from agent_learner.core.events import build_learning_event, write_learning_event
from agent_learner.core.pipeline import (
    extract_candidate_from_event,
    is_processed,
    load_learning_event,
    process_unprocessed_events,
)


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
    assert results[0].status == "candidate_written"
    assert results[0].candidate_path is not None
    candidate_path = Path(results[0].candidate_path)
    assert candidate_path.exists()
    content = candidate_path.read_text(encoding="utf-8")
    assert "Always keep learned rules short and reusable." in content
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
