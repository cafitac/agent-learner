#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_PATHS = [
    ROOT / 'pyproject.toml',
    ROOT / 'package.json',
    ROOT / 'CHANGELOG.md',
    ROOT / '.github' / 'workflows' / 'release.yml',
    ROOT / '.github' / 'workflows' / 'pypi-publish.yml',
    ROOT / '.github' / 'workflows' / 'npm-publish.yml',
]
RECOMMENDED_COMMANDS = [
    ['npm', 'test'],
    ['npm', 'pack', '--dry-run'],
    ['uv', 'run', 'pytest', '-q'],
    ['uv', 'build'],
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Validate release prerequisites before pushing tags.')
    parser.add_argument('--version', help='optional version to validate against release tag shapes')
    parser.add_argument('--json', action='store_true', help='emit machine-readable JSON')
    parser.add_argument('--skip-commands', action='store_true', help='skip runnable command checks and only inspect files/tools')
    return parser.parse_args()


def validate_version(version: str | None) -> list[str]:
    if not version:
        return []
    issues: list[str] = []
    if version.startswith('v'):
        issues.append('version should be plain X.Y.Z without a leading v')
    pieces = version.split('.')
    if len(pieces) < 3:
        issues.append('version should look like X.Y.Z')
    return issues


def tool_status(name: str) -> dict[str, object]:
    path = shutil.which(name)
    if not path:
        return {'available': False, 'path': None}
    return {'available': True, 'path': path}


def run_command(command: list[str]) -> dict[str, object]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return {
        'command': ' '.join(command),
        'ok': result.returncode == 0,
        'returncode': result.returncode,
        'stdout': result.stdout[-5000:],
        'stderr': result.stderr[-5000:],
    }


def build_report(version: str | None, skip_commands: bool) -> dict[str, object]:
    files = [{'path': str(path.relative_to(ROOT)), 'exists': path.exists()} for path in REQUIRED_PATHS]
    tools = {name: tool_status(name) for name in ['npm', 'node', 'uv', 'python3']}
    version_issues = validate_version(version)
    commands = [] if skip_commands else [run_command(command) for command in RECOMMENDED_COMMANDS]
    ok = all(entry['exists'] for entry in files) and all(info['available'] for info in tools.values()) and not version_issues and all(entry['ok'] for entry in commands)
    advice: list[str] = []
    if version:
        advice.extend([f'git tag v{version}', f'git tag py-v{version}', f'git tag npm-v{version}'])
    if not tools['uv']['available']:
        advice.append('Install uv before attempting release commands.')
    if any(not entry['exists'] for entry in files):
        advice.append('Restore missing release/config files before tagging a release.')
    if not skip_commands and any(not entry['ok'] for entry in commands):
        advice.append('Fix failing local checks before pushing any release tags.')
    return {
        'ok': ok,
        'version': version,
        'files': files,
        'tools': tools,
        'commands': commands,
        'version_issues': version_issues,
        'advice': advice,
    }


def print_text(report: dict[str, object]) -> None:
    print(f"release-check: {'ok' if report['ok'] else 'failed'}")
    if report['version']:
        print(f"version: {report['version']}")
    print('files:')
    for entry in report['files']:
        print(f"- {entry['path']}: {'ok' if entry['exists'] else 'missing'}")
    print('tools:')
    for name, info in report['tools'].items():
        print(f"- {name}: {'ok' if info['available'] else 'missing'}" + (f" ({info['path']})" if info['path'] else ''))
    if report['version_issues']:
        print('version issues:')
        for issue in report['version_issues']:
            print(f"- {issue}")
    if report['commands']:
        print('commands:')
        for entry in report['commands']:
            status = 'ok' if entry['ok'] else f"failed ({entry['returncode']})"
            print(f"- {entry['command']}: {status}")
    if report['advice']:
        print('advice:')
        for item in report['advice']:
            print(f"- {item}")


def main() -> int:
    args = parse_args()
    report = build_report(args.version, args.skip_commands)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
