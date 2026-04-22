#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test published pipx / uvx / npx runtime paths.")
    parser.add_argument("--python-spec", default="agent-learner[web]", help='PyPI package spec, e.g. "agent-learner[web]"')
    parser.add_argument("--npm-spec", default="@cafitac/agent-learner", help='npm package spec, e.g. "@cafitac/agent-learner"')
    parser.add_argument("--project-root", required=True, help="Target consumer project root used for doctor/dashboard commands")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--skip-commands", action="store_true", help="Only print the command plan; do not execute")
    return parser.parse_args()


def tool_status(name: str) -> dict[str, object]:
    path = shutil.which(name)
    return {"available": bool(path), "path": path}


def build_commands(args: argparse.Namespace) -> list[list[str]]:
    project_root = args.project_root
    return [
        ["pipx", "install", args.python_spec],
        ["pipx", "run", "--spec", args.python_spec, "agent-learner", "doctor", "--project-root", project_root],
        ["uvx", "--from", args.python_spec, "agent-learner", "doctor", "--project-root", project_root],
        ["npx", args.npm_spec, "doctor"],
        ["npx", args.npm_spec, "dashboard", "--project-root", project_root],
    ]


def run_command(command: list[str]) -> dict[str, object]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return {
        "command": " ".join(command),
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout[-5000:],
        "stderr": result.stderr[-5000:],
    }


def build_report(args: argparse.Namespace) -> dict[str, object]:
    tools = {name: tool_status(name) for name in ["pipx", "uvx", "npx", "python3", "node", "npm"]}
    commands = build_commands(args)
    executed = [] if args.skip_commands else [run_command(command) for command in commands]
    ok = all(entry["available"] for entry in tools.values() if entry["path"] is not None or entry["available"] is False)
    if executed:
        ok = ok and all(entry["ok"] for entry in executed)
    advice: list[str] = []
    if not tools["pipx"]["available"]:
        advice.append("Install pipx before running the published Python package path.")
    if not tools["uvx"]["available"]:
        advice.append("Install uv so the uvx path can be verified.")
    if not tools["npx"]["available"]:
        advice.append("Install Node.js/npm so the npm wrapper path can be verified.")
    if args.skip_commands:
        advice.append("Commands were not executed; rerun without --skip-commands for a real publish smoke.")
    elif any(not item["ok"] for item in executed):
        advice.append("At least one published runtime smoke command failed. Inspect stdout/stderr in the report.")
    return {
        "ok": ok,
        "project_root": str(Path(args.project_root).resolve()),
        "python_spec": args.python_spec,
        "npm_spec": args.npm_spec,
        "tools": tools,
        "commands": [" ".join(command) for command in commands],
        "results": executed,
        "advice": advice,
    }


def print_text(report: dict[str, object]) -> None:
    print(f"published-runtime-smoke: {'ok' if report['ok'] else 'failed'}")
    print(f"project_root={report['project_root']}")
    print(f"python_spec={report['python_spec']}")
    print(f"npm_spec={report['npm_spec']}")
    print("tools:")
    for name, info in report["tools"].items():
        print(f"- {name}: {'ok' if info['available'] else 'missing'}" + (f" ({info['path']})" if info['path'] else ""))
    print("commands:")
    for command in report["commands"]:
        print(f"- {command}")
    if report["results"]:
        print("results:")
        for item in report["results"]:
            status = "ok" if item["ok"] else f"failed ({item['returncode']})"
            print(f"- {item['command']}: {status}")
    if report["advice"]:
        print("advice:")
        for item in report["advice"]:
            print(f"- {item}")


def main() -> int:
    args = parse_args()
    report = build_report(args)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
