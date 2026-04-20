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
