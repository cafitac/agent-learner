from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from agent_learner.core.storage import LEARNING_BUCKETS, agent_learner_home, global_learning_root, storage_migration_marker_path

ADAPTERS = ("codex", "claude", "hermes")


def _count_files(path: Path, pattern: str) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob(pattern) if item.is_file())


def _count_direct_files(path: Path, pattern: str) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.glob(pattern) if item.is_file())


def _read_jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _read_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    try:
        _, frontmatter, _ = text.split("---", 2)
    except ValueError:
        return {}
    data: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def _candidate_counts(home: Path) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    root = home / "candidates"
    for adapter_dir in sorted(root.iterdir()) if root.exists() else []:
        if not adapter_dir.is_dir():
            continue
        adapter_counts: dict[str, int] = {}
        for candidate in sorted(adapter_dir.glob("*.md")):
            status = _read_frontmatter(candidate).get("status") or "unknown"
            adapter_counts[status] = adapter_counts.get(status, 0) + 1
        counts[adapter_dir.name] = adapter_counts
    return counts


def _events_by_adapter(home: Path) -> dict[str, int]:
    root = home / "events"
    counts: dict[str, int] = {}
    for adapter_dir in sorted(root.iterdir()) if root.exists() else []:
        if adapter_dir.is_dir():
            counts[adapter_dir.name] = _count_direct_files(adapter_dir, "*.json")
    return counts


def _learning_by_bucket() -> dict[str, int]:
    root = global_learning_root()
    return {bucket: _count_direct_files(root / bucket, "*.md") for bucket in LEARNING_BUCKETS}


def _file_counts_for_agent_learner_root(root: Path) -> dict[str, int]:
    return {
        "events": _count_files(root / "events", "*.json"),
        "candidates": _count_files(root / "candidates", "*.md"),
        "history": _count_files(root / "history", "*.jsonl"),
        "rules": _count_files(root / "learning", "*.md"),
        "state": _count_files(root / "state", "*"),
    }


def _file_counts_for_legacy_codex_root(root: Path) -> dict[str, int]:
    return {"rules": _count_files(root, "*.md")}


def _read_marker(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": str(path)}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"exists": True, "path": str(path), "valid": False}
    return {
        "exists": True,
        "path": str(path),
        "valid": True,
        "migrated_from": payload.get("migrated_from"),
        "canonical_root": payload.get("canonical_root"),
        "copied_counts": payload.get("copied_counts", {}),
        "copied_files_count": len(payload.get("copied_files", [])) if isinstance(payload.get("copied_files"), list) else 0,
    }


def _has_any_files(counts: dict[str, int]) -> bool:
    return any(value > 0 for value in counts.values())


def _unmirrored_local_files(source_root: Path, home: Path) -> list[str]:
    mappings = [
        (source_root / "events", home / "events", "*.json"),
        (source_root / "candidates", home / "candidates", "*.md"),
        (source_root / "history", home / "history", "*.jsonl"),
        (source_root / "learning", home / "learning", "*.md"),
    ]
    missing: list[str] = []
    for source_base, target_base, pattern in mappings:
        if not source_base.exists():
            continue
        for source in sorted(source_base.rglob(pattern)):
            if not source.is_file():
                continue
            target = target_base / source.relative_to(source_base)
            if not target.exists():
                missing.append(str(source))
    return missing


def _unmirrored_legacy_codex_files(source_root: Path) -> list[str]:
    missing: list[str] = []
    target_root = global_learning_root()
    if not source_root.exists():
        return missing
    for bucket in LEARNING_BUCKETS:
        for source in sorted((source_root / bucket).glob("*.md")):
            if not (target_root / bucket / source.name).exists():
                missing.append(str(source))
    return missing


def collect_storage_doctor(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    home = agent_learner_home()
    local_root = project_root / ".agent-learner"
    codex_legacy_root = project_root / ".codex" / "references" / "learning"

    local_counts = _file_counts_for_agent_learner_root(local_root)
    local_marker = _read_marker(storage_migration_marker_path(project_root))
    local_unmirrored = _unmirrored_local_files(local_root, home)
    codex_counts = _file_counts_for_legacy_codex_root(codex_legacy_root)
    codex_unmirrored = _unmirrored_legacy_codex_files(codex_legacy_root)

    legacy_sources = [
        {
            "kind": "project_local_agent_learner",
            "path": str(local_root),
            "exists": local_root.exists(),
            "file_counts": local_counts,
            "migration_marker": local_marker,
            "unmirrored_files_count": len(local_unmirrored),
            "sample_unmirrored_files": local_unmirrored[:5],
        },
        {
            "kind": "legacy_codex_learning",
            "path": str(codex_legacy_root),
            "exists": codex_legacy_root.exists(),
            "file_counts": codex_counts,
            "unmirrored_files_count": len(codex_unmirrored),
            "sample_unmirrored_files": codex_unmirrored[:5],
        },
    ]

    warnings: list[dict[str, str]] = []
    local_migration_command = f"agent-learner bootstrap --target {project_root}"
    codex_migration_command = f"agent-learner bootstrap --target {project_root} --adapters codex --codex-scope project"
    if _has_any_files(local_counts) and not local_marker.get("exists"):
        warnings.append(
            {
                "code": "legacy_source_missing_migration_marker",
                "path": str(local_root),
                "message": "Project-local .agent-learner files exist without a storage migration marker.",
                "next_command": local_migration_command,
            }
        )
    if local_unmirrored:
        warnings.append(
            {
                "code": "legacy_source_has_unmigrated_files",
                "path": str(local_root),
                "message": "Project-local .agent-learner files are not present in AGENT_LEARNER_HOME.",
                "next_command": local_migration_command,
            }
        )
    if codex_unmirrored:
        warnings.append(
            {
                "code": "legacy_codex_learning_unmigrated",
                "path": str(codex_legacy_root),
                "message": "Legacy Codex learning files are not present in AGENT_LEARNER_HOME; run the Codex bootstrap path to copy them into canonical global storage.",
                "next_command": codex_migration_command,
            }
        )

    counts = {
        "events_by_adapter": _events_by_adapter(home),
        "candidates_by_adapter_status": _candidate_counts(home),
        "learning_by_bucket": _learning_by_bucket(),
        "history_entries": _read_jsonl_count(home / "history" / "promotions.jsonl"),
        "index": {
            "rules_json": (home / "index" / "rules.json").exists(),
            "index_md": (home / "index" / "index.md").exists(),
        },
    }

    next_commands = [
        f"agent-learner process-events --project-root {project_root}",
        f"agent-learner rebuild-index --project-root {project_root}",
        f"agent-learner usage-summary --project-root {project_root} --format json",
    ]
    for warning in reversed(warnings):
        command = warning.get("next_command")
        if command and command not in next_commands:
            next_commands.insert(0, command)

    return {
        "project_root": str(project_root),
        "canonical": {
            "home": str(home),
            "learning_root": str(global_learning_root()),
            "env_var": "AGENT_LEARNER_HOME",
            "env_override_set": bool(os.environ.get("AGENT_LEARNER_HOME", "").strip()),
        },
        "counts": counts,
        "legacy_sources": legacy_sources,
        "warnings": warnings,
        "next_commands": next_commands,
    }


def format_storage_doctor_text(report: dict[str, Any]) -> str:
    warnings = report.get("warnings", [])
    lines = [
        "storage-doctor",
        f"project_root={report['project_root']}",
        f"canonical_home={report['canonical']['home']}",
        f"learning_root={report['canonical']['learning_root']}",
        f"warnings={len(warnings)}",
    ]
    counts = report.get("counts", {})
    lines.append(f"events_by_adapter={counts.get('events_by_adapter', {})}")
    lines.append(f"learning_by_bucket={counts.get('learning_by_bucket', {})}")
    for warning in warnings:
        lines.append(f"warning {warning['code']}: {warning['message']} ({warning['path']})")
    lines.append("next_commands:")
    for command in report.get("next_commands", []):
        lines.append(f"- {command}")
    return "\n".join(lines)
