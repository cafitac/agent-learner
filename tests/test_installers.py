import json
from pathlib import Path

from agent_learner.adapters import install_claude_adapter, install_codex_adapter
from agent_learner.core.storage import resolve_learning_root, storage_migration_marker_path


def test_install_codex_adapter_creates_expected_assets(tmp_path: Path) -> None:
    written = install_codex_adapter(tmp_path)
    assert (tmp_path / ".codex" / "hooks.json").exists()
    assert (tmp_path / ".codex" / "skills" / "session-wrap" / "SKILL.md").exists()
    assert (tmp_path / ".codex" / "references" / "scripts" / "auto_session_learning.py").exists()
    assert (tmp_path / ".codex" / "references" / "scripts" / "codex_prompt_context.py").exists()
    assert (tmp_path / ".agent-learner" / "learning").exists()
    assert (tmp_path / ".agent-learner" / "events" / "codex").exists()
    assert (tmp_path / ".agent-learner" / "history").exists()
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
    assert ".agent-learner/learning/inbox/" in content
    assert ".agent-learner/learning/drafts/" in content
    assert ".agent-learner/history/" in content
    assert ".agent-learner/events/" in content
    assert ".agent-learner/candidates/" in content
    assert ".agent-learner/state/" in content


def test_install_codex_adapter_migrates_legacy_learning_assets(tmp_path: Path) -> None:
    legacy_rule = tmp_path / ".codex" / "references" / "learning" / "approved" / "legacy-rule.md"
    legacy_rule.parent.mkdir(parents=True, exist_ok=True)
    legacy_rule.write_text(
        "---\nname: legacy-rule\ndescription: legacy rule\ntype: learned-feedback\nstatus: approved\n---\n\n## Rule\nKeep tests updated.\n",
        encoding="utf-8",
    )

    written = install_codex_adapter(tmp_path)

    migrated_rule = tmp_path / ".agent-learner" / "learning" / "approved" / "legacy-rule.md"
    assert migrated_rule.exists()
    assert storage_migration_marker_path(tmp_path).exists()
    assert resolve_learning_root(tmp_path) == tmp_path / ".agent-learner" / "learning"
    assert migrated_rule in written


def test_resolve_learning_root_prefers_legacy_until_migration_marker(tmp_path: Path) -> None:
    legacy_rule = tmp_path / ".codex" / "references" / "learning" / "approved" / "legacy-rule.md"
    legacy_rule.parent.mkdir(parents=True, exist_ok=True)
    legacy_rule.write_text("legacy", encoding="utf-8")
    canonical_rule = tmp_path / ".agent-learner" / "learning" / "approved" / "canonical-rule.md"
    canonical_rule.parent.mkdir(parents=True, exist_ok=True)
    canonical_rule.write_text("canonical", encoding="utf-8")

    assert resolve_learning_root(tmp_path) == tmp_path / ".codex" / "references" / "learning"
