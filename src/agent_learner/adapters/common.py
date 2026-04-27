from __future__ import annotations

import json
from pathlib import Path


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def merge_json_file(path: Path, patch: dict) -> dict:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {}
    merged = deep_merge(data, patch)
    write_text(path, json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
    return merged


def append_lines_if_missing(path: Path, lines: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8").splitlines()
    else:
        existing = []
    seen = set(existing)
    for line in lines:
        if line not in seen:
            existing.append(line)
            seen.add(line)
    path.write_text("\n".join(existing).rstrip() + "\n", encoding="utf-8")
    return path


def deep_merge(base: dict, patch: dict) -> dict:
    result = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        elif isinstance(value, list) and isinstance(result.get(key), list):
            result[key] = merge_lists(result[key], value)
        else:
            result[key] = value
    return result


def merge_lists(existing: list, incoming: list) -> list:
    result = list(existing)
    seen = {json.dumps(item, sort_keys=True, ensure_ascii=False) for item in existing}
    for item in incoming:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result


def is_agent_learner_hook(hook: dict) -> bool:
    """Check whether a hook entry was installed by agent-learner."""
    return "agent-learner" in hook.get("command", "")


def upsert_hook(settings_path: Path, event_name: str, command: str) -> Path:
    """Idempotently install or update an agent-learner hook in a JSON settings file.

    - Creates the file and parent directories if they do not exist.
    - Replaces an existing agent-learner hook under *event_name* if found.
    - Appends a new hook entry otherwise.
    - Preserves all other hooks.
    """
    ensure_dir(settings_path.parent)

    if settings_path.exists():
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    else:
        data = {}

    hooks = data.setdefault("hooks", {})
    event_hooks: list[dict] = hooks.setdefault(event_name, [])

    new_hook = {"command": command}
    replaced = False
    for i, hook in enumerate(event_hooks):
        if is_agent_learner_hook(hook):
            event_hooks[i] = new_hook
            replaced = True
            break
    if not replaced:
        event_hooks.append(new_hook)

    hooks[event_name] = event_hooks
    settings_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return settings_path
