#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re

VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-a-zA-Z0-9.]+)?$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print prerelease rehearsal steps for a version.")
    parser.add_argument("version", help="version to rehearse, e.g. 0.2.0")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser.parse_args()


def validate_version(version: str) -> None:
    if not VERSION_RE.match(version):
        raise SystemExit(f"invalid version: {version}")


def build_plan(version: str) -> dict[str, object]:
    return {
        "version": version,
        "local_checks": [
            "npm test",
            "npm pack --dry-run",
            "uv run pytest -q",
            "uv build",
            "uv run agent-learner qa-codex-smoke",
            "uv run agent-learner qa-claude-smoke",
            f"python scripts/release/bump_version.py {version} --dry-run",
        ],
        "prerelease_tags": [
            {
                "tag": f"py-rc-v{version}",
                "workflow": ".github/workflows/pypi-testpypi.yml",
                "post_check": "uvx --from agent-learner --index-url https://test.pypi.org/simple agent-learner --help",
            },
            {
                "tag": f"npm-rc-v{version}",
                "workflow": ".github/workflows/npm-prerelease.yml",
                "post_check": "npx @cafibot/agent-learner@next doctor",
            },
        ],
        "final_tags": [f"v{version}", f"py-v{version}", f"npm-v{version}"],
    }


def print_text(plan: dict[str, object]) -> None:
    print(f"Prerelease rehearsal for {plan['version']}")
    print("\nLocal checks:")
    for command in plan["local_checks"]:
        print(f"- {command}")
    print("\nPrerelease tag order:")
    for step in plan["prerelease_tags"]:
        print(f"- {step['tag']} -> {step['workflow']}")
        print(f"  post-check: {step['post_check']}")
    print("\nFinal release tags:")
    for tag in plan["final_tags"]:
        print(f"- {tag}")


def main() -> int:
    args = parse_args()
    validate_version(args.version)
    plan = build_plan(args.version)
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print_text(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
