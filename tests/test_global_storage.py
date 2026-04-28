import json
from pathlib import Path

from agent_learner.core.events import LearningEvent, event_storage_dir, write_learning_event
from agent_learner.core.pipeline import candidate_storage_dir, processed_marker_dir
from agent_learner.core.storage import (
    canonical_learning_root,
    global_history_path,
    global_learning_root,
    migrate_local_learning_store_to_global,
    promotions_history_path,
)


def test_canonical_storage_paths_are_global(monkeypatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    project_root = tmp_path / "project"
    project_root.mkdir()
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(home))

    assert canonical_learning_root(project_root) == global_learning_root()
    assert promotions_history_path(project_root) == global_history_path()
    assert event_storage_dir(project_root, "hermes") == home / "events" / "hermes"
    assert candidate_storage_dir(project_root, "hermes") == home / "candidates" / "hermes"
    assert processed_marker_dir(project_root, "extract", "hermes") == home / "state" / "processed-events" / "extract" / "hermes"


def test_write_learning_event_stores_in_global_home(monkeypatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    project_root = tmp_path / "project"
    project_root.mkdir()
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(home))

    event = LearningEvent(
        adapter="hermes",
        event_name="session_end",
        cwd=str(project_root),
        captured_at="2026-04-28T13:00:00Z",
        session_id="sess-1",
        transcript_path="/tmp/transcript.json",
        payload={"summary": "Keep tests updated."},
        repo_id="acme/project",
        repo_root=str(project_root),
        worktree_path=str(project_root),
        repo_remote_url="git@github.com:acme/project.git",
    )

    path = write_learning_event(project_root, event)

    assert path == home / "events" / "hermes" / "session_end-sess-1.json"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert '"repo_id": "acme/project"' in text
    assert '"worktree_path": ' in text


def test_migrate_local_learning_store_to_global_copies_existing_artifacts(monkeypatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    project_root = tmp_path / "project"
    local = project_root / ".agent-learner"
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(home))

    (local / "events" / "hermes").mkdir(parents=True)
    (local / "candidates" / "hermes").mkdir(parents=True)
    (local / "history").mkdir(parents=True)
    (local / "learning" / "approved").mkdir(parents=True)

    event_path = local / "events" / "hermes" / "session_end-1.json"
    candidate_path = local / "candidates" / "hermes" / "candidate-rule.md"
    history_path = local / "history" / "promotions.jsonl"
    rule_path = local / "learning" / "approved" / "rule.md"

    event_path.write_text('{"adapter":"hermes"}\n', encoding="utf-8")
    candidate_path.write_text('candidate\n', encoding="utf-8")
    history_path.write_text('{"rule":"rule"}\n', encoding="utf-8")
    rule_path.write_text('---\nname: rule\nstatus: approved\n---\n\n## Rule\nKeep tests updated.\n', encoding="utf-8")

    migrated = migrate_local_learning_store_to_global(project_root)

    assert migrated["events"] == 1
    assert migrated["candidates"] == 1
    assert migrated["history"] == 1
    assert migrated["rules"] == 1
    assert (home / "events" / "hermes" / event_path.name).exists()
    assert (home / "candidates" / "hermes" / candidate_path.name).exists()
    assert global_history_path().exists()
    assert (global_learning_root() / "approved" / rule_path.name).exists()


def test_repeated_global_migration_keeps_original_marker_counts(monkeypatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    project_root = tmp_path / "project"
    local = project_root / ".agent-learner"
    marker = local / "state" / "storage-migration.json"
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(home))

    (local / "events" / "hermes").mkdir(parents=True)
    (local / "candidates" / "hermes").mkdir(parents=True)
    (local / "history").mkdir(parents=True)
    (local / "learning" / "approved").mkdir(parents=True)

    (local / "events" / "hermes" / "session_end-1.json").write_text('{"adapter":"hermes"}\n', encoding="utf-8")
    (local / "candidates" / "hermes" / "candidate-rule.md").write_text('candidate\n', encoding="utf-8")
    (local / "history" / "promotions.jsonl").write_text('{"rule":"rule"}\n', encoding="utf-8")
    (local / "learning" / "approved" / "rule.md").write_text('---\nname: rule\nstatus: approved\n---\n\n## Rule\nKeep tests updated.\n', encoding="utf-8")

    migrated = migrate_local_learning_store_to_global(project_root)
    assert migrated == {"events": 1, "candidates": 1, "history": 1, "rules": 1}

    migrated_again = migrate_local_learning_store_to_global(project_root)
    assert migrated_again == {"events": 0, "candidates": 0, "history": 0, "rules": 0}

    marker_payload = json.loads(marker.read_text(encoding="utf-8"))
    assert marker_payload["copied_counts"] == {"events": 1, "candidates": 1, "history": 1, "rules": 1}
