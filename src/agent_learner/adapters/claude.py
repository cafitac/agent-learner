from __future__ import annotations

from pathlib import Path

from .common import ensure_dir, merge_json_file, write_text


AUTO_SESSION_LEARNING = """#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import os
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


def main() -> int:
    payload = read_json()
    cwd = Path(payload.get("cwd") or os.getcwd()).resolve()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    learning_root = cwd / ".claude" / "learned-feedback"
    learning_root.mkdir(parents=True, exist_ok=True)
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


def install_claude_adapter(target_root: Path) -> list[Path]:
    written: list[Path] = []
    claude_root = ensure_dir(target_root / ".claude")
    ensure_dir(claude_root / "skills" / "session-wrap")
    ensure_dir(claude_root / "skills" / "feedback-learning")
    ensure_dir(claude_root / "hooks")
    ensure_dir(claude_root / "learned-feedback")

    written.append(write_text(claude_root / "hooks" / "auto_session_learning.py", AUTO_SESSION_LEARNING))
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
                                "command": "python3 ./.claude/hooks/auto_session_learning.py",
                            }
                        ],
                    }
                ]
            }
        },
    )
    written.append(claude_root / "settings.json")
    return written
