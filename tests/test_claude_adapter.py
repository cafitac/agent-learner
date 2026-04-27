"""Tests for the refactored Claude adapter hook installation."""
from __future__ import annotations

import json
from pathlib import Path

from agent_learner.adapters.claude import install_claude_hooks


def test_install_claude_hooks_creates_settings(tmp_path: Path) -> None:
    install_claude_hooks(tmp_path, scope="project")
    settings_path = tmp_path / ".claude" / "settings.json"
    assert settings_path.exists()
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    stop_hooks = settings["hooks"]["Stop"]
    assert any("agent-learner process" in h["command"] for h in stop_hooks)


def test_install_claude_hooks_idempotent(tmp_path: Path) -> None:
    install_claude_hooks(tmp_path, scope="project")
    install_claude_hooks(tmp_path, scope="project")
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    al_hooks = [h for h in settings["hooks"]["Stop"] if "agent-learner" in h["command"]]
    assert len(al_hooks) == 1


def test_install_claude_hooks_preserves_existing(tmp_path: Path) -> None:
    existing = {"hooks": {"Stop": [{"command": "my-existing-hook"}]}}
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps(existing))
    install_claude_hooks(tmp_path, scope="project")
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    commands = [h["command"] for h in settings["hooks"]["Stop"]]
    assert "my-existing-hook" in commands
    assert any("agent-learner" in c for c in commands)


def test_install_claude_hooks_command_format(tmp_path: Path) -> None:
    install_claude_hooks(tmp_path, scope="project")
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    hook = [h for h in settings["hooks"]["Stop"] if "agent-learner" in h["command"]][0]
    assert "--adapter claude" in hook["command"]
    assert "--session-id $CLAUDE_SESSION_ID" in hook["command"]
    assert "--cwd $CWD" in hook["command"]
    assert "--model-id $CLAUDE_MODEL" in hook["command"]


def test_install_claude_hooks_user_scope(tmp_path: Path) -> None:
    home = tmp_path / "home"
    install_claude_hooks(home, scope="user")
    settings_path = home / ".claude" / "settings.json"
    assert settings_path.exists()
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert any("agent-learner" in h["command"] for h in settings["hooks"]["Stop"])
