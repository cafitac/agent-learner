from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_release_check_json_reports_ok() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / 'scripts' / 'release' / 'release_check.py'), '--json', '--skip-commands', '--version', '0.2.0'],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload['ok'] is True
    assert payload['version'] == '0.2.0'
    assert any(entry['path'] == 'pyproject.toml' for entry in payload['files'])
    assert payload['tools']['python3']['available'] is True


def test_release_check_rejects_bad_version() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / 'scripts' / 'release' / 'release_check.py'), '--json', '--skip-commands', '--version', 'v0.2'],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload['ok'] is False
    assert payload['version_issues']
