from __future__ import annotations

import shlex
from pathlib import Path

from .common import ensure_dir, merge_json_file, upsert_hook, write_text


AUTO_SESSION_LEARNING = """#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import importlib.util
import json
import os
import shutil
import subprocess
import sys


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


def emit_shared_event(project_root: Path, payload: dict) -> None:
    session_id = payload.get("session_id") or datetime.now().strftime("%Y%m%d-%H%M%S")
    transcript_path = payload.get("transcript_path") or payload.get("transcriptPath") or None
    argv = ["capture-event", "--project-root", str(project_root), "--adapter", "claude", "--event-name", "session_end", "--session-id", session_id]
    if transcript_path:
        argv.extend(["--transcript-path", transcript_path])
    run_shared_cli(project_root, argv, payload)
    run_shared_cli(project_root, ["process-events", "--project-root", str(project_root), "--adapter", "claude", "--limit", "1"], None)


def main() -> int:
    payload = read_json()
    cwd = Path(payload.get("cwd") or os.getcwd()).resolve()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    learning_root = cwd / ".claude" / "learned-feedback"
    learning_root.mkdir(parents=True, exist_ok=True)
    ensure_events = cwd / ".agent-learner" / "events" / "claude"
    ensure_events.mkdir(parents=True, exist_ok=True)
    emit_shared_event(cwd, payload)
    (learning_root / "_session-end.md").write_text(f"# Session End\\n\\n- captured_at: {ts}\\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""


SESSION_WRAP = """---
name: session-wrap
description: Wrap up a coding session by preserving durable decisions and lessons.
---

# Session Wrap

Read the latest learning assets and summarize durable decisions.
"""


FEEDBACK_LEARNING = """---
name: feedback-learning
description: Capture repeated user corrections and durable working preferences.
---

# Feedback Learning

Turn repeated corrections into durable reusable rules.
"""


def _command_for_script(script_path: Path, *, scope: str) -> str:
    if scope == "user":
        return f"python3 {shlex.quote(str(script_path))}"
    return "python3 ./.claude/hooks/auto_session_learning.py"


def install_claude_adapter_with_scope(target_root: Path, *, scope: str = "project") -> list[Path]:
    if scope not in {"project", "user"}:
        raise ValueError(f"unsupported claude install scope: {scope}")
    written: list[Path] = []
    claude_root = ensure_dir(target_root / ".claude")
    auto_script = claude_root / "hooks" / "auto_session_learning.py"

    ensure_dir(claude_root / "skills" / "session-wrap")
    ensure_dir(claude_root / "skills" / "feedback-learning")
    ensure_dir(claude_root / "hooks")

    if scope == "project":
        ensure_dir(claude_root / "learned-feedback")
        ensure_dir(target_root / ".agent-learner" / "events" / "claude")

    written.append(write_text(auto_script, AUTO_SESSION_LEARNING))
    written.append(write_text(claude_root / "skills" / "session-wrap" / "SKILL.md", SESSION_WRAP))
    written.append(write_text(claude_root / "skills" / "feedback-learning" / "SKILL.md", FEEDBACK_LEARNING))

    merge_json_file(
        claude_root / "settings.json",
        {
            "hooks": {
                "SessionEnd": [
                    {
                        "matcher": ".*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": _command_for_script(auto_script, scope=scope),
                                "timeout": 30,
                            }
                        ],
                    }
                ]
            }
        },
    )
    written.append(claude_root / "settings.json")
    return written


def install_claude_adapter(target_root: Path) -> list[Path]:
    return install_claude_adapter_with_scope(target_root, scope="project")


# ---------------------------------------------------------------------------
# Phase 2: lightweight hook installer (mirrors hermit adapter pattern)
# ---------------------------------------------------------------------------

_CLAUDE_HOOK_COMMAND = (
    "agent-learner process --adapter claude"
    " --session-id $CLAUDE_SESSION_ID"
    " --cwd $CWD"
    " --model-id $CLAUDE_MODEL"
    " --auto"
)


def install_claude_hooks(project_root: Path, *, scope: str = "project") -> Path:
    """Install agent-learner Stop hook into .claude/settings.json.

    - scope="project": {project_root}/.claude/settings.json
    - Idempotent: updates existing agent-learner hook if present.
    - Preserves other Stop hooks.
    """
    settings_path = project_root / ".claude" / "settings.json"
    return upsert_hook(settings_path, "Stop", _CLAUDE_HOOK_COMMAND, hook_format="claude")
