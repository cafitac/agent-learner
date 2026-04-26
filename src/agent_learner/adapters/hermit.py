"""Hermit adapter — install OnStop hooks and emit session events."""
from __future__ import annotations

import json
from pathlib import Path

from .common import ensure_dir, merge_json_file
from agent_learner.core.events import build_learning_event, write_learning_event

_ADAPTER = "hermit"

_HOOK_COMMAND = (
    "agent-learner process --adapter hermit"
    " --session-id $HERMIT_SESSION_ID"
    " --cwd $CWD"
    " --model-id $HERMIT_MODEL_ID"
    " --auto"
)


def _hermit_settings_path(project_root: Path, *, scope: str) -> Path:
    return project_root / ".hermit" / "settings.json"


def _is_agent_learner_hook(hook: dict) -> bool:
    return "agent-learner" in hook.get("command", "")


def install_hermit_hooks(project_root: Path, *, scope: str = "project") -> Path:
    """
    Install agent-learner OnStop hook into .hermit/settings.json.

    - scope="project": {project_root}/.hermit/settings.json
    - scope="user": ~/.hermit/settings.json
    - Idempotent: updates existing agent-learner hook if present.
    - Preserves other OnStop hooks.
    """
    settings_path = _hermit_settings_path(project_root, scope=scope)
    ensure_dir(settings_path.parent)

    # Read existing settings
    if settings_path.exists():
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    else:
        settings = {}

    # Navigate to hooks.OnStop
    hooks = settings.setdefault("hooks", {})
    on_stop: list[dict] = hooks.setdefault("OnStop", [])

    # Find existing agent-learner hook or create new one
    new_hook = {"command": _HOOK_COMMAND}
    found = False
    for i, hook in enumerate(on_stop):
        if _is_agent_learner_hook(hook):
            on_stop[i] = new_hook
            found = True
            break
    if not found:
        on_stop.append(new_hook)

    hooks["OnStop"] = on_stop
    settings_path.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return settings_path


def emit_session_event(
    project_root: Path,
    *,
    session_id: str,
    cwd: str,
    model_id: str,
    outcome: str,
    tool_call_count: int,
    pytest_output: str | None = None,
    transcript_path: str | None = None,
) -> Path:
    """
    Write a session_end event to .agent-learner/events/hermit/.

    Wraps write_learning_event() from core.
    """
    payload: dict[str, object] = {
        "outcome": outcome,
        "tool_call_count": tool_call_count,
        "model_id": model_id,
    }
    if pytest_output is not None:
        payload["pytest_output"] = pytest_output
    if transcript_path is not None:
        payload["transcript_path"] = transcript_path

    event = build_learning_event(
        adapter=_ADAPTER,
        event_name="session_end",
        cwd=cwd,
        session_id=session_id,
        transcript_path=transcript_path,
        payload=payload,
    )
    return write_learning_event(project_root, event)
