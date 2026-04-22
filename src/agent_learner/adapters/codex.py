from __future__ import annotations

from pathlib import Path

from .common import append_lines_if_missing, ensure_dir, merge_json_file, write_text
from agent_learner.core.storage import migrate_legacy_learning_assets


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
        base = [cli] if cli else [sys.executable, "-m", "agent_learner.cli.main"]
    try:
        subprocess.run(base + argv, input=json.dumps(payload or {}), capture_output=True, text=True, check=False)
    except Exception:
        return


def emit_shared_event(project_root: Path, payload: dict, session_id: str) -> None:
    run_shared_cli(project_root, ["capture-event", "--project-root", str(project_root), "--adapter", "codex", "--event-name", "stop", "--session-id", session_id], payload)
    run_shared_cli(project_root, ["process-events", "--project-root", str(project_root), "--adapter", "codex", "--limit", "1"], None)


def main() -> int:
    payload = read_json()
    cwd = Path(payload.get("cwd") or os.getcwd()).resolve()
    session_id = payload.get("session_id") or datetime.now().strftime("%Y%m%d-%H%M%S")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    learning_root = cwd / ".agent-learner" / "learning"
    inbox = learning_root / "inbox"
    drafts = learning_root / "drafts"
    approved = learning_root / "approved"
    needs_review = learning_root / "needs_review"
    deprecated = learning_root / "deprecated"
    for path in (inbox, drafts, approved, needs_review, deprecated):
        path.mkdir(parents=True, exist_ok=True)

    emit_shared_event(cwd, payload, session_id)

    slug = session_id.replace("/", "-").replace(":", "-")
    (inbox / f"session-learning-{slug}.md").write_text(
        f"# Session Learning Candidate\\n\\n- captured_at: {ts}\\n- session_id: {session_id}\\n",
        encoding="utf-8",
    )
    (drafts / f"learned-rule-draft-{slug}.md").write_text(
        f"# Learned Rule Drafts\\n\\n- captured_at: {ts}\\n- session_id: {session_id}\\n",
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


def main() -> int:
    payload = read_json()
    prompt = (payload.get("prompt") or payload.get("user_prompt") or payload.get("userPrompt") or "").strip()
    if not prompt:
        return 0

    project_root = Path(payload.get("cwd") or os.getcwd()).resolve()
    argv: list[str] | None = None
    if importlib.util.find_spec("agent_learner") is not None:
        argv = [sys.executable, "-m", "agent_learner.cli.main", "render-codex-context", "--project-root", str(project_root), "--prompt", prompt, "--format", "hook-json"]
    else:
        cli = shutil.which("agent-learner")
        if cli:
            argv = [cli, "render-codex-context", "--project-root", str(project_root), "--prompt", prompt, "--format", "hook-json"]
        else:
            argv = [sys.executable, "-m", "agent_learner.cli.main", "render-codex-context", "--project-root", str(project_root), "--prompt", prompt, "--format", "hook-json"]

    try:
        result = subprocess.run(argv, capture_output=True, text=True, check=False)
    except Exception:
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


SESSION_WRAP = """---
name: session-wrap
description: Wrap up a coding session by preserving durable decisions, follow-ups, and repeatable lessons for future Codex runs.
---

# Session Wrap

1. Read the newest files in `.agent-learner/learning/inbox/`, `.agent-learner/learning/drafts/`, and `.agent-learner/history/promotions.jsonl`.
2. Extract durable rules, unfinished work, and next actions.
3. Save enduring rules to AGENTS, references, or canonical learning assets as appropriate.
"""


FEEDBACK_LEARNING = """---
name: feedback-learning
description: Capture repeated user corrections and durable working preferences as Codex-native learned feedback assets.
---

# Feedback Learning

1. Read the newest draft files in `.agent-learner/learning/drafts/`.
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

This directory holds canonical learning assets for this repo.

- inbox/
- drafts/
- approved/
- needs_review/
- deprecated/

Approved rules can be retrieved per-turn and injected into Codex prompt context
through the installed `UserPromptSubmit` hook without expanding the persistent
system prompt.

Normalized hook events are captured under `.agent-learner/events/codex/` so the
shared control plane can reason about Codex and Claude sessions using the same
event envelope.

Processed candidates and marker state are written under `.agent-learner/candidates/`
and `.agent-learner/state/` to avoid reprocessing the same session artifact.
"""


ROOT_GITIGNORE_LINES = [
    ".agent-learner/learning/inbox/",
    ".agent-learner/learning/drafts/",
    ".agent-learner/history/",
    ".agent-learner/events/",
    ".agent-learner/candidates/",
    ".agent-learner/state/",
]


def install_codex_adapter(target_root: Path) -> list[Path]:
    written: list[Path] = []
    codex_root = ensure_dir(target_root / ".codex")
    learning_root = ensure_dir(target_root / ".agent-learner" / "learning")
    for child in ("inbox", "drafts", "approved", "needs_review", "deprecated"):
        ensure_dir(learning_root / child)
    ensure_dir(target_root / ".agent-learner" / "events" / "codex")
    ensure_dir(target_root / ".agent-learner" / "history")

    written.append(write_text(learning_root / "README.md", LEARNING_README))
    written.append(write_text(codex_root / "references" / "scripts" / "auto_session_learning.py", AUTO_SESSION_LEARNING))
    written.append(write_text(codex_root / "references" / "scripts" / "codex_prompt_context.py", PROMPT_CONTEXT))
    written.append(write_text(codex_root / "skills" / "session-wrap" / "SKILL.md", SESSION_WRAP))
    written.append(write_text(codex_root / "skills" / "feedback-learning" / "SKILL.md", FEEDBACK_LEARNING))
    written.append(write_text(codex_root / "skills" / "hermit-learner" / "SKILL.md", HERMIT_LEARNER))
    written.append(append_lines_if_missing(target_root / ".gitignore", ROOT_GITIGNORE_LINES))

    merge_json_file(
        codex_root / "hooks.json",
        {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "python3 ./.codex/references/scripts/codex_prompt_context.py",
                                "timeout": 15,
                            }
                        ]
                    }
                ],
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
    written.extend(migrate_legacy_learning_assets(target_root))
    return written
