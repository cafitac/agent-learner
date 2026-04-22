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


def global_brain_root() -> Path:
    return agent_learner_home() / "global"


def global_learning_root() -> Path:
    return global_brain_root() / "learning"


def global_history_path() -> Path:
    return global_brain_root() / "history" / "promotions.jsonl"


def project_registry_path() -> Path:
    return global_brain_root() / "projects.json"


def canonical_learning_root(project_root: Path) -> Path:
    return project_root / ".agent-learner" / "learning"


def legacy_codex_learning_root(project_root: Path) -> Path:
    return project_root / ".codex" / "references" / "learning"


def resolve_learning_root(project_root: Path) -> Path:
    canonical = canonical_learning_root(project_root)
    legacy = legacy_codex_learning_root(project_root)
    marker = storage_migration_marker_path(project_root)
    if canonical.exists() and legacy.exists():
        if marker.exists():
            return canonical
        if has_learning_assets(canonical) and not has_learning_assets(legacy):
            return canonical
        return legacy
    if canonical.exists() or not legacy.exists():
        return canonical
    return legacy


def ensure_learning_root(project_root: Path) -> Path:
    root = canonical_learning_root(project_root)
    for bucket in LEARNING_BUCKETS:
        (root / bucket).mkdir(parents=True, exist_ok=True)
    return root


def ensure_global_learning_root() -> Path:
    root = global_learning_root()
    for bucket in LEARNING_BUCKETS:
        (root / bucket).mkdir(parents=True, exist_ok=True)
    return root


def promotions_history_path(project_root: Path) -> Path:
    return project_root / ".agent-learner" / "history" / "promotions.jsonl"


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
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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


def register_project(project_root: Path) -> Path:
    project_root = project_root.resolve()
    path = project_registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    projects = read_project_registry()
    entry = {"name": project_root.name, "root": str(project_root)}
    roots = {item["root"] for item in projects}
    if entry["root"] not in roots:
        projects.append(entry)
        projects = sorted(projects, key=lambda item: item["name"])
        path.write_text(json.dumps(projects, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def effective_learning_roots(project_root: Path) -> list[Path]:
    roots: list[Path] = []
    local = resolve_learning_root(project_root)
    if local.exists():
        roots.append(local)
    global_root = global_learning_root()
    if global_root.exists():
        roots.append(global_root)
    return roots


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
