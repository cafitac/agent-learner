from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


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
