from pathlib import Path

from agent_learner.cli.main import main as cli_main


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
