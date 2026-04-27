"""Hermit adapter — install OnStop hooks and emit session events."""
from __future__ import annotations

from pathlib import Path

from .common import upsert_hook
from agent_learner.core.events import build_learning_event, write_learning_event

_ADAPTER = "hermit"

_HOOK_COMMAND = (
    "agent-learner process --adapter hermit"
    " --session-id $HERMIT_SESSION_ID"
    " --cwd $CWD"
    " --model-id $HERMIT_MODEL_ID"
    " --auto"
)


def install_hermit_hooks(project_root: Path, *, scope: str = "project") -> Path:
    """
    Install agent-learner OnStop hook into .hermit/settings.json.

    - scope="project": {project_root}/.hermit/settings.json
    - scope="user": ~/.hermit/settings.json
    - Idempotent: updates existing agent-learner hook if present.
    - Preserves other OnStop hooks.
    """
    settings_path = project_root / ".hermit" / "settings.json"
    return upsert_hook(settings_path, "OnStop", _HOOK_COMMAND)


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
