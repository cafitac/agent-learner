from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .repo_identity import detect_repo_identity

PROJECT_MARKERS = ("pyproject.toml", "package.json", "go.mod", "Cargo.toml")
CURRENT_MODEL_STATE_PATH = Path(".agent-learner/state/current-model.txt")


@dataclass(slots=True)
class ContextSnapshot:
    cwd: str
    project_root: str | None
    project_name: str | None
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    current_model: str | None = None
    repo_id: str | None = None
    repo_root: str | None = None
    worktree_path: str | None = None
    repo_remote_url: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


def detect_project_root(cwd: Path) -> Path | None:
    current = cwd.resolve()
    for _ in range(20):
        if any((current / marker).exists() for marker in PROJECT_MARKERS):
            return current
        if current.parent == current:
            return None
        current = current.parent
    return None


def detect_languages(root: Path | None) -> list[str]:
    if root is None:
        return []
    languages: list[str] = []
    if (root / "pyproject.toml").exists():
        languages.append("python")
    if (root / "package.json").exists():
        languages.extend([lang for lang in ("javascript", "typescript") if lang not in languages])
    if (root / "go.mod").exists():
        languages.append("go")
    if (root / "Cargo.toml").exists():
        languages.append("rust")
    return languages


def detect_frameworks(root: Path | None) -> list[str]:
    if root is None:
        return []
    frameworks: list[str] = []
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8").lower()
        for marker, framework in (
            ("django", "django"),
            ("fastapi", "fastapi"),
            ("pytest", "pytest"),
            ("flask", "flask"),
        ):
            if marker in text and framework not in frameworks:
                frameworks.append(framework)
    package = root / "package.json"
    if package.exists():
        try:
            payload = json.loads(package.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        deps = {**payload.get("dependencies", {}), **payload.get("devDependencies", {})}
        for marker, framework in (
            ("react", "react"),
            ("next", "nextjs"),
            ("vitest", "vitest"),
            ("jest", "jest"),
            ("vue", "vue"),
        ):
            if marker in deps and framework not in frameworks:
                frameworks.append(framework)
    return frameworks


def read_current_model(project_root: Path) -> str | None:
    env_model = (
        __import__("os").environ.get("AGENT_LEARNER_MODEL")
        or __import__("os").environ.get("MODEL")
        or ""
    ).strip()
    if env_model:
        return env_model
    state_file = project_root / CURRENT_MODEL_STATE_PATH
    if state_file.exists():
        value = state_file.read_text(encoding="utf-8").strip()
        return value or None
    return None


def write_current_model(project_root: Path, model: str) -> Path:
    state_file = project_root / CURRENT_MODEL_STATE_PATH
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(model.strip() + "\n", encoding="utf-8")
    return state_file


def detect_context(cwd: Path) -> ContextSnapshot:
    resolved_cwd = cwd.resolve()
    project_root = detect_project_root(resolved_cwd) or resolved_cwd
    repo_identity = detect_repo_identity(resolved_cwd)
    return ContextSnapshot(
        cwd=str(resolved_cwd),
        project_root=str(project_root),
        project_name=project_root.name if project_root else None,
        languages=detect_languages(project_root),
        frameworks=detect_frameworks(project_root),
        current_model=read_current_model(project_root),
        repo_id=repo_identity.repo_id,
        repo_root=repo_identity.repo_root,
        worktree_path=repo_identity.worktree_path,
        repo_remote_url=repo_identity.repo_remote_url,
    )
