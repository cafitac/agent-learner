"""Tests for the refactored Codex adapter hook installation."""
from __future__ import annotations

import json
from pathlib import Path

from agent_learner.adapters.codex import install_codex_hooks


def test_install_codex_hooks_creates_hooks_json(tmp_path: Path) -> None:
    install_codex_hooks(tmp_path, scope="project")
    hooks_path = tmp_path / ".codex" / "hooks.json"
    assert hooks_path.exists()
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    stop_hooks = hooks["hooks"]["Stop"]
    assert any("agent-learner process" in h["command"] for h in stop_hooks)


def test_install_codex_hooks_idempotent(tmp_path: Path) -> None:
    install_codex_hooks(tmp_path, scope="project")
    install_codex_hooks(tmp_path, scope="project")
    hooks = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    al_hooks = [h for h in hooks["hooks"]["Stop"] if "agent-learner" in h["command"]]
    assert len(al_hooks) == 1


def test_install_codex_hooks_preserves_existing(tmp_path: Path) -> None:
    existing = {"hooks": {"Stop": [{"command": "my-existing-hook"}]}}
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex" / "hooks.json").write_text(json.dumps(existing))
    install_codex_hooks(tmp_path, scope="project")
    hooks = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    commands = [h["command"] for h in hooks["hooks"]["Stop"]]
    assert "my-existing-hook" in commands
    assert any("agent-learner" in c for c in commands)


def test_install_codex_hooks_command_format(tmp_path: Path) -> None:
    install_codex_hooks(tmp_path, scope="project")
    hooks = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    hook = [h for h in hooks["hooks"]["Stop"] if "agent-learner" in h["command"]][0]
    assert "--adapter codex" in hook["command"]
    assert "--session-id $CODEX_SESSION_ID" in hook["command"]
    assert "--cwd $CWD" in hook["command"]
    assert "--model-id $CODEX_MODEL" in hook["command"]


def test_install_codex_hooks_user_scope(tmp_path: Path) -> None:
    home = tmp_path / "home"
    install_codex_hooks(home, scope="user")
    hooks_path = home / ".codex" / "hooks.json"
    assert hooks_path.exists()
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    assert any("agent-learner" in h["command"] for h in hooks["hooks"]["Stop"])
