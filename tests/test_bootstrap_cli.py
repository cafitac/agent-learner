"""Tests for the bootstrap CLI command."""
from __future__ import annotations

import json
from pathlib import Path

from agent_learner.cli.main import build_parser, main as cli_main


def _invoke(args: list[str]) -> int:
    """Run CLI and return exit code."""
    parser = build_parser()
    parsed = parser.parse_args(args)
    # We need to call main() indirectly; use subprocess-free approach
    import sys
    old_argv = sys.argv
    sys.argv = ["agent-learner"] + args
    try:
        return cli_main()
    finally:
        sys.argv = old_argv


def test_bootstrap_detects_hermit(tmp_path: Path) -> None:
    (tmp_path / ".hermit").mkdir()
    _invoke(["bootstrap", "--target", str(tmp_path), "--adapters", "auto"])
    settings_path = tmp_path / ".hermit" / "settings.json"
    assert settings_path.exists()
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert any("agent-learner" in h["command"] for h in settings["hooks"]["OnStop"])


def test_bootstrap_detects_claude(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    _invoke(["bootstrap", "--target", str(tmp_path), "--adapters", "auto", "--claude-scope", "project"])
    settings_path = tmp_path / ".claude" / "settings.json"
    assert settings_path.exists()


def test_bootstrap_detects_codex(tmp_path: Path) -> None:
    (tmp_path / ".codex").mkdir()
    _invoke(["bootstrap", "--target", str(tmp_path), "--adapters", "auto"])
    hooks_path = tmp_path / ".codex" / "hooks.json"
    assert hooks_path.exists()


def test_bootstrap_detects_all_three(tmp_path: Path) -> None:
    (tmp_path / ".hermit").mkdir()
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".codex").mkdir()
    _invoke(["bootstrap", "--target", str(tmp_path), "--adapters", "auto", "--claude-scope", "project"])
    assert (tmp_path / ".hermit" / "settings.json").exists()
    assert (tmp_path / ".claude" / "settings.json").exists()
    assert (tmp_path / ".codex" / "hooks.json").exists()


def test_bootstrap_idempotent(tmp_path: Path) -> None:
    (tmp_path / ".hermit").mkdir()
    _invoke(["bootstrap", "--target", str(tmp_path), "--adapters", "auto"])
    _invoke(["bootstrap", "--target", str(tmp_path), "--adapters", "auto"])
    settings = json.loads((tmp_path / ".hermit" / "settings.json").read_text(encoding="utf-8"))
    al_hooks = [h for h in settings["hooks"]["OnStop"] if "agent-learner" in h["command"]]
    assert len(al_hooks) == 1


def test_init_creates_directory_structure(tmp_path: Path) -> None:
    _invoke(["init", "--root", str(tmp_path / ".agent-learner")])
    assert (tmp_path / ".agent-learner" / "approved").exists()
    assert (tmp_path / ".agent-learner" / "drafts").exists()


def test_bootstrap_no_harness_creates_nothing(tmp_path: Path) -> None:
    _invoke(["bootstrap", "--target", str(tmp_path), "--adapters", "auto"])
    assert not (tmp_path / ".hermit").exists()
    assert not (tmp_path / ".claude").exists()
    assert not (tmp_path / ".codex").exists()
