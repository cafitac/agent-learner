from __future__ import annotations

from pathlib import Path

from .common import append_lines_if_missing, ensure_dir, merge_json_file, write_text


AUTO_SESSION_LEARNING = """#!/usr/bin/env python3
from __future__ import annotations

import json
import os
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


def main() -> int:
    payload = read_json()
    cwd = Path(payload.get("cwd") or os.getcwd()).resolve()
    session_id = payload.get("session_id") or datetime.now().strftime("%Y%m%d-%H%M%S")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    learning_root = cwd / ".codex" / "references" / "learning"
    inbox = learning_root / "inbox"
    drafts = learning_root / "drafts"
    approved = learning_root / "approved"
    needs_review = learning_root / "needs_review"
    deprecated = learning_root / "deprecated"
    session_log = cwd / ".omx" / "wiki" / "session-log"
    for path in (inbox, drafts, approved, needs_review, deprecated, session_log):
        path.mkdir(parents=True, exist_ok=True)

    slug = session_id.replace("/", "-").replace(":", "-")
    (inbox / f"session-learning-{slug}.md").write_text(
        f"# Session Learning Candidate\\n\\n- captured_at: {ts}\\n- session_id: {session_id}\\n",
        encoding="utf-8",
    )
    (drafts / f"learned-rule-draft-{slug}.md").write_text(
        f"# Learned Rule Drafts\\n\\n- captured_at: {ts}\\n- session_id: {session_id}\\n",
        encoding="utf-8",
    )
    (session_log / f"session-wrap-{slug}.md").write_text(
        f"# Session Wrap\\n\\n- captured_at: {ts}\\n- session_id: {session_id}\\n",
        encoding="utf-8",
    )
    dashboard = learning_root / "dashboard.md"
    dashboard.write_text(
        "# Learning Assets Dashboard\\n\\n"
        f"- approved: {len(list(approved.glob('*.md')))}\\n"
        f"- needs_review: {len(list(needs_review.glob('*.md')))}\\n"
        f"- deprecated: {len(list(deprecated.glob('*.md')))}\\n"
        f"- drafts: {len(list(drafts.glob('*.md')))}\\n"
        f"- inbox: {len(list(inbox.glob('*.md')))}\\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""


SESSION_WRAP = """---
name: session-wrap
description: Wrap up a coding session by preserving durable decisions, follow-ups, and repeatable lessons for future Codex runs.
---

# Session Wrap

1. Read the newest files in `.codex/references/learning/inbox/`, `.codex/references/learning/drafts/`, and `.omx/wiki/session-log/`.
2. Extract durable rules, unfinished work, and next actions.
3. Save enduring rules to AGENTS, references, or wiki as appropriate.
"""


FEEDBACK_LEARNING = """---
name: feedback-learning
description: Capture repeated user corrections and durable working preferences as Codex-native learned feedback assets.
---

# Feedback Learning

1. Read the newest draft files in `.codex/references/learning/drafts/`.
2. Decide whether each rule should stay draft, become approved, or move elsewhere.
3. Prefer short reusable rules over narrative logs.
"""


HERMIT_LEARNER = """---
name: hermit-learner
description: Review and curate Hermit-generated learning assets.
---

# Hermit Learner

Use this skill to inspect and curate Hermit-side learning artifacts critically.
"""


LEARNING_README = """# Learned Feedback and Learning Assets

This directory holds Codex-native learning assets for this repo.

- inbox/
- drafts/
- approved/
- needs_review/
- deprecated/
"""


ROOT_GITIGNORE_LINES = [
    ".codex/references/learning/inbox/",
    ".codex/references/learning/drafts/",
    ".omx/wiki/session-log/",
]


def install_codex_adapter(target_root: Path) -> list[Path]:
    written: list[Path] = []
    codex_root = ensure_dir(target_root / ".codex")
    learning_root = ensure_dir(codex_root / "references" / "learning")
    for child in ("inbox", "drafts", "approved", "needs_review", "deprecated"):
        ensure_dir(learning_root / child)
    ensure_dir(target_root / ".omx" / "wiki" / "session-log")

    written.append(write_text(learning_root / "README.md", LEARNING_README))
    written.append(write_text(codex_root / "references" / "scripts" / "auto_session_learning.py", AUTO_SESSION_LEARNING))
    written.append(write_text(codex_root / "skills" / "session-wrap" / "SKILL.md", SESSION_WRAP))
    written.append(write_text(codex_root / "skills" / "feedback-learning" / "SKILL.md", FEEDBACK_LEARNING))
    written.append(write_text(codex_root / "skills" / "hermit-learner" / "SKILL.md", HERMIT_LEARNER))
    written.append(append_lines_if_missing(target_root / ".gitignore", ROOT_GITIGNORE_LINES))

    merge_json_file(
        codex_root / "hooks.json",
        {
            "hooks": {
                "Stop": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "python3 ./.codex/references/scripts/auto_session_learning.py",
                                "timeout": 15,
                            }
                        ]
                    }
                ]
            }
        },
    )
    written.append(codex_root / "hooks.json")
    return written
