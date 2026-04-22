import json
from pathlib import Path

from agent_learner.core.doctor import collect_dashboard_doctor, ensure_frontend_dist, format_doctor_text
from agent_learner.core.fastapi_app import app_root_dir, frontend_dist_dir, frontend_src_dir
from agent_learner.cli.main import main as cli_main
from agent_learner.core.lifecycle import LearningLifecycle
from agent_learner.core.models import LearningRule
from agent_learner.core.webapp import apply_web_action, render_dashboard_app_html, run_dashboard_server


def test_bootstrap_codex_only(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "bootstrap", "--target", str(tmp_path), "--adapters", "codex"],
    )
    assert cli_main() == 0
    assert (tmp_path / ".codex" / "hooks.json").exists()
    assert (tmp_path / ".agent-learner" / "learning").exists()
    assert not (tmp_path / ".claude").exists()


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


def test_bootstrap_migrates_legacy_codex_learning_assets(monkeypatch, tmp_path: Path) -> None:
    legacy_rule = tmp_path / ".codex" / "references" / "learning" / "approved" / "legacy-rule.md"
    legacy_rule.parent.mkdir(parents=True, exist_ok=True)
    legacy_rule.write_text(
        "---\nname: legacy-rule\ndescription: legacy rule\ntype: learned-feedback\nstatus: approved\n---\n\n## Rule\nKeep tests updated.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        ["agent-learner", "bootstrap", "--target", str(tmp_path), "--adapters", "codex"],
    )
    assert cli_main() == 0
    assert (tmp_path / ".agent-learner" / "learning" / "approved" / "legacy-rule.md").exists()
    assert (tmp_path / ".agent-learner" / "state" / "storage-migration.json").exists()


def test_render_codex_context_command_outputs_hook_json(monkeypatch, tmp_path: Path, capsys) -> None:
    lifecycle = LearningLifecycle(tmp_path / ".agent-learner" / "learning")
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
    lifecycle = LearningLifecycle(tmp_path / ".agent-learner" / "learning")
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
    assert payload[0]["status"] == "rule_promoted"


def test_review_candidates_and_approve_candidate_commands(monkeypatch, tmp_path: Path, capsys) -> None:
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(json.dumps({"message": "Always update tests whenever behavior changes in services."}) + "\n", encoding="utf-8")
    event_dir = tmp_path / ".agent-learner" / "events" / "codex"
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


def test_history_command_filters_entries(monkeypatch, tmp_path: Path, capsys) -> None:
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(json.dumps({"message": "Always keep tests updated in services."}) + "\n", encoding="utf-8")
    event_dir = tmp_path / ".agent-learner" / "events" / "codex"
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


def test_history_command_supports_latest_per_rule(monkeypatch, tmp_path: Path, capsys) -> None:
    history_path = tmp_path / ".agent-learner" / "history" / "promotions.jsonl"
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
    history_path = tmp_path / ".agent-learner" / "history" / "promotions.jsonl"
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


def test_overview_command_reports_dashboard_metrics(monkeypatch, tmp_path: Path, capsys) -> None:
    history_path = tmp_path / ".agent-learner" / "history" / "promotions.jsonl"
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
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(tmp_path / "home-brain"))
    learning_root = tmp_path / ".agent-learner" / "learning"
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
    assert summary["known_projects"]

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
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(tmp_path / "home-brain"))
    learning_root = tmp_path / ".agent-learner" / "learning"
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
    assert result["brain_scope"] == "global"

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
    assert app_path.exists()
    assert components_path.exists()
    assert types_path.exists()
    app_source = app_path.read_text(encoding="utf-8")
    components_source = components_path.read_text(encoding="utf-8")
    assert "HistoryTable" in app_source
    assert "Promote to all projects" in components_source
    assert "Candidate Detail" in components_source
    assert "Filter history" in components_source
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
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text("<html></html>", encoding="utf-8")
    report = collect_dashboard_doctor(tmp_path)
    assert "ready_fastapi" in report
    assert "remediations" in report
    assert "verdict" in report
    assert "recommended_path" in report
    assert ensure_frontend_dist(tmp_path, build=False) == dist


def test_format_doctor_text_includes_next_command(tmp_path: Path) -> None:
    report = collect_dashboard_doctor(tmp_path)
    text = format_doctor_text(report)
    assert "verdict=" in text
    assert "status=" in text
    assert "next:" in text
    assert "can_run_now=" in text


def test_promote_global_command_copies_rule_to_global_brain(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(tmp_path / "home-brain"))
    learning_root = tmp_path / ".agent-learner" / "learning"
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
    assert payload["brain_scope"] == "global"
    assert Path(payload["path"]).exists()


def test_sync_global_promotes_eligible_rules(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(tmp_path / "home-brain"))
    learning_root = tmp_path / ".agent-learner" / "learning"
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

    learning_root = tmp_path / ".agent-learner" / "learning"
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
