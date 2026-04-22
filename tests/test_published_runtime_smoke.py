from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_published_runtime_smoke_json_reports_structure(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "release" / "published_runtime_smoke.py"),
            "--json",
            "--skip-commands",
            "--project-root",
            str(tmp_path),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in (0, 1)
    payload = json.loads(result.stdout)
    assert "tools" in payload
    assert "commands" in payload
    assert "advice" in payload
    assert payload["project_root"] == str(tmp_path.resolve())
