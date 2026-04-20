#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT_PATH = ROOT / "pyproject.toml"
PACKAGE_JSON_PATH = ROOT / "package.json"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-a-zA-Z0-9.]+)?$")
PRERELEASE_RC_RE = re.compile(r"^(?P<base>\d+\.\d+\.\d+)rc(?P<num>\d+)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bump Python core and npm wrapper versions together.")
    parser.add_argument("version", help="new version, e.g. 0.2.0 or 0.2.0rc1")
    parser.add_argument("--date", dest="release_date", default=date.today().isoformat(), help="release date for changelog finalization")
    parser.add_argument("--dry-run", action="store_true", help="print planned changes without writing files")
    return parser.parse_args()


def validate_version(version: str) -> None:
    if not VERSION_RE.match(version):
        raise SystemExit(f"invalid version: {version}")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str, dry_run: bool) -> None:
    if not dry_run:
        path.write_text(content, encoding="utf-8")


def bump_pyproject(version: str, dry_run: bool) -> None:
    text = read_text(PYPROJECT_PATH)
    updated = re.sub(r'(?m)^version = ".*"$', f'version = "{version}"', text, count=1)
    if updated == text:
        raise SystemExit("failed to update pyproject version")
    write_text(PYPROJECT_PATH, updated, dry_run)


def npm_version_for(version: str) -> str:
    match = PRERELEASE_RC_RE.match(version)
    if match:
        return f"{match.group('base')}-rc{match.group('num')}"
    return version


def bump_package_json(version: str, dry_run: bool) -> None:
    payload = json.loads(read_text(PACKAGE_JSON_PATH))
    payload["version"] = npm_version_for(version)
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    write_text(PACKAGE_JSON_PATH, content, dry_run)


def finalize_changelog(version: str, release_date: str, dry_run: bool) -> None:
    text = read_text(CHANGELOG_PATH)
    unreleased_header = "## [Unreleased]"
    if unreleased_header not in text:
        raise SystemExit("missing Unreleased section in CHANGELOG.md")
    release_header = f"## [{version}] - {release_date}"
    if release_header in text:
        raise SystemExit(f"CHANGELOG already contains {release_header}")
    updated = text.replace(unreleased_header, unreleased_header + "\n\n" + release_header, 1)
    write_text(CHANGELOG_PATH, updated, dry_run)


def main() -> int:
    args = parse_args()
    validate_version(args.version)
    bump_pyproject(args.version, args.dry_run)
    bump_package_json(args.version, args.dry_run)
    finalize_changelog(args.version, args.release_date, args.dry_run)
    print(json.dumps({
        "version": args.version,
        "release_date": args.release_date,
        "dry_run": args.dry_run,
        "npm_version": npm_version_for(args.version),
        "updated": [
            str(PYPROJECT_PATH.relative_to(ROOT)),
            str(PACKAGE_JSON_PATH.relative_to(ROOT)),
            str(CHANGELOG_PATH.relative_to(ROOT)),
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
