import json
from pathlib import Path

from agent_learner.adapters import install_claude_adapter, install_codex_adapter, install_hermes_adapter
from agent_learner.adapters.claude import install_claude_adapter_with_scope as install_claude_adapter_with_scope
from agent_learner.adapters.codex import install_codex_adapter_with_scope
from agent_learner.adapters.hermes import install_hermes_adapter_with_scope
from agent_learner.core.storage import global_learning_root, read_project_registry, register_project, resolve_learning_root, should_register_project, storage_migration_marker_path


def test_install_codex_adapter_creates_expected_assets(tmp_path: Path) -> None:
    written = install_codex_adapter(tmp_path)
    assert (tmp_path / ".codex" / "hooks.json").exists()
    assert (tmp_path / ".codex" / "skills" / "session-wrap" / "SKILL.md").exists()
    assert (tmp_path / ".codex" / "references" / "scripts" / "auto_session_learning.py").exists()
    assert (tmp_path / ".codex" / "references" / "scripts" / "codex_prompt_context.py").exists()
    assert (tmp_path / ".agent-learner" / "learning").exists()
    assert (tmp_path / ".agent-learner" / "events" / "codex").exists()
    assert (tmp_path / ".agent-learner" / "history").exists()
    assert not (tmp_path / ".omx").exists()
    assert written

    hooks = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    assert "UserPromptSubmit" in hooks["hooks"]
    prompt_hook = hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    command = prompt_hook["command"]
    assert "codex_prompt_context.py" in command
    assert prompt_hook["statusMessage"] == "AgentLearner: applying learned context"
    stop_hook = hooks["hooks"]["Stop"][0]["hooks"][0]
    assert stop_hook["statusMessage"] == "AgentLearner: capturing learning candidates"
    auto_script = (tmp_path / ".codex" / "references" / "scripts" / "auto_session_learning.py").read_text(encoding="utf-8")
    prompt_script = (tmp_path / ".codex" / "references" / "scripts" / "codex_prompt_context.py").read_text(encoding="utf-8")
    assert ".omx/wiki" not in auto_script
    assert 'base = [cli, "core"] if cli else [sys.executable, "-m", "agent_learner.cli.main"]' in auto_script
    assert '[cli, "core", "render-codex-context"' in prompt_script


def test_install_codex_adapter_user_scope_creates_user_assets_only(tmp_path: Path) -> None:
    home_root = tmp_path / "home"
    written = install_codex_adapter_with_scope(home_root, scope="user")
    hooks_path = home_root / ".codex" / "hooks.json"
    assert hooks_path.exists()
    assert (home_root / ".codex" / "skills" / "session-wrap" / "SKILL.md").exists()
    assert not (home_root / ".agent-learner" / "learning").exists()
    assert not (home_root / ".gitignore").exists()
    assert written

    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    prompt_hook = hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    command = prompt_hook["command"]
    assert str(home_root / ".codex" / "references" / "scripts" / "codex_prompt_context.py") in command
    assert prompt_hook["statusMessage"] == "AgentLearner: applying learned context"


def test_install_claude_adapter_creates_expected_assets(tmp_path: Path) -> None:
    written = install_claude_adapter(tmp_path)
    assert (tmp_path / ".claude" / "settings.json").exists()
    assert (tmp_path / ".claude" / "hooks" / "auto_session_learning.py").exists()
    assert (tmp_path / ".claude" / "skills" / "session-wrap" / "SKILL.md").exists()
    assert (tmp_path / ".agent-learner" / "events" / "claude").exists()
    auto_script = (tmp_path / ".claude" / "hooks" / "auto_session_learning.py").read_text(encoding="utf-8")
    assert 'base = [cli, "core"] if cli else [sys.executable, "-m", "agent_learner.cli.main"]' in auto_script
    assert written


def test_install_claude_adapter_user_scope_creates_user_assets_only(tmp_path: Path) -> None:
    home_root = tmp_path / "home"
    written = install_claude_adapter_with_scope(home_root, scope="user")
    settings_path = home_root / ".claude" / "settings.json"
    assert settings_path.exists()
    assert (home_root / ".claude" / "hooks" / "auto_session_learning.py").exists()
    assert (home_root / ".claude" / "skills" / "session-wrap" / "SKILL.md").exists()
    assert not (home_root / ".agent-learner" / "events").exists()
    assert not (home_root / ".claude" / "learned-feedback").exists()
    assert written

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    hook_cmd = settings["hooks"]["SessionEnd"][0]["hooks"][0]["command"]
    assert str(home_root / ".claude" / "hooks" / "auto_session_learning.py") in hook_cmd
    assert settings["hooks"]["SessionEnd"][0]["hooks"][0]["timeout"] == 30


def test_install_hermes_adapter_creates_expected_assets(tmp_path: Path) -> None:
    written = install_hermes_adapter(tmp_path)
    hermes_root = tmp_path / ".hermes"
    assert not (tmp_path / ".agent-learner" / "events" / "hermes").exists()
    assert (hermes_root / "hooks" / "auto_session_learning.py").exists()
    assert (hermes_root / "hooks" / "hermes_prompt_context.py").exists()
    assert (hermes_root / "config.yaml").exists()
    assert (hermes_root / "config.agent-learner.yaml").exists()
    assert (hermes_root / "AGENT_LEARNER_README.md").exists()
    assert not (tmp_path / ".codex").exists()
    assert not (tmp_path / ".claude").exists()
    assert written

    config_text = (hermes_root / "config.yaml").read_text(encoding="utf-8")
    auto_script = (hermes_root / "hooks" / "auto_session_learning.py").read_text(encoding="utf-8")
    prompt_script = (hermes_root / "hooks" / "hermes_prompt_context.py").read_text(encoding="utf-8")
    assert "pre_llm_call" in config_text
    assert "on_session_end" in config_text
    assert "./.hermes/hooks/hermes_prompt_context.py" in config_text
    assert "./.hermes/hooks/auto_session_learning.py" in config_text
    assert '--adapter", "hermes"' in auto_script
    assert '--event-name' in auto_script
    assert '"process-events", "--project-root", str(project_root), "--adapter", "hermes", "--limit", "1"' in auto_script
    assert "session_{session_id}.json" in auto_script
    assert 'extra.get("user_message")' in prompt_script
    assert 'render-hermes-context' in prompt_script
    assert '--adapter", "hermes"' not in prompt_script


def test_install_hermes_user_scope_merges_hooks_into_existing_config_without_duplicates(tmp_path: Path) -> None:
    hermes_root = tmp_path / ".hermes"
    hermes_root.mkdir(parents=True, exist_ok=True)
    config_path = hermes_root / "config.yaml"
    config_path.write_text(
        "model:\n"
        "  provider: openai-codex\n"
        "hooks:\n"
        "  pre_llm_call:\n"
        "    - command: 'python existing-hook.py'\n"
        "      timeout: 5\n"
        "hooks_auto_accept: false\n",
        encoding="utf-8",
    )

    first_written = install_hermes_adapter_with_scope(tmp_path, scope="user")
    second_written = install_hermes_adapter_with_scope(tmp_path, scope="user")

    config_text = config_path.read_text(encoding="utf-8")
    assert "provider: openai-codex" in config_text
    assert "python existing-hook.py" in config_text
    assert config_text.count("hermes_prompt_context.py") == 1
    assert config_text.count("auto_session_learning.py") == 1
    assert "hooks_auto_accept: false" in config_text
    assert (hermes_root / "config.agent-learner.yaml").exists()
    assert (hermes_root / "config.yaml.agent-learner.bak").exists()
    assert first_written
    assert second_written


def test_install_hermes_user_scope_preserves_compact_yaml_hook_indentation(tmp_path: Path) -> None:
    hermes_root = tmp_path / ".hermes"
    hermes_root.mkdir(parents=True, exist_ok=True)
    config_path = hermes_root / "config.yaml"
    config_path.write_text(
        "model:\n"
        "  provider: openai-codex\n"
        "hooks:\n"
        "  pre_llm_call:\n"
        "  - command: /tmp/existing_prompt.py\n"
        "    timeout: 5\n"
        "hooks_auto_accept: false\n",
        encoding="utf-8",
    )

    install_hermes_adapter_with_scope(tmp_path, scope="user")
    install_hermes_adapter_with_scope(tmp_path, scope="user")

    config_text = config_path.read_text(encoding="utf-8")
    assert config_text.count("hermes_prompt_context.py") == 1
    assert config_text.count("auto_session_learning.py") == 1
    assert "  - command: /tmp/existing_prompt.py" in config_text
    assert config_text.count("  - command: /tmp/existing_prompt.py") == 1
    assert "    - command: '/tmp/existing_prompt.py'" not in config_text


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

    migrated_rule = global_learning_root() / "approved" / "legacy-rule.md"
    assert migrated_rule.exists()
    assert storage_migration_marker_path(tmp_path).exists()
    assert resolve_learning_root(tmp_path) == global_learning_root()
    assert migrated_rule in written


def test_resolve_learning_root_migrates_legacy_assets_into_global_root(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(tmp_path / "home"))
    legacy_rule = tmp_path / ".codex" / "references" / "learning" / "approved" / "legacy-rule.md"
    legacy_rule.parent.mkdir(parents=True, exist_ok=True)
    legacy_rule.write_text("legacy", encoding="utf-8")
    canonical_rule = tmp_path / ".agent-learner" / "learning" / "approved" / "canonical-rule.md"
    canonical_rule.parent.mkdir(parents=True, exist_ok=True)
    canonical_rule.write_text("canonical", encoding="utf-8")

    resolved = resolve_learning_root(tmp_path)

    assert resolved == global_learning_root()
    assert (global_learning_root() / "approved" / "legacy-rule.md").exists()
    assert (global_learning_root() / "approved" / "canonical-rule.md").exists()
    assert storage_migration_marker_path(tmp_path).exists()


def test_should_register_project_rejects_pytest_temp_paths(tmp_path: Path) -> None:
    fake = tmp_path / "pytest-of-user" / "pytest-1" / "test_dashboard_summary_auto_re0"
    fake.mkdir(parents=True, exist_ok=True)
    assert should_register_project(fake) is False


def test_register_project_skips_pytest_temp_paths(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AGENT_LEARNER_HOME", str(tmp_path / "home"))
    fake = tmp_path / "pytest-of-user" / "pytest-1" / "test_dashboard_summary_auto_re0"
    fake.mkdir(parents=True, exist_ok=True)
    register_project(fake)
    assert read_project_registry() == []
