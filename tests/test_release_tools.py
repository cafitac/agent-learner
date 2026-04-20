from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_bump_version_dry_run_reports_expected_files() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "release" / "bump_version.py"), "9.9.9", "--dry-run", "--date", "2026-04-21"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["version"] == "9.9.9"
    assert payload["dry_run"] is True
    assert payload["updated"] == ["pyproject.toml", "package.json", "CHANGELOG.md"]


def test_bump_version_dry_run_reports_npm_semver_for_rc() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "release" / "bump_version.py"), "9.9.9rc1", "--dry-run", "--date", "2026-04-21"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["npm_version"] == "9.9.9-rc1"
