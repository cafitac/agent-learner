from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_GITHUB_SSH_RE = re.compile(r"^(?:ssh://)?git@([^:]+):(.+?)(?:\.git)?$")
_HTTPS_RE = re.compile(r"^https?://([^/]+)/(.+?)(?:\.git)?/?$")


@dataclass(slots=True)
class RepoIdentity:
    repo_id: str
    repo_root: str
    cwd: str
    worktree_path: str
    repo_remote_url: str | None = None


def _run_git(cwd: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return None
    output = (result.stdout or "").strip()
    if result.returncode != 0 or not output:
        return None
    return output


def _normalize_remote(remote_url: str | None) -> str | None:
    if not remote_url:
        return None
    text = remote_url.strip()
    for pattern in (_GITHUB_SSH_RE, _HTTPS_RE):
        match = pattern.match(text)
        if match:
            return match.group(2).rstrip("/")
    if ":" in text and "/" in text:
        tail = text.split(":", 1)[-1]
        return tail.removesuffix(".git").strip("/")
    return None


def detect_repo_identity(cwd: Path) -> RepoIdentity:
    resolved_cwd = cwd.resolve()
    git_root = _run_git(resolved_cwd, "rev-parse", "--show-toplevel")
    repo_root = Path(git_root).resolve() if git_root else resolved_cwd
    remote_url = _run_git(repo_root, "remote", "get-url", "origin")
    repo_id = _normalize_remote(remote_url)
    if not repo_id:
        digest = hashlib.sha1(str(repo_root).encode("utf-8")).hexdigest()[:12]
        repo_id = f"local/{repo_root.name}-{digest}"
    return RepoIdentity(
        repo_id=repo_id,
        repo_root=str(repo_root),
        cwd=str(resolved_cwd),
        worktree_path=str(resolved_cwd),
        repo_remote_url=remote_url,
    )
