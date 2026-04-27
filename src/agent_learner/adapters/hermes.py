from __future__ import annotations

import shlex
import sys
from pathlib import Path

from .common import append_lines_if_missing, ensure_dir, write_text

AUTO_SESSION_LEARNING = """#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def read_json() -> dict:
    try:
        if sys.stdin.isatty():
            return {}
    except Exception:
        return {}
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def run_shared_cli(project_root: Path, argv: list[str], payload: dict | None = None) -> None:
    if importlib.util.find_spec("agent_learner") is not None:
        base = [sys.executable, "-m", "agent_learner.cli.main"]
    else:
        cli = shutil.which("agent-learner")
        base = [cli, "core"] if cli else [sys.executable, "-m", "agent_learner.cli.main"]
    try:
        subprocess.run(base + argv, input=json.dumps(payload or {}), capture_output=True, text=True, check=False, timeout=30)
    except (subprocess.TimeoutExpired, Exception):
        return


def detect_project_root(cwd: Path) -> Path:
    current = cwd.resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(current),
            capture_output=True,
            text=True,
            check=False,
        )
        root = (result.stdout or "").strip()
        if result.returncode == 0 and root:
            return Path(root).resolve()
    except Exception:
        pass
    for _ in range(20):
        if any((current / marker).exists() for marker in ("pyproject.toml", "package.json", "go.mod", "Cargo.toml", ".git")):
            return current
        if current.parent == current:
            break
        current = current.parent
    return cwd.resolve()


def detect_hermes_home(cwd: Path) -> Path:
    env_home = os.environ.get("HERMES_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()
    project_home = cwd / ".hermes"
    if project_home.exists():
        return project_home.resolve()
    return (Path.home() / ".hermes").resolve()


def resolve_transcript_path(payload: dict, *, cwd: Path, session_id: str) -> Path | None:
    extra = payload.get("extra") if isinstance(payload.get("extra"), dict) else {}
    nested_extra = extra.get("extra") if isinstance(extra.get("extra"), dict) else {}
    explicit = (
        payload.get("transcript_path")
        or payload.get("transcriptPath")
        or extra.get("transcript_path")
        or extra.get("transcriptPath")
        or nested_extra.get("transcript_path")
        or nested_extra.get("transcriptPath")
    )
    if isinstance(explicit, str) and explicit.strip():
        candidate = Path(explicit).expanduser()
        if not candidate.is_absolute():
            candidate = cwd / candidate
        if candidate.exists():
            return candidate.resolve()

    hermes_home = detect_hermes_home(cwd)
    sessions_dir = hermes_home / "sessions"
    for name in (
        f"{session_id}.json",
        f"{session_id}.jsonl",
        f"session_{session_id}.json",
        f"session_{session_id}.jsonl",
    ):
        candidate = sessions_dir / name
        if candidate.exists():
            return candidate.resolve()
    return None


def emit_shared_event(project_root: Path, payload: dict, session_id: str, transcript_path: Path | None) -> None:
    argv = [
        "capture-event",
        "--project-root",
        str(project_root),
        "--adapter",
        "hermes",
        "--event-name",
        "session_end",
        "--session-id",
        session_id,
    ]
    if transcript_path is not None:
        argv.extend(["--transcript-path", str(transcript_path)])
    run_shared_cli(project_root, argv, payload)
    run_shared_cli(project_root, ["process-events", "--project-root", str(project_root), "--adapter", "hermes", "--limit", "1"], None)


def main() -> int:
    payload = read_json()
    cwd = Path(payload.get("cwd") or os.getcwd()).resolve()
    project_root = detect_project_root(cwd)
    session_id = payload.get("session_id") or datetime.now().strftime("%Y%m%d-%H%M%S")
    transcript_path = resolve_transcript_path(payload, cwd=cwd, session_id=session_id)
    emit_shared_event(project_root, payload, session_id, transcript_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""

PROMPT_CONTEXT = """#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def read_json() -> dict:
    try:
        if sys.stdin.isatty():
            return {}
    except Exception:
        return {}
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def detect_project_root(cwd: Path) -> Path:
    current = cwd.resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(current),
            capture_output=True,
            text=True,
            check=False,
        )
        root = (result.stdout or "").strip()
        if result.returncode == 0 and root:
            return Path(root).resolve()
    except Exception:
        pass
    for _ in range(20):
        if any((current / marker).exists() for marker in ("pyproject.toml", "package.json", "go.mod", "Cargo.toml", ".git")):
            return current
        if current.parent == current:
            break
        current = current.parent
    return cwd.resolve()


def extract_prompt(payload: dict) -> str:
    extra = payload.get("extra") if isinstance(payload.get("extra"), dict) else {}
    nested_extra = extra.get("extra") if isinstance(extra.get("extra"), dict) else {}
    prompt = (
        extra.get("user_message")
        or nested_extra.get("user_message")
        or payload.get("prompt")
        or payload.get("user_prompt")
        or payload.get("userPrompt")
        or payload.get("user_message")
        or nested_extra.get("prompt")
        or ""
    )
    return prompt.strip() if isinstance(prompt, str) else ""


def main() -> int:
    payload = read_json()
    prompt = extract_prompt(payload)
    if not prompt:
        return 0

    project_root = detect_project_root(Path(payload.get("cwd") or os.getcwd()).resolve())
    if importlib.util.find_spec("agent_learner") is not None:
        argv = [sys.executable, "-m", "agent_learner.cli.main", "render-hermes-context", "--project-root", str(project_root), "--prompt", prompt, "--format", "hook-json"]
    else:
        cli = shutil.which("agent-learner")
        argv = [cli, "core", "render-hermes-context", "--project-root", str(project_root), "--prompt", prompt, "--format", "hook-json"] if cli else [sys.executable, "-m", "agent_learner.cli.main", "render-hermes-context", "--project-root", str(project_root), "--prompt", prompt, "--format", "hook-json"]

    try:
        result = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=30)
    except (subprocess.TimeoutExpired, Exception):
        return 0
    if result.returncode != 0:
        return 0
    output = result.stdout.strip()
    if output:
        sys.stdout.write(output + "\\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""

ROOT_GITIGNORE_LINES = [
    ".agent-learner/events/",
    ".agent-learner/candidates/",
    ".agent-learner/history/",
    ".agent-learner/state/",
]

CONFIG_SNIPPET_HEADER = "# agent-learner hermes hooks snippet\n"
ACTIVATION_NOTES = """# Agent Learner + Hermes

This directory contains a project-local Hermes home for agent-learner hooks.

Safe default:
- Hermes will NOT read this automatically unless you opt in.
- To use the project-local hooks without affecting your default Hermes setup:

  HERMES_HOME=.hermes hermes --accept-hooks

- The project-local HERMES_HOME must also have model/auth configured.
- If it does not, merge the hook entries from config.agent-learner.yaml into the Hermes config you already use.

If you already maintain your own Hermes config, merge the hook entries from
config.agent-learner.yaml into your chosen config.yaml after review.
"""


def install_hermes_adapter(target_root: Path) -> list[Path]:
    return install_hermes_adapter_with_scope(target_root, scope="project")


def _command_for_script(script_path: Path, *, scope: str) -> str:
    python_cmd = shlex.quote(sys.executable)
    if scope == "user":
        return f"{python_cmd} {shlex.quote(str(script_path))}"
    return f"{python_cmd} {shlex.quote(f'./.hermes/hooks/{script_path.name}') }"


def _render_config_yaml(*, prompt_command: str, auto_command: str) -> str:
    return (
        "hooks:\n"
        "  pre_llm_call:\n"
        f"    - command: {prompt_command!r}\n"
        "      timeout: 15\n"
        "  on_session_end:\n"
        f"    - command: {auto_command!r}\n"
        "      timeout: 15\n"
        "hooks_auto_accept: false\n"
    )


def _write_config_files(hermes_root: Path, *, scope: str, prompt_script: Path, auto_script: Path) -> list[Path]:
    prompt_command = _command_for_script(prompt_script, scope=scope)
    auto_command = _command_for_script(auto_script, scope=scope)
    config_text = _render_config_yaml(prompt_command=prompt_command, auto_command=auto_command)
    config_path = hermes_root / "config.yaml"
    snippet_path = hermes_root / "config.agent-learner.yaml"
    written: list[Path] = []

    if not config_path.exists():
        written.append(write_text(config_path, config_text))
    written.append(write_text(snippet_path, CONFIG_SNIPPET_HEADER + config_text))
    written.append(write_text(hermes_root / "AGENT_LEARNER_README.md", ACTIVATION_NOTES))
    return written


def install_hermes_adapter_with_scope(target_root: Path, *, scope: str = "project") -> list[Path]:
    if scope not in {"project", "user"}:
        raise ValueError(f"unsupported hermes install scope: {scope}")

    written: list[Path] = []
    hermes_root = ensure_dir(target_root / ".hermes")
    hooks_root = ensure_dir(hermes_root / "hooks")
    auto_script = hooks_root / "auto_session_learning.py"
    prompt_script = hooks_root / "hermes_prompt_context.py"

    if scope == "project":
        ensure_dir(target_root / ".agent-learner" / "events" / "hermes")
        written.append(append_lines_if_missing(target_root / ".gitignore", ROOT_GITIGNORE_LINES))

    written.append(write_text(auto_script, AUTO_SESSION_LEARNING))
    written.append(write_text(prompt_script, PROMPT_CONTEXT))
    written.extend(_write_config_files(hermes_root, scope=scope, prompt_script=prompt_script, auto_script=auto_script))
    return written
