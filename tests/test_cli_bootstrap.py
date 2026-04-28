import json
from pathlib import Path

import pytest

from agent_learner.core.doctor import collect_dashboard_doctor, ensure_frontend_dist, format_doctor_text
from agent_learner.core.dashboard import build_dashboard_summary, merge_rules
from agent_learner.core.fastapi_app import app_root_dir, frontend_dist_dir, frontend_src_dir, frontend_dist_is_valid
from agent_learner.cli.main import build_parser, main as cli_main
from agent_learner.core.lifecycle import LearningLifecycle
from agent_learner.core.models import LearningRule
from agent_learner.core.webapp import apply_web_action, render_dashboard_app_html, run_dashboard_server


def test_bootstrap_codex_only(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "bootstrap", "--target", str(tmp_path), "--adapters", "codex", "--codex-scope", "project"],
    )
    assert cli_main() == 0
    assert (tmp_path / ".codex" / "hooks.json").exists()
    assert (tmp_path / "home-learning" / "learning").exists()
    assert not (tmp_path / ".claude").exists()


def test_bootstrap_codex_user_scope_writes_to_home(monkeypatch, tmp_path: Path) -> None:
    home_root = tmp_path / "home"
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "bootstrap", "--adapters", "codex", "--codex-scope", "user", "--target", str(home_root)],
    )
    assert cli_main() == 0
    assert (home_root / ".codex" / "hooks.json").exists()
    assert not (home_root / ".agent-learner" / "learning").exists()


@pytest.mark.parametrize(
    ("command", "replacement"),
    [
        ("install-codex", "bootstrap --adapters codex"),
        ("install-claude", "bootstrap --adapters claude"),
        ("install-hermes", "bootstrap --adapters hermes"),
    ],
)
def test_removed_install_commands_point_to_bootstrap(monkeypatch, capsys, command: str, replacement: str) -> None:
    monkeypatch.setattr("sys.argv", ["agent-learner", command])
    with pytest.raises(SystemExit) as exc:
        cli_main()
    assert exc.value.code == 2
    stderr = capsys.readouterr().err
    assert f"`{command}` was removed" in stderr
    assert replacement in stderr


def test_doctor_command_reports_status(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "doctor", "--project-root", str(tmp_path), "--format", "json"],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert "ready_fastapi" in payload
    assert "frontend" in payload
    assert payload["project_root"] == str(tmp_path.resolve())
    assert "status" in payload
    assert "verdict" in payload
    assert "can_run_now" in payload
    assert "can_auto_build" in payload
    assert "next_command" in payload


def test_bootstrap_claude_only(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "bootstrap", "--target", str(tmp_path), "--adapters", "claude", "--claude-scope", "project"],
    )
    assert cli_main() == 0
    assert (tmp_path / ".claude" / "settings.json").exists()
    assert not (tmp_path / ".codex").exists()


def test_bootstrap_hermes_project_scope_creates_project_assets(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "bootstrap", "--adapters", "hermes", "--hermes-scope", "project", "--target", str(tmp_path)],
    )
    assert cli_main() == 0
    assert not (tmp_path / ".agent-learner" / "events" / "hermes").exists()
    assert (tmp_path / ".hermes" / "hooks" / "auto_session_learning.py").exists()
    assert (tmp_path / ".hermes" / "hooks" / "hermes_prompt_context.py").exists()
    assert (tmp_path / ".hermes" / "config.yaml").exists()
    assert (tmp_path / ".hermes" / "config.agent-learner.yaml").exists()
    assert not (tmp_path / ".codex").exists()
    assert not (tmp_path / ".claude").exists()
    stderr = capsys.readouterr().err
    assert "Hermes adapter installed in project-local opt-in mode" in stderr
    assert "Safest activation:" in stderr
    assert "HERMES_HOME=" in stderr
    assert "must also have model/auth configured" in stderr


def test_bootstrap_hermes_project_scope_preserves_existing_config_and_prints_merge_guidance(monkeypatch, tmp_path: Path, capsys) -> None:
    hermes_root = tmp_path / ".hermes"
    hermes_root.mkdir(parents=True, exist_ok=True)
    config_path = hermes_root / "config.yaml"
    config_path.write_text("model:\n  provider: openai-codex\n", encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "bootstrap", "--adapters", "hermes", "--hermes-scope", "project", "--target", str(tmp_path)],
    )
    assert cli_main() == 0
    assert config_path.read_text(encoding="utf-8") == "model:\n  provider: openai-codex\n"
    stderr = capsys.readouterr().err
    assert "Existing Hermes config preserved" in stderr
    assert "config.agent-learner.yaml" in stderr


def test_bootstrap_defaults_to_all_three_user_scope(monkeypatch, tmp_path: Path, capsys) -> None:
    home_root = tmp_path / "home-bootstrap"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home_root))
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "bootstrap"],
    )
    assert cli_main() == 0
    assert (home_root / ".codex" / "hooks.json").exists()
    assert (home_root / ".claude" / "settings.json").exists()
    assert (home_root / ".hermes" / "config.yaml").exists()
    assert not (home_root / ".agent-learner" / "events").exists()
    stderr = capsys.readouterr().err
    assert "Bootstrap installed adapters: codex, claude, hermes" in stderr
    assert "Default bootstrap keeps everything in user scope unless you opt into project scope." in stderr


def test_bootstrap_hermes_only_defaults_to_user_scope(monkeypatch, tmp_path: Path, capsys) -> None:
    home_root = tmp_path / "home-hermes-bootstrap"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home_root))
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "bootstrap", "--adapters", "hermes"],
    )
    assert cli_main() == 0
    assert (home_root / ".hermes" / "hooks" / "auto_session_learning.py").exists()
    assert not (home_root / ".agent-learner").exists()
    assert not (home_root / ".codex").exists()
    assert not (home_root / ".claude").exists()
    stderr = capsys.readouterr().err
    assert "Hermes user-scope hooks installed" in stderr
    assert "project-local opt-in" not in stderr


def test_bootstrap_hermes_preserves_existing_config_and_auto_merges_hooks(monkeypatch, tmp_path: Path, capsys) -> None:
    hermes_root = tmp_path / ".hermes"
    hermes_root.mkdir(parents=True, exist_ok=True)
    config_path = hermes_root / "config.yaml"
    config_path.write_text("model:\n  provider: openai-codex\nhooks: {}\n", encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "bootstrap", "--target", str(tmp_path), "--adapters", "hermes"],
    )
    assert cli_main() == 0
    config_text = config_path.read_text(encoding="utf-8")
    assert "provider: openai-codex" in config_text
    assert "pre_llm_call" in config_text
    assert "on_session_end" in config_text
    assert (hermes_root / "config.yaml.agent-learner.bak").exists()
    stderr = capsys.readouterr().err
    assert "Hermes user-scope hooks installed" in stderr
    assert "merged into your active Hermes config" in stderr
    assert "config.agent-learner.yaml" in stderr


def test_bootstrap_help_emphasizes_one_command_default_and_labels_advanced_flags(capsys) -> None:
    parser = build_parser()
    try:
        parser.parse_args(["bootstrap", "--help"])
    except SystemExit as exc:
        assert exc.code == 0
    help_text = capsys.readouterr().out
    assert "One-command setup:" in help_text
    assert "installs codex, claude, and hermes in user scope by" in help_text
    assert "default" in help_text
    assert "advanced" in help_text.lower()
    assert "--target TARGET" in help_text
    assert "--hermes-scope {project,user}" in help_text


def test_removed_install_commands_are_not_in_parser(capsys) -> None:
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["install-hermes"])
    assert exc.value.code == 2
    stderr = capsys.readouterr().err
    assert "invalid choice" in stderr
    assert "install-hermes" in stderr


def test_bootstrap_migrates_legacy_codex_learning_assets(monkeypatch, tmp_path: Path) -> None:
    legacy_rule = tmp_path / ".codex" / "references" / "learning" / "approved" / "legacy-rule.md"
    legacy_rule.parent.mkdir(parents=True, exist_ok=True)
    legacy_rule.write_text(
        "---\nname: legacy-rule\ndescription: legacy rule\ntype: learned-feedback\nstatus: approved\n---\n\n## Rule\nKeep tests updated.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "bootstrap", "--target", str(tmp_path), "--adapters", "codex", "--codex-scope", "project"],
    )
    assert cli_main() == 0
    assert (tmp_path / "home-learning" / "learning" / "approved" / "legacy-rule.md").exists()
    assert (tmp_path / ".agent-learner" / "state" / "storage-migration.json").exists()


def test_render_codex_context_command_outputs_hook_json(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(tmp_path / "home-learning"))
    lifecycle = LearningLifecycle(tmp_path / "home-learning" / "learning")
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


def test_render_hermes_context_command_outputs_json(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(tmp_path / "home-learning"))
    lifecycle = LearningLifecycle(tmp_path / "home-learning" / "learning")
    lifecycle.promote(
        LearningRule(
            name="hermes-tests-updated",
            rule="Update Hermes tests whenever bootstrap behavior changes.",
            why="Hermes bootstrap wiring should stay regression-tested.",
            scope="hermes adapter",
            good_pattern="Edit Hermes bootstrap code and tests together.",
            avoid_pattern="Change Hermes wiring without tests.",
            summary="Keep Hermes bootstrap changes covered by tests.",
            triggers=["hermes", "bootstrap", "tests"],
            task_types=["cli"],
            priority="high",
            confidence="high",
        )
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "agent-learner",
            "render-hermes-context",
            "--project-root",
            str(tmp_path),
            "--prompt",
            "update hermes bootstrap wiring and tests",
            "--format",
            "json",
        ],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert "additional_context" in payload
    assert "active_learning" in payload["additional_context"]
    assert "hermes-tests-updated" in payload["additional_context"]


def test_retrieve_command_outputs_ranked_rules(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(tmp_path / "home-learning"))
    lifecycle = LearningLifecycle(tmp_path / "home-learning" / "learning")
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


def test_qa_codex_smoke_command_runs_end_to_end(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(tmp_path / "home-learning"))
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "qa-codex-smoke"],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["returncode"] == 0
    assert payload["payload"]["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "codex-hook-tests" in payload["payload"]["hookSpecificOutput"]["additionalContext"]


def test_qa_codex_smoke_command_runs_end_to_end_user_scope(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(tmp_path / "home-learning"))
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "qa-codex-smoke", "--scope", "user"],
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


def test_capture_event_command_writes_hermes_session_end(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "agent-learner",
            "capture-event",
            "--project-root",
            str(tmp_path),
            "--adapter",
            "hermes",
            "--event-name",
            "session_end",
            "--session-id",
            "session-hermes-1",
        ],
    )
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO('{"summary":"Always keep Hermes rules concise."}'))
    assert cli_main() == 0
    out_path = Path(capsys.readouterr().out.strip())
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["adapter"] == "hermes"
    assert payload["event_name"] == "session_end"
    assert payload["payload"]["summary"] == "Always keep Hermes rules concise."


def test_process_events_command_outputs_candidate_json(monkeypatch, tmp_path: Path, capsys) -> None:
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(json.dumps({"message": "Always keep learned rules concise."}) + "\n", encoding="utf-8")
    event_dir = tmp_path / "home-learning" / "events" / "claude"
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
    assert payload[0]["status"] == "rule_promoted"


def test_process_events_command_outputs_hermes_candidate_json(monkeypatch, tmp_path: Path, capsys) -> None:
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(json.dumps({"message": "Always keep Hermes learning rules concise and reusable."}) + "\n", encoding="utf-8")
    event_dir = tmp_path / "home-learning" / "events" / "hermes"
    event_dir.mkdir(parents=True, exist_ok=True)
    event_path = event_dir / "session_end-h1.json"
    event_path.write_text(json.dumps({
        "adapter": "hermes",
        "event_name": "session_end",
        "cwd": str(tmp_path),
        "captured_at": "2026-04-20T00:00:00Z",
        "session_id": "h1",
        "transcript_path": str(transcript),
        "payload": {"message": "done"}
    }))
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "process-events", "--project-root", str(tmp_path), "--adapter", "hermes", "--format", "json"],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["status"] == "rule_promoted"
    assert payload[0]["source_adapter"] == "hermes"


def test_review_candidates_and_approve_candidate_commands(monkeypatch, tmp_path: Path, capsys) -> None:
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(json.dumps({"message": "Always update tests whenever behavior changes in services."}) + "\n", encoding="utf-8")
    event_dir = tmp_path / "home-learning" / "events" / "codex"
    event_dir.mkdir(parents=True, exist_ok=True)
    event_path = event_dir / "stop-s1.json"
    event_path.write_text(json.dumps({
        "adapter": "codex",
        "event_name": "stop",
        "cwd": str(tmp_path),
        "captured_at": "2026-04-20T00:00:00Z",
        "session_id": "s1",
        "transcript_path": str(transcript),
        "payload": {"message": "Always update tests whenever behavior changes in services."}
    }))

    monkeypatch.setattr("sys.argv", ["agent-learner", "process-events", "--project-root", str(tmp_path)])
    assert cli_main() == 0
    _ = capsys.readouterr()

    monkeypatch.setattr("sys.argv", ["agent-learner", "review-candidates", "--project-root", str(tmp_path), "--format", "json"])
    assert cli_main() == 0
    records = json.loads(capsys.readouterr().out)
    assert len(records) == 1
    assert records[0]["decision"] == "new_rule"
    assert records[0]["status"] == "auto_applied"
    assert "field_diffs" in records[0]
    candidate_path = records[0]["path"]

    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "review-candidate", "--project-root", str(tmp_path), "--candidate", candidate_path, "--action", "approve", "--format", "json"],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "auto_applied"
    assert Path(payload["rule_path"]).exists()
    assert "field_diffs" in payload


def test_review_candidates_command_filters_hermes_candidates(monkeypatch, tmp_path: Path, capsys) -> None:
    transcript = tmp_path / "session.json"
    transcript.write_text(
        json.dumps(
            {
                "messages": [
                    {"role": "user", "content": "Always keep Hermes learning rules concise and reusable."},
                    {"role": "assistant", "content": "Noted."},
                ]
            }
        ),
        encoding="utf-8",
    )
    event_dir = tmp_path / "home-learning" / "events" / "hermes"
    event_dir.mkdir(parents=True, exist_ok=True)
    (event_dir / "session_end-h1.json").write_text(
        json.dumps(
            {
                "adapter": "hermes",
                "event_name": "session_end",
                "cwd": str(tmp_path),
                "captured_at": "2026-04-20T00:00:00Z",
                "session_id": "h1",
                "transcript_path": str(transcript),
                "payload": {"message": "done"},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("sys.argv", ["agent-learner", "process-events", "--project-root", str(tmp_path), "--adapter", "hermes"])
    assert cli_main() == 0
    _ = capsys.readouterr()

    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "review-candidates", "--project-root", str(tmp_path), "--adapter", "hermes", "--format", "json"],
    )
    assert cli_main() == 0
    records = json.loads(capsys.readouterr().out)
    assert len(records) == 1
    assert records[0]["adapter"] == "hermes"
    assert records[0]["source_event_path"].endswith("session_end-h1.json")



def test_history_command_filters_entries(monkeypatch, tmp_path: Path, capsys) -> None:
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(json.dumps({"message": "Always keep tests updated in services."}) + "\n", encoding="utf-8")
    event_dir = tmp_path / "home-learning" / "events" / "codex"
    event_dir.mkdir(parents=True, exist_ok=True)
    event_path = event_dir / "stop-s1.json"
    event_path.write_text(json.dumps({
        "adapter": "codex",
        "event_name": "stop",
        "cwd": str(tmp_path),
        "captured_at": "2026-04-20T00:00:00Z",
        "session_id": "s1",
        "transcript_path": str(transcript),
        "payload": {"message": "Always keep tests updated in services."}
    }))
    monkeypatch.setattr("sys.argv", ["agent-learner", "process-events", "--project-root", str(tmp_path)])
    assert cli_main() == 0
    _ = capsys.readouterr()

    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "history", "--project-root", str(tmp_path), "--action", "promote", "--adapter", "codex", "--format", "json"],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload
    assert all(entry["action"] == "promote" for entry in payload)
    assert all(entry["source_adapter"] == "codex" for entry in payload)
    candidate_name = payload[0]["derived_from_candidate"]

    monkeypatch.setattr(
        "sys.argv",
        [
            "agent-learner",
            "history",
            "--project-root",
            str(tmp_path),
            "--decision",
            "new_rule",
            "--candidate",
            candidate_name,
            "--format",
            "json",
        ],
    )
    assert cli_main() == 0
    filtered = json.loads(capsys.readouterr().out)
    assert filtered
    assert all(entry["decision"] == "new_rule" for entry in filtered)
    assert all(entry["derived_from_candidate"] == candidate_name for entry in filtered)


def test_history_command_filters_hermes_entries(monkeypatch, tmp_path: Path, capsys) -> None:
    transcript = tmp_path / "session.json"
    transcript.write_text(
        json.dumps(
            {
                "messages": [
                    {"role": "user", "content": "Always keep Hermes learning rules concise and reusable."},
                    {"role": "assistant", "content": "Noted."},
                ]
            }
        ),
        encoding="utf-8",
    )
    event_dir = tmp_path / "home-learning" / "events" / "hermes"
    event_dir.mkdir(parents=True, exist_ok=True)
    (event_dir / "session_end-h1.json").write_text(
        json.dumps(
            {
                "adapter": "hermes",
                "event_name": "session_end",
                "cwd": str(tmp_path),
                "captured_at": "2026-04-20T00:00:00Z",
                "session_id": "h1",
                "transcript_path": str(transcript),
                "payload": {"message": "done"},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("sys.argv", ["agent-learner", "process-events", "--project-root", str(tmp_path), "--adapter", "hermes"])
    assert cli_main() == 0
    _ = capsys.readouterr()

    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "history", "--project-root", str(tmp_path), "--adapter", "hermes", "--format", "json"],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload
    assert all(entry["source_adapter"] == "hermes" for entry in payload)
    assert all("session_end-h1.json" in entry["source_event"] for entry in payload)


def test_history_command_supports_latest_per_rule(monkeypatch, tmp_path: Path, capsys) -> None:
    history_path = tmp_path / "home-learning" / "history" / "promotions.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(
        json.dumps({"ts": "2026-04-20T00:00:01Z", "action": "promote", "rule": "keep-tests", "source_adapter": "codex"}) + "\n"
        + json.dumps({"ts": "2026-04-20T00:00:02Z", "action": "refresh", "rule": "keep-tests", "source_adapter": "codex"}) + "\n"
        + json.dumps({"ts": "2026-04-20T00:00:02Z", "action": "promote", "rule": "retry-network", "source_adapter": "codex"}) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "history", "--project-root", str(tmp_path), "--latest-per-rule", "--format", "json"],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    rule_names = [entry["rule"] for entry in payload]
    assert len(rule_names) == len(set(rule_names))

    monkeypatch.setattr(
        "sys.argv",
        [
            "agent-learner",
            "history",
            "--project-root",
            str(tmp_path),
            "--since",
            "2026-04-20T00:00:02Z",
            "--until",
            "2026-04-20T00:00:02Z",
            "--last",
            "1",
            "--format",
            "json",
        ],
    )
    assert cli_main() == 0
    filtered = json.loads(capsys.readouterr().out)
    assert len(filtered) == 1
    assert filtered[0]["ts"] == "2026-04-20T00:00:02Z"


def test_history_summary_groups_entries(monkeypatch, tmp_path: Path, capsys) -> None:
    history_path = tmp_path / "home-learning" / "history" / "promotions.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(
        json.dumps({"ts": "2026-04-20T00:00:01Z", "action": "promote", "rule": "keep-tests", "source_adapter": "codex", "decision": "new_rule"}) + "\n"
        + json.dumps({"ts": "2026-04-20T00:00:02Z", "action": "refresh", "rule": "keep-tests", "source_adapter": "codex", "decision": "refresh_existing"}) + "\n"
        + json.dumps({"ts": "2026-04-20T00:00:03Z", "action": "promote", "rule": "retry-network", "source_adapter": "claude", "decision": "new_rule"}) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "history-summary", "--project-root", str(tmp_path), "--by", "action", "--format", "json"],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["group_by"] == "action"
    groups = {item["key"]: item["count"] for item in payload["groups"]}
    assert groups["promote"] == 2
    assert groups["refresh"] == 1

    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "history-summary", "--project-root", str(tmp_path), "--by", "adapter", "--format", "json"],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    groups = {item["key"]: item["count"] for item in payload["groups"]}
    assert groups["codex"] == 2
    assert groups["claude"] == 1

    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "history-summary", "--project-root", str(tmp_path), "--by", "action", "--top", "1", "--format", "json"],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["groups"]) == 1
    assert payload["groups"][0]["key"] == "promote"

    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "history-summary", "--project-root", str(tmp_path), "--by", "adapter-decision", "--format", "json"],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["group_by"] == "adapter-decision"
    assert payload["matrix"]["codex"]["new_rule"] == 1
    assert payload["matrix"]["codex"]["refresh_existing"] == 1
    assert payload["matrix"]["claude"]["new_rule"] == 1


def test_usage_summary_reports_retrieval_and_stale_signals(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(tmp_path / "home-learning"))
    lifecycle = LearningLifecycle(tmp_path / "home-learning" / "learning")

    used_rule = LearningRule(
        name="used-rule",
        rule="Keep tests updated.",
        why="Frequently reused.",
        scope="testing",
        good_pattern="Update tests with behavior changes.",
        avoid_pattern="Ship stale tests.",
        summary="Frequently retrieved rule.",
        status="approved",
        promote_count=2,
        refresh_count=1,
        use_count=3,
        last_used="2026-04-25",
    )
    never_used_rule = LearningRule(
        name="never-used-rule",
        rule="Document migrations before rollout.",
        why="Still unproven.",
        scope="migrations",
        good_pattern="Write migration notes first.",
        avoid_pattern="Ship undocumented migrations.",
        summary="Promoted but never retrieved.",
        status="approved",
        promote_count=1,
        use_count=0,
    )
    stale_rule = LearningRule(
        name="stale-rule",
        rule="Keep deployment notes concise.",
        why="Looks old.",
        scope="deploy",
        good_pattern="Short deployment notes.",
        avoid_pattern="Verbose deployment notes.",
        summary="Old retrieved rule.",
        status="approved",
        promote_count=1,
        use_count=2,
        last_used="2026-03-01",
    )
    lifecycle.save_rule(used_rule)
    lifecycle.save_rule(never_used_rule)
    lifecycle.save_rule(stale_rule)

    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "usage-summary", "--project-root", str(tmp_path), "--stale-days", "30", "--format", "json"],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["overview"]["total_rules"] == 3
    assert payload["overview"]["retrieved_rules"] == 2
    assert payload["overview"]["never_retrieved_rules"] == 1
    assert payload["overview"]["stale_rules"] == 1

    by_name = {item["name"]: item for item in payload["rules"]}
    assert by_name["used-rule"]["use_count"] == 3
    assert by_name["used-rule"]["last_retrieved_at"] == "2026-04-25"
    assert by_name["used-rule"]["never_retrieved_since_promotion"] is False
    assert by_name["used-rule"]["stale"] is False

    assert by_name["never-used-rule"]["never_retrieved_since_promotion"] is True
    assert by_name["never-used-rule"]["last_retrieved_at"] is None

    assert by_name["stale-rule"]["stale"] is True
    assert by_name["stale-rule"]["stale_reason"] == "unused 30d+"


def test_overview_command_reports_dashboard_metrics(monkeypatch, tmp_path: Path, capsys) -> None:
    history_path = tmp_path / "home-learning" / "history" / "promotions.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(
        json.dumps({"ts": "2026-04-20T00:00:01Z", "action": "promote", "rule": "keep-tests", "source_adapter": "codex", "decision": "new_rule"}) + "\n"
        + json.dumps({"ts": "2026-04-20T00:00:02Z", "action": "refresh", "rule": "keep-tests", "source_adapter": "codex", "decision": "refresh_existing"}) + "\n"
        + json.dumps({"ts": "2026-04-20T00:00:03Z", "action": "promote", "rule": "retry-network", "source_adapter": "claude", "decision": "new_rule"}) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "overview", "--project-root", str(tmp_path), "--format", "json"],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_entries"] == 3
    assert payload["unique_rules"] == 2
    assert payload["latest_ts"] == "2026-04-20T00:00:03Z"
    assert payload["by_action"]["promote"] == 2
    assert payload["by_adapter"]["codex"] == 2
    assert payload["by_decision"]["new_rule"] == 2


def test_dashboard_summary_and_generate_dashboard_commands(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(tmp_path / "home-learning"))
    learning_root = tmp_path / "home-learning" / "learning"
    lifecycle = LearningLifecycle(learning_root)
    lifecycle.promote(
        LearningRule(
            name="local-rule",
            rule="Update tests whenever behavior changes.",
            why="Project local rule.",
            scope="changes",
            good_pattern="Edit code and tests together.",
            avoid_pattern="Leave tests stale.",
            summary="Local rule.",
        )
    )

    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "dashboard-summary", "--project-root", str(tmp_path), "--format", "json"],
    )
    assert cli_main() == 0
    summary = json.loads(capsys.readouterr().out)
    assert "overview" in summary
    assert "history_summary" in summary
    assert "local" in summary
    assert "global" in summary
    assert "merged" in summary
    assert "candidates" in summary
    assert "recent_history" in summary
    assert "agent_learner_home" in summary["paths"]
    assert isinstance(summary["known_projects"], list)

    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "generate-dashboard", "--project-root", str(tmp_path), "--format", "json"],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert Path(payload["json_path"]).exists()
    assert Path(payload["html_path"]).exists()
    html = Path(payload["html_path"]).read_text(encoding="utf-8")
    assert "agent-learner dashboard" in html
    assert 'data-scope-toggle="merged"' in html
    assert 'data-scope-panel="global"' in html
    assert "History by Action" in html


def test_webapp_helpers_support_actions(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(tmp_path / "home-learning"))
    learning_root = tmp_path / "home-learning" / "learning"
    lifecycle = LearningLifecycle(learning_root)
    lifecycle.promote(
        LearningRule(
            name="local-rule",
            rule="Update tests whenever behavior changes.",
            why="Project local rule.",
            scope="changes",
            good_pattern="Edit code and tests together.",
            avoid_pattern="Leave tests stale.",
            summary="Local rule.",
        )
    )
    result = apply_web_action(tmp_path, "promote-global", {"name": "local-rule"})
    assert result["learning_scope"] == "global"

    html = render_dashboard_app_html(tmp_path)
    assert "/api/summary" in html
    assert "/api/promote-global" in html
    assert "/api/review-candidate" in html

    class FakeServer:
        def __init__(self, address, handler):
            self.server_address = ("127.0.0.1", 43210)
            self.handler = handler
        def server_close(self) -> None:
            return None

    monkeypatch.setattr("agent_learner.core.webapp.ThreadingHTTPServer", FakeServer)
    server, url = run_dashboard_server(tmp_path, port=0)
    assert url == "http://127.0.0.1:43210/"
    server.server_close()


def test_fastapi_frontend_scaffold_paths() -> None:
    assert app_root_dir() == Path(__file__).resolve().parents[1]
    assert (app_root_dir() / "frontend" / "package.json").exists()
    app_path = frontend_src_dir() / "App.tsx"
    components_path = frontend_src_dir() / "components.tsx"
    types_path = frontend_src_dir() / "types.ts"
    assert frontend_dist_dir().name == "frontend_dist"
    assert frontend_dist_is_valid(frontend_dist_dir())
    assert app_path.exists()
    assert components_path.exists()
    assert types_path.exists()
    app_source = app_path.read_text(encoding="utf-8")
    components_source = components_path.read_text(encoding="utf-8")
    assert "HistoryTable" in app_source
    assert "Review pending candidates first" in app_source
    assert "Action queue" in app_source
    assert "Health summary" in app_source
    assert "Exception patterns" in app_source
    assert "Automation Rate" in app_source
    assert "Exception Rate" in app_source
    assert "Recent Auto (" in app_source
    assert "Recent Exceptions (" in app_source
    assert "Rule Exception Reasons" in app_source
    assert "Candidate Exception Reasons" in app_source
    assert "Review Load" in app_source
    assert "Rule Health" in app_source
    assert "Audit Coverage" in app_source
    assert "Quiet workspace" in app_source
    assert "Nothing urgent is waiting yet" in app_source
    assert "Operator notes" in app_source
    assert "Keep rules tidy" in app_source
    assert "Candidate queues are ordered by review urgency first" in app_source
    assert "The dashboard now surfaces the unresolved reason, decision type, and provenance" in app_source
    assert "How this dashboard works" in app_source
    assert "Dashboard is for viewing and managing learned guidance" in app_source
    assert "applyFocusRing" in app_source
    assert "Reusable learning, organized for review." in app_source
    assert "Use Overview for queue health, Rules for reusable guidance, Candidates for review, and History for audit." in app_source
    assert 'aria-label={`${item.label}: ${item.value}`}' in app_source
    assert 'aria-label={`Priority ${item.priority}`}' in app_source
    assert "Skip to main content" in app_source
    assert 'aria-live="polite"' in app_source
    assert 'aria-current={page === key ? "page" : undefined}' in app_source
    assert 'aria-label="Dashboard sections"' in app_source
    assert "Promote to all projects" in components_source
    assert "Candidate Detail" in components_source
    assert "Filter history" in components_source
    assert 'role="tablist"' in components_source
    assert "View details" in components_source
    assert "denseRowTemplate" in components_source
    assert "previousFocus?.focus()" in components_source
    assert "useFocusRing" in components_source
    assert "Sorted by review urgency, then confidence, then title." in components_source
    assert "Sorted for quick reuse: strongest curated guidance first." in components_source
    assert "Needs Review" in components_source
    assert "No rules need review" in components_source
    assert "Open each item to see the unresolved reason and provenance before intervening." in components_source
    assert "Why this still needs review" in components_source
    assert "Open details to see why an item stayed in review instead of auto-applying." in components_source
    assert "No curated rules yet" in components_source
    assert "If this stays empty in a fresh workspace" in components_source
    assert "Fresh workspaces often stay empty here" in components_source
    assert "Review the primary summary first, then scan patterns, provenance, and actions." in components_source
    assert "Primary details" in components_source
    assert "No structured provenance has been recorded yet." in components_source
    assert "KeyValueGrid" in components_source
    assert 'aria-describedby={`${titleId}-description`}' in components_source
    dashboard_shell = app_root_dir() / "bin" / "dashboard.sh"
    publish_smoke_shell = app_root_dir() / "bin" / "publish-smoke.sh"
    assert dashboard_shell.exists()
    assert publish_smoke_shell.exists()
    shell_source = dashboard_shell.read_text(encoding="utf-8")
    publish_smoke_source = publish_smoke_shell.read_text(encoding="utf-8")
    assert "agent-learner dashboard" in shell_source
    assert "agent-learner doctor" in shell_source
    assert "publish_smoke_check.py" in publish_smoke_source


def test_doctor_helpers_detect_existing_dist(monkeypatch, tmp_path: Path) -> None:
    dist = frontend_dist_dir()
    original = (dist / "index.html").read_text(encoding="utf-8")
    try:
        dist.mkdir(parents=True, exist_ok=True)
        (dist / "index.html").write_text("<html></html>", encoding="utf-8")
        report = collect_dashboard_doctor(tmp_path)
        assert "ready_fastapi" in report
        assert "remediations" in report
        assert "verdict" in report
        assert "recommended_path" in report
        assert report["frontend"]["dist_valid"] is False
    finally:
        (dist / "index.html").write_text(original, encoding="utf-8")
    assert ensure_frontend_dist(tmp_path, build=False) == dist


def test_format_doctor_text_includes_next_command(tmp_path: Path) -> None:
    report = collect_dashboard_doctor(tmp_path)
    text = format_doctor_text(report)
    assert "verdict=" in text
    assert "status=" in text
    assert "next:" in text
    assert "can_run_now=" in text


def test_promote_global_command_copies_rule_to_global_learning(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(tmp_path / "home-learning"))
    learning_root = tmp_path / "home-learning" / "learning"
    lifecycle = LearningLifecycle(learning_root)
    lifecycle.promote(
        LearningRule(
            name="shared-rule",
            rule="Keep migrations reversible.",
            why="Useful across projects.",
            scope="migrations",
            good_pattern="Reversible migration path.",
            avoid_pattern="Irreversible schema changes.",
            summary="Global candidate rule.",
        )
    )

    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "promote-global", "--project-root", str(tmp_path), "--name", "shared-rule", "--format", "json"],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["learning_scope"] == "global"
    assert Path(payload["path"]).exists()


def test_sync_global_promotes_eligible_rules(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(tmp_path / "home-learning"))
    learning_root = tmp_path / "home-learning" / "learning"
    lifecycle = LearningLifecycle(learning_root)
    rule = LearningRule(
        name="eligible-rule",
        rule="Keep tests updated.",
        why="Useful across projects.",
        scope="testing",
        good_pattern="Update tests with code.",
        avoid_pattern="Leave tests stale.",
        summary="Eligible global rule.",
        promote_count=2,
        use_count=1,
    )
    lifecycle.promote(rule)

    monkeypatch.setattr(
        "sys.argv",
        [
            "agent-learner",
            "sync-global",
            "--project-root",
            str(tmp_path),
            "--min-promote-count",
            "2",
            "--min-use-count",
            "1",
            "--format",
            "json",
        ],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 1
    assert payload[0]["rule"] == "eligible-rule"


def test_merge_rules_prefers_complete_approved_rule_over_empty_local_draft() -> None:
    merged = merge_rules(
        [
            {
                "name": "shared-rule",
                "status": "draft",
                "summary": "",
                "scope": "",
                "learning_scope": "project",
                "source_project": None,
                "decision": None,
                "related_rule": None,
                "supersedes": None,
                "promote_count": 0,
                "refresh_count": 0,
                "use_count": 0,
            }
        ],
        [
            {
                "name": "shared-rule",
                "status": "approved",
                "summary": "Reusable global rule.",
                "scope": "migrations",
                "learning_scope": "global",
                "source_project": "codex-channels",
                "decision": None,
                "related_rule": None,
                "supersedes": None,
                "promote_count": 1,
                "refresh_count": 0,
                "use_count": 0,
            }
        ],
    )
    assert merged[0]["status"] == "approved"
    assert merged[0]["summary"] == "Reusable global rule."


def test_dashboard_summary_auto_reapproves_needs_review_rule_for_current_model(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    state_dir = tmp_path / ".agent-learner" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "current-model.txt").write_text("claude-sonnet-4-7\n", encoding="utf-8")

    lifecycle = LearningLifecycle(tmp_path / "home-learning" / "learning")
    rule = LearningRule(
        name="auto-reapproved",
        rule="Keep tests updated.",
        why="Verification should stay aligned with changes.",
        scope="core",
        good_pattern="Update tests with code.",
        avoid_pattern="Leave tests stale.",
        summary="Keep tests updated.",
        validated_on_models=["claude-sonnet-4-6"],
        model_dependency="low",
    )
    lifecycle.mark_needs_review(rule)

    summary = build_dashboard_summary(tmp_path)
    names = {item["name"]: item["status"] for item in summary["local"]["rules"]}
    assert names["auto-reapproved"] == "approved"


def test_dashboard_summary_categorizes_exception_reasons(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    lifecycle = LearningLifecycle(tmp_path / "home-learning" / "learning")
    rule = LearningRule(
        name="review-rule",
        rule="Update tests whenever behavior changes.",
        why="same conceptual rule but durable wording should change materially",
        scope="core",
        good_pattern="Update tests with code.",
        avoid_pattern="Leave tests stale.",
        summary="Update tests whenever behavior changes.",
        status="needs_review",
    )
    lifecycle.mark_needs_review(rule)

    candidates_dir = tmp_path / "home-learning" / "candidates" / "codex"
    candidates_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = candidates_dir / "candidate-conflict.md"
    candidate_path.write_text(
        "---\n"
        "adapter: codex\n"
        "captured_at: 2026-04-23T00:00:00Z\n"
        "source_event_path: events/codex/stop.json\n"
        "transcript_path: \n"
        "status: needs_review_candidate\n"
        "decision: fork_rule\n"
        'decision_reason: "related topic overlaps with an existing rule but safe merge is not possible"\n'
        "matched_rule: retry-network-failures\n"
        "review_required: true\n"
        "confidence: medium\n"
        "field_diffs: {}\n"
        "---\n\n"
        "# conflict\n\n"
        "## Suggested rule\n"
        "Always retry network failures when the request budget allows it.\n\n"
        "## Summary\n"
        "Retry network failures when budget allows it.\n\n"
        "## Scope\n"
        "codex adapter event:stop\n\n"
        "## Evidence\n"
        "Always retry network failures when the request budget allows it.\n",
        encoding="utf-8",
    )

    summary = build_dashboard_summary(tmp_path)
    assert summary["exception_summary"]["rule_reasons"]["wording-change"] == 1
    assert summary["exception_summary"]["candidate_reasons"]["overlap"] == 1


def test_dashboard_summary_reports_automation_metrics(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(tmp_path / "home-learning"))
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    history_path = tmp_path / "home-learning" / "history" / "promotions.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(
        "\n".join(
            [
                json.dumps({"ts": "2026-04-23T00:00:00Z", "action": "promote", "rule": "r1"}),
                json.dumps({"ts": "2026-04-23T00:01:00Z", "action": "refresh", "rule": "r1"}),
                json.dumps({"ts": "2026-04-23T00:02:00Z", "action": "candidate_created", "rule": "r2"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    candidates_dir = tmp_path / "home-learning" / "candidates" / "codex"
    candidates_dir.mkdir(parents=True, exist_ok=True)
    (candidates_dir / "candidate-review.md").write_text(
        "---\n"
        "adapter: codex\n"
        "captured_at: 2026-04-23T00:00:00Z\n"
        "source_event_path: events/codex/stop.json\n"
        "transcript_path: \n"
        "status: needs_review_candidate\n"
        "decision: revise_existing\n"
        'decision_reason: "same conceptual rule but durable wording should change materially"\n'
        "matched_rule: existing-rule\n"
        "review_required: true\n"
        "confidence: medium\n"
        "field_diffs: {}\n"
        "---\n\n"
        "# review\n\n"
        "## Suggested rule\n"
        "Update tests when behavior changes.\n\n"
        "## Summary\n"
        "Update tests when behavior changes.\n\n"
        "## Scope\n"
        "codex adapter event:stop\n\n"
        "## Evidence\n"
        "Update tests when behavior changes.\n",
        encoding="utf-8",
    )

    summary = build_dashboard_summary(tmp_path)
    assert summary["overview"]["automation_rate"] == 66.7
    assert summary["overview"]["exception_rate"] == 100.0
    assert summary["overview"]["auto_resolved_actions"] == 2
    assert summary["overview"]["pending_review_candidates"] == 1
    assert summary["overview"]["recent_window"] == 10
    assert summary["overview"]["recent_auto_rate"] == 66.7
    assert summary["overview"]["recent_exception_rate"] == 100.0
    assert summary["overview"]["recent_auto_resolved_actions"] == 2
    assert summary["overview"]["recent_pending_review_candidates"] == 1


def test_qa_claude_smoke_creates_event_and_candidate(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["agent-learner", "qa-claude-smoke"])
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["returncode"] == 0
    assert payload["event_files"]
    assert payload["candidate_files"]


def test_qa_hermes_smoke_creates_event_candidate_and_prompt_context(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["agent-learner", "qa-hermes-smoke"])
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["auto_returncode"] == 0
    assert payload["prompt_returncode"] == 0
    assert payload["event_files"]
    assert payload["candidate_files"]
    assert payload["rule_files"]
    assert payload["config_path"].endswith("/.hermes/config.yaml")
    assert payload["config_created"] is True
    assert payload["config_preserved"] is False
    assert payload["activation_hint"].startswith("HERMES_HOME=")
    assert payload["activation_hint"].endswith(" hermes --accept-hooks")
    assert "config.agent-learner.yaml" in payload["merge_hint"]
    assert payload["prompt_payload"]["context"]
    assert "active_learning" in payload["prompt_payload"]["context"]
    if payload["runtime"]["available"]:
        assert payload["runtime"]["hooks_list_returncode"] == 0
        assert payload["runtime"]["hooks_test_pre_returncode"] == 0
        assert payload["runtime"]["hooks_test_end_returncode"] == 0


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

    learning_root = tmp_path / "home-learning" / "learning"
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


def test_rebuild_index_command_outputs_paths(monkeypatch, tmp_path: Path, capsys) -> None:
    lifecycle = LearningLifecycle(tmp_path / "home-learning" / "learning")
    lifecycle.promote(
        LearningRule(
            name="index-me",
            rule="Keep index metadata current.",
            why="Retrieval should not scan every file.",
            scope="learning",
            good_pattern="Update the rule index whenever rules change.",
            avoid_pattern="Scan every file on every retrieval.",
            summary="Index rules for faster retrieval.",
        )
    )
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "rebuild-index", "--project-root", str(tmp_path), "--scope", "project", "--format", "json"],
    )
    assert cli_main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["scope"] == "project"
    assert payload[0]["total_rules"] >= 1


def test_frontend_dist_validation_rejects_blank_shell(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text("<html></html>", encoding="utf-8")
    assert frontend_dist_is_valid(dist) is False
