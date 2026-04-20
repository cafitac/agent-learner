import json
from pathlib import Path

from agent_learner.adapters import install_claude_adapter, install_codex_adapter


def test_install_codex_adapter_creates_expected_assets(tmp_path: Path) -> None:
    written = install_codex_adapter(tmp_path)
    assert (tmp_path / ".codex" / "hooks.json").exists()
    assert (tmp_path / ".codex" / "skills" / "session-wrap" / "SKILL.md").exists()
    assert (tmp_path / ".codex" / "references" / "scripts" / "auto_session_learning.py").exists()
    assert (tmp_path / ".codex" / "references" / "scripts" / "codex_prompt_context.py").exists()
    assert (tmp_path / ".omx" / "wiki" / "session-log").exists()
    assert (tmp_path / ".agent-learner" / "events" / "codex").exists()
    assert written

    hooks = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    assert "UserPromptSubmit" in hooks["hooks"]
    command = hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
    assert "codex_prompt_context.py" in command


def test_install_claude_adapter_creates_expected_assets(tmp_path: Path) -> None:
    written = install_claude_adapter(tmp_path)
    assert (tmp_path / ".claude" / "settings.json").exists()
    assert (tmp_path / ".claude" / "hooks" / "auto_session_learning.py").exists()
    assert (tmp_path / ".claude" / "skills" / "session-wrap" / "SKILL.md").exists()
    assert (tmp_path / ".agent-learner" / "events" / "claude").exists()
    assert written


def test_installers_are_independent(tmp_path: Path) -> None:
    install_codex_adapter(tmp_path)
    assert not (tmp_path / ".claude").exists()
    install_claude_adapter(tmp_path)
    assert (tmp_path / ".codex").exists()
    assert (tmp_path / ".claude").exists()


def test_codex_install_adds_gitignore_lines(tmp_path: Path) -> None:
    install_codex_adapter(tmp_path)
    content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".codex/references/learning/inbox/" in content
    assert ".codex/references/learning/drafts/" in content
    assert ".omx/wiki/session-log/" in content
    assert ".agent-learner/events/" in content
    assert ".agent-learner/candidates/" in content
    assert ".agent-learner/state/" in content
