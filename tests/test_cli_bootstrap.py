import json
from pathlib import Path

from agent_learner.cli.main import main as cli_main
from agent_learner.core.lifecycle import LearningLifecycle
from agent_learner.core.models import LearningRule


def test_bootstrap_codex_only(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "bootstrap", "--target", str(tmp_path), "--adapters", "codex"],
    )
    assert cli_main() == 0
    assert (tmp_path / ".codex" / "hooks.json").exists()
    assert not (tmp_path / ".claude").exists()


def test_bootstrap_claude_only(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "bootstrap", "--target", str(tmp_path), "--adapters", "claude"],
    )
    assert cli_main() == 0
    assert (tmp_path / ".claude" / "settings.json").exists()
    assert not (tmp_path / ".codex").exists()


def test_bootstrap_both(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "bootstrap", "--target", str(tmp_path)],
    )
    assert cli_main() == 0
    assert (tmp_path / ".codex" / "hooks.json").exists()
    assert (tmp_path / ".claude" / "settings.json").exists()


def test_render_codex_context_command_outputs_hook_json(monkeypatch, tmp_path: Path, capsys) -> None:
    lifecycle = LearningLifecycle(tmp_path / ".codex" / "references" / "learning")
    lifecycle.promote(
        LearningRule(
            name="keep-tests-updated",
            rule="Update tests whenever behavior changes.",
            why="Verification should move with behavior.",
            scope="changes",
            good_pattern="Edit code and tests together.",
            avoid_pattern="Delay test updates.",
            summary="Keep tests aligned with behavior changes.",
            triggers=["behavior", "tests"],
            task_types=["bugfix"],
            priority="high",
            confidence="high",
        )
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "agent-learner",
            "render-codex-context",
            "--project-root",
            str(tmp_path),
            "--prompt",
            "fix behavior bug and keep tests updated",
            "--format",
            "hook-json",
        ],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "active_learning" in payload["hookSpecificOutput"]["additionalContext"]


def test_retrieve_command_outputs_ranked_rules(monkeypatch, tmp_path: Path, capsys) -> None:
    lifecycle = LearningLifecycle(tmp_path / ".codex" / "references" / "learning")
    lifecycle.promote(
        LearningRule(
            name="prompt-hook-tests",
            rule="Update tests with hook changes.",
            why="Prompt wiring should stay verified.",
            scope="codex adapter",
            good_pattern="Change hook code and tests together.",
            avoid_pattern="Edit hook behavior without regression tests.",
            summary="Keep hook changes covered by tests.",
            triggers=["hook", "tests"],
            task_types=["cli"],
            priority="high",
            confidence="high",
        )
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "agent-learner",
            "retrieve",
            "--project-root",
            str(tmp_path),
            "--prompt",
            "fix the codex hook and tests",
        ],
    )
    assert cli_main() == 0
    output = capsys.readouterr().out
    assert "prompt-hook-tests" in output


def test_qa_codex_smoke_command_runs_end_to_end(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "qa-codex-smoke"],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["returncode"] == 0
    assert payload["payload"]["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "codex-hook-tests" in payload["payload"]["hookSpecificOutput"]["additionalContext"]


def test_capture_event_command_writes_normalized_event(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "agent-learner",
            "capture-event",
            "--project-root",
            str(tmp_path),
            "--adapter",
            "codex",
            "--event-name",
            "stop",
            "--session-id",
            "session-123",
        ],
    )
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO('{"prompt":"hello"}'))
    assert cli_main() == 0
    out_path = Path(capsys.readouterr().out.strip())
    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["adapter"] == "codex"
    assert payload["event_name"] == "stop"
    assert payload["payload"]["prompt"] == "hello"


def test_process_events_command_outputs_candidate_json(monkeypatch, tmp_path: Path, capsys) -> None:
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(json.dumps({"message": "Always keep learned rules concise."}) + "\n", encoding="utf-8")
    event_dir = tmp_path / ".agent-learner" / "events" / "claude"
    event_dir.mkdir(parents=True, exist_ok=True)
    event_path = event_dir / "session_end-s1.json"
    event_path.write_text(json.dumps({
        "adapter": "claude",
        "event_name": "session_end",
        "cwd": str(tmp_path),
        "captured_at": "2026-04-20T00:00:00Z",
        "session_id": "s1",
        "transcript_path": str(transcript),
        "payload": {"message": "done"}
    }))
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "process-events", "--project-root", str(tmp_path), "--adapter", "claude", "--format", "json"],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["status"] == "candidate_written"


def test_qa_claude_smoke_creates_event_and_candidate(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["agent-learner", "qa-claude-smoke"])
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["returncode"] == 0
    assert payload["event_files"]
    assert payload["candidate_files"]


def test_detect_context_set_model_and_sweep_commands(monkeypatch, tmp_path: Path, capsys) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["agent-learner", "set-model", "--project-root", str(tmp_path), "--model", "claude-opus-4-7"])
    assert cli_main() == 0
    assert (tmp_path / ".agent-learner" / "state" / "current-model.txt").exists()
    _ = capsys.readouterr()

    monkeypatch.setattr("sys.argv", ["agent-learner", "detect-context", "--project-root", str(tmp_path)])
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["current_model"] == "claude-opus-4-7"

    learning_root = tmp_path / ".codex" / "references" / "learning"
    lifecycle = LearningLifecycle(learning_root)
    rule = LearningRule(
        name="sweep-me",
        rule="Always revalidate high-dependency rules.",
        why="Model changes can alter behavior.",
        scope="core",
        good_pattern="Validate on new model.",
        avoid_pattern="Assume compatibility.",
        summary="Revalidate model-sensitive rules.",
        model_dependency="high",
        validated_on_models=["claude-sonnet-4-6"],
        languages=["python"],
    )
    lifecycle.promote(rule)

    monkeypatch.setattr("sys.argv", ["agent-learner", "sweep", "--project-root", str(tmp_path), "--format", "json"])
    assert cli_main() == 0
    changes = json.loads(capsys.readouterr().out)
    assert changes[0]["to"] == "needs_review"
