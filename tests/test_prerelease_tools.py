from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_prerelease_checklist_json_contains_expected_tags() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "release" / "prerelease_checklist.py"), "0.2.0", "--json"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["version"] == "0.2.0"
    assert payload["prerelease_tags"][0]["tag"] == "py-rc-v0.2.0"
    assert payload["prerelease_tags"][1]["tag"] == "npm-rc-v0.2.0"
    assert payload["final_tags"] == ["v0.2.0", "py-v0.2.0", "npm-v0.2.0"]
