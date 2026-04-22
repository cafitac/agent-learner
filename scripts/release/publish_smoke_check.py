#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_PATHS = [
    ROOT / "pyproject.toml",
    ROOT / "package.json",
    ROOT / "README.md",
    ROOT / "docs" / "install.md",
    ROOT / "docs" / "publish-smoke-checklist.md",
    ROOT / "bin" / "dashboard.sh",
    ROOT / "frontend" / "package.json",
    ROOT / "frontend" / "src" / "App.tsx",
    ROOT / "src" / "agent_learner" / "core" / "fastapi_app.py",
]

RECOMMENDED_COMMANDS = [
    ["npm", "test"],
    ["python3", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_pipeline.py", "tests/test_lifecycle.py", "tests/test_installers.py", "tests/test_cli_bootstrap.py", "tests/test_retrieval.py"],
    ["uv", "run", "--extra", "web", "agent-learner", "doctor", "--project-root", str(ROOT), "--format", "json"],
    ["npm", "run", "build"],
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate publish-time smoke prerequisites for dashboard UX.")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--skip-commands", action="store_true", help="skip runnable command checks")
    return parser.parse_args()


def tool_status(name: str) -> dict[str, object]:
    path = shutil.which(name)
    if not path:
        return {"available": False, "path": None}
    return {"available": True, "path": path}


def command_env(command: list[str]) -> dict[str, str] | None:
    if command[:3] == ["python3", "-m", "agent_learner.cli.main"]:
        env = os.environ.copy()
        src_path = str(ROOT / "src")
        current = env.get("PYTHONPATH")
        env["PYTHONPATH"] = src_path if not current else f"{src_path}{os.pathsep}{current}"
        return env
    return None


def run_command(command: list[str]) -> dict[str, object]:
    cwd = ROOT / "frontend" if command[:2] == ["npm", "run"] and "build" in command else ROOT
    result = subprocess.run(command, cwd=cwd, env=command_env(command), capture_output=True, text=True, check=False)
    return {
        "command": " ".join(command),
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout[-5000:],
        "stderr": result.stderr[-5000:],
    }


def build_report(skip_commands: bool) -> dict[str, object]:
    files = [{"path": str(path.relative_to(ROOT)), "exists": path.exists()} for path in REQUIRED_PATHS]
    tools = {name: tool_status(name) for name in ["npm", "node", "uv", "python3", "pipx"]}
    commands = [] if skip_commands else [run_command(command) for command in RECOMMENDED_COMMANDS]
    ok = all(entry["exists"] for entry in files) and all(info["available"] for info in tools.values() if info is not None) and all(entry["ok"] for entry in commands)
    advice: list[str] = []
    if not tools["pipx"]["available"]:
        advice.append("Install pipx so the published Python package path can be smoke-tested.")
    if not tools["uv"]["available"]:
        advice.append("Install uv so the published uvx path can be smoke-tested.")
    if not skip_commands and any(not entry["ok"] for entry in commands):
        advice.append("Fix the failing smoke commands before publishing.")
    advice.append("After publishing, run the pipx / uvx / npx checks from docs/publish-smoke-checklist.md.")
    return {
        "ok": ok,
        "files": files,
        "tools": tools,
        "commands": commands,
        "advice": advice,
    }


def print_text(report: dict[str, object]) -> None:
    print(f"publish-smoke-check: {'ok' if report['ok'] else 'failed'}")
    print("files:")
    for entry in report["files"]:
        print(f"- {entry['path']}: {'ok' if entry['exists'] else 'missing'}")
    print("tools:")
    for name, info in report["tools"].items():
        print(f"- {name}: {'ok' if info['available'] else 'missing'}" + (f" ({info['path']})" if info['path'] else ""))
    if report["commands"]:
        print("commands:")
        for entry in report["commands"]:
            status = "ok" if entry["ok"] else f"failed ({entry['returncode']})"
            print(f"- {entry['command']}: {status}")
    if report["advice"]:
        print("advice:")
        for item in report["advice"]:
            print(f"- {item}")


def main() -> int:
    args = parse_args()
    report = build_report(args.skip_commands)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
