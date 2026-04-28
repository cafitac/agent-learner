from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

LEARNING_BUCKETS = ("inbox", "drafts", "approved", "needs_review", "deprecated")


def agent_learner_home() -> Path:
    override = os.environ.get("AGENT_LEARNER_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".agent-learner").resolve()


def global_learning_home() -> Path:
    return agent_learner_home()


def global_learning_root() -> Path:
    return global_learning_home() / "learning"


def global_history_path() -> Path:
    return global_learning_home() / "history" / "promotions.jsonl"


def project_registry_path() -> Path:
    return global_learning_home() / "projects.json"


def canonical_learning_root(project_root: Path) -> Path:
    migrate_local_learning_store_to_global(project_root)
    migrate_legacy_learning_assets(project_root)
    return global_learning_root()


def legacy_codex_learning_root(project_root: Path) -> Path:
    return project_root / ".codex" / "references" / "learning"


def resolve_learning_root(project_root: Path) -> Path:
    migrate_local_learning_store_to_global(project_root)
    migrate_legacy_learning_assets(project_root)
    return global_learning_root()


def ensure_learning_root(project_root: Path) -> Path:
    return ensure_global_learning_root()


def ensure_global_learning_root() -> Path:
    root = global_learning_root()
    for bucket in LEARNING_BUCKETS:
        (root / bucket).mkdir(parents=True, exist_ok=True)
    return root


def promotions_history_path(project_root: Path) -> Path:
    migrate_local_learning_store_to_global(project_root)
    return global_history_path()


def storage_migration_marker_path(project_root: Path) -> Path:
    return project_root / ".agent-learner" / "state" / "storage-migration.json"


def has_learning_assets(root: Path) -> bool:
    if not root.exists():
        return False
    for bucket in LEARNING_BUCKETS:
        if any((root / bucket).glob("*.md")):
            return True
    return False


def write_storage_migration_marker(project_root: Path, payload: dict[str, object]) -> Path:
    path = storage_migration_marker_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, object] = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}

    merged = dict(existing)
    merged.update(payload)

    existing_counts = existing.get("copied_counts") if isinstance(existing.get("copied_counts"), dict) else {}
    new_counts = payload.get("copied_counts") if isinstance(payload.get("copied_counts"), dict) else None
    if new_counts is not None:
        merged["copied_counts"] = {
            key: max(int(existing_counts.get(key, 0)), int(new_counts.get(key, 0)))
            for key in sorted(set(existing_counts) | set(new_counts))
        }

    existing_files = existing.get("copied_files") if isinstance(existing.get("copied_files"), list) else []
    new_files = payload.get("copied_files") if isinstance(payload.get("copied_files"), list) else None
    if new_files is not None:
        merged["copied_files"] = sorted({str(item) for item in [*existing_files, *new_files]})

    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def append_jsonl(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path


def read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        rows.append(json.loads(stripped))
    return rows


def read_project_registry() -> list[dict[str, str]]:
    path = project_registry_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def should_register_project(project_root: Path) -> bool:
    root_text = str(project_root.resolve())
    name = project_root.name
    if "/pytest-of-" in root_text or "/pytest-" in root_text:
        return False
    if "/tmp/" in root_text or root_text.startswith("/tmp/"):
        return False
    if name.startswith("test_") and "pytest" in root_text:
        return False
    return True


def register_project(project_root: Path) -> Path:
    project_root = project_root.resolve()
    path = project_registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not should_register_project(project_root):
        return path
    projects = read_project_registry()
    entry = {"name": project_root.name, "root": str(project_root)}
    roots = {item["root"] for item in projects}
    if entry["root"] not in roots:
        projects.append(entry)
        projects = sorted(projects, key=lambda item: item["name"])
        path.write_text(json.dumps(projects, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def effective_learning_roots(project_root: Path) -> list[Path]:
    migrate_local_learning_store_to_global(project_root)
    root = global_learning_root()
    return [root] if root.exists() else []


def _copy_tree_files(source_root: Path, target_root: Path, pattern: str = "*") -> int:
    copied = 0
    if not source_root.exists():
        return copied
    for source in sorted(source_root.rglob(pattern)):
        if not source.is_file():
            continue
        target = target_root / source.relative_to(source_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            continue
        shutil.copy2(source, target)
        copied += 1
    return copied


def migrate_local_learning_store_to_global(project_root: Path) -> dict[str, int]:
    project_root = project_root.resolve()
    local_root = project_root / ".agent-learner"
    ensure_global_learning_root()
    counts = {
        "events": _copy_tree_files(local_root / "events", agent_learner_home() / "events", "*.json"),
        "candidates": _copy_tree_files(local_root / "candidates", agent_learner_home() / "candidates", "*.md"),
        "history": _copy_tree_files(local_root / "history", agent_learner_home() / "history", "*.jsonl"),
        "rules": _copy_tree_files(local_root / "learning", global_learning_root(), "*.md"),
    }
    write_storage_migration_marker(
        project_root,
        {
            "migrated_from": str(local_root),
            "canonical_root": str(agent_learner_home()),
            "copied_counts": counts,
        },
    )
    return counts


def migrate_legacy_learning_assets(project_root: Path) -> list[Path]:
    canonical = ensure_learning_root(project_root)
    legacy = legacy_codex_learning_root(project_root)
    migrated: list[Path] = []
    if not legacy.exists():
        return migrated

    for bucket in LEARNING_BUCKETS:
        legacy_bucket = legacy / bucket
        canonical_bucket = canonical / bucket
        if not legacy_bucket.exists():
            continue
        for source in sorted(legacy_bucket.glob("*.md")):
            target = canonical_bucket / source.name
            if target.exists():
                continue
            shutil.copy2(source, target)
            migrated.append(target)

    if migrated or has_learning_assets(canonical):
        write_storage_migration_marker(
            project_root,
            {
                "migrated_from": str(legacy),
                "canonical_root": str(canonical),
                "copied_files": [str(path) for path in migrated],
            },
        )
    return migrated
