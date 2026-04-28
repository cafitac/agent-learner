from pathlib import Path

from agent_learner.core.repo_identity import detect_repo_identity


def test_detect_repo_identity_uses_origin_remote_for_repo(tmp_path: Path) -> None:
    repo = tmp_path / "demo-repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

    import subprocess

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "remote", "add", "origin", "git@github.com:acme/demo-repo.git"], cwd=repo, check=True, capture_output=True, text=True)

    identity = detect_repo_identity(repo)

    assert identity.repo_id == "acme/demo-repo"
    assert identity.repo_root == str(repo.resolve())
    assert identity.cwd == str(repo.resolve())
    assert identity.worktree_path == str(repo.resolve())
    assert identity.repo_remote_url == "git@github.com:acme/demo-repo.git"


def test_detect_repo_identity_keeps_same_repo_id_for_nested_worktree_like_path(tmp_path: Path) -> None:
    repo = tmp_path / "demo-repo"
    nested = repo / ".worktrees" / "feature"
    nested.mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

    import subprocess

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "remote", "add", "origin", "https://github.com/acme/demo-repo.git"], cwd=repo, check=True, capture_output=True, text=True)

    identity = detect_repo_identity(nested)

    assert identity.repo_id == "acme/demo-repo"
    assert identity.repo_root == str(repo.resolve())
    assert identity.cwd == str(nested.resolve())
    assert identity.worktree_path == str(nested.resolve())
