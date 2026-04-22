from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType


def load_publish_smoke_module(root: Path) -> ModuleType:
    module_path = root / "scripts" / "release" / "publish_smoke_check.py"
    spec = importlib.util.spec_from_file_location("publish_smoke_check", module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_publish_smoke_check_json_reports_structure() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "release" / "publish_smoke_check.py"), "--json", "--skip-commands"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in (0, 1)
    payload = json.loads(result.stdout)
    assert "files" in payload
    assert "tools" in payload
    assert "advice" in payload
    assert any(entry["path"] == "bin/dashboard.sh" for entry in payload["files"])


def test_publish_smoke_doctor_command_uses_source_tree_pythonpath() -> None:
    root = Path(__file__).resolve().parents[1]
    module = load_publish_smoke_module(root)

    env = module.command_env(["python3", "-m", "agent_learner.cli.main", "doctor"])
    assert env is not None
    assert str(root / "src") in env["PYTHONPATH"].split(module.os.pathsep)
    assert module.command_env(["npm", "test"]) is None


def test_publish_smoke_recommends_uv_web_doctor() -> None:
    root = Path(__file__).resolve().parents[1]
    module = load_publish_smoke_module(root)

    assert ["uv", "run", "--extra", "web", "agent-learner", "doctor", "--project-root", str(root), "--format", "json"] in module.RECOMMENDED_COMMANDS
