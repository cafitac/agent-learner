"""Tests for the Hermit adapter (adapters/hermit.py)."""
from __future__ import annotations

import json
from pathlib import Path

from agent_learner.adapters.hermit import emit_session_event, install_hermit_hooks


def test_install_hooks_creates_settings_file(tmp_path: Path) -> None:
    install_hermit_hooks(tmp_path, scope="project")
    settings_path = tmp_path / ".hermit" / "settings.json"
    assert settings_path.exists()
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    hooks = settings["hooks"]["OnStop"]
    assert any("agent-learner process" in h["command"] for h in hooks)


def test_install_hooks_idempotent(tmp_path: Path) -> None:
    install_hermit_hooks(tmp_path, scope="project")
    install_hermit_hooks(tmp_path, scope="project")
    settings = json.loads((tmp_path / ".hermit" / "settings.json").read_text(encoding="utf-8"))
    al_hooks = [h for h in settings["hooks"]["OnStop"] if "agent-learner" in h["command"]]
    assert len(al_hooks) == 1


def test_install_hooks_preserves_existing_hooks(tmp_path: Path) -> None:
    existing = {"hooks": {"OnStop": [{"command": "my-other-hook"}]}}
    (tmp_path / ".hermit").mkdir()
    (tmp_path / ".hermit" / "settings.json").write_text(json.dumps(existing))
    install_hermit_hooks(tmp_path, scope="project")
    settings = json.loads((tmp_path / ".hermit" / "settings.json").read_text(encoding="utf-8"))
    commands = [h["command"] for h in settings["hooks"]["OnStop"]]
    assert "my-other-hook" in commands
    assert any("agent-learner" in c for c in commands)


def test_install_hooks_user_scope(tmp_path: Path) -> None:
    home = tmp_path / "home"
    install_hermit_hooks(home, scope="user")
    settings_path = home / ".hermit" / "settings.json"
    assert settings_path.exists()
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    hooks = settings["hooks"]["OnStop"]
    assert any("agent-learner process" in h["command"] for h in hooks)


def test_install_hooks_command_contains_hermit_adapter(tmp_path: Path) -> None:
    install_hermit_hooks(tmp_path, scope="project")
    settings = json.loads((tmp_path / ".hermit" / "settings.json").read_text(encoding="utf-8"))
    hook = [h for h in settings["hooks"]["OnStop"] if "agent-learner" in h["command"]][0]
    assert "--adapter hermit" in hook["command"]
    assert "--session-id $HERMIT_SESSION_ID" in hook["command"]
    assert "--cwd $CWD" in hook["command"]
    assert "--model-id $HERMIT_MODEL_ID" in hook["command"]


def test_emit_session_event_creates_file(tmp_path: Path) -> None:
    path = emit_session_event(
        tmp_path,
        session_id="test-123",
        cwd=str(tmp_path),
        model_id="glm-5.1",
        outcome="success",
        tool_call_count=10,
    )
    assert path.exists()
    event = json.loads(path.read_text(encoding="utf-8"))
    assert event["adapter"] == "hermit"
    assert event["event_name"] == "session_end"
    assert event["session_id"] == "test-123"
    assert event["payload"]["outcome"] == "success"
    assert event["payload"]["tool_call_count"] == 10
    assert event["payload"]["model_id"] == "glm-5.1"


def test_emit_session_event_creates_events_dir(tmp_path: Path) -> None:
    emit_session_event(
        tmp_path,
        session_id="s1",
        cwd=str(tmp_path),
        model_id="test-model",
        outcome="failure",
        tool_call_count=3,
    )
    assert (tmp_path / ".agent-learner" / "events" / "hermit").exists()
